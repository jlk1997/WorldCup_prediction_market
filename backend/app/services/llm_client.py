import json
import logging
import re
import threading
import time

from openai import APIStatusError, OpenAI, RateLimitError

from app.core.ai_concurrency import acquire_llm_slot, release_llm_slot
from app.core.config import get_settings
from app.core.exceptions import LLMError, ServiceUnavailableError

logger = logging.getLogger(__name__)


def is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "too many requests" in msg or "rate limit" in msg


def rate_limit_retry_delay(exc: Exception, attempt: int, base_seconds: float) -> float:
    retry_after = getattr(exc, "response", None)
    if retry_after is not None:
        header = retry_after.headers.get("retry-after") if hasattr(retry_after, "headers") else None
        if header:
            try:
                return max(float(header), base_seconds)
            except ValueError:
                pass
    return base_seconds * (2 ** attempt)


class LLMClient:
    def __init__(self):
        settings = get_settings()
        if not settings.minimax_configured():
            raise ServiceUnavailableError(
                "未配置 MINIMAX_API_KEY，请在 backend/.env 中填入 MiniMax API Key"
            )
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            max_retries=0,
        )
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self._usage_lock = threading.Lock()

    @staticmethod
    def merge_usage(target: dict, source: dict) -> None:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            target[key] = target.get(key, 0) + source.get(key, 0)

    def _record_usage(self, completion) -> None:
        usage = getattr(completion, "usage", None)
        if not usage:
            return
        pt = int(getattr(usage, "prompt_tokens", 0) or 0)
        ct = int(getattr(usage, "completion_tokens", 0) or 0)
        tt = int(getattr(usage, "total_tokens", 0) or (pt + ct))
        with self._usage_lock:
            self.token_usage["prompt_tokens"] += pt
            self.token_usage["completion_tokens"] += ct
            self.token_usage["total_tokens"] += tt

    def _create_completion(self, **kwargs):
        max_retries = max(0, self.settings.minimax_max_retries)
        base = max(0.5, self.settings.minimax_retry_base_seconds)
        last_exc: Exception | None = None

        for attempt in range(max_retries + 1):
            slot = acquire_llm_slot()
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                last_exc = exc
                if not is_rate_limit_error(exc):
                    raise
                if attempt >= max_retries:
                    logger.warning(
                        "MiniMax rate limit exhausted after %s attempts: %s",
                        attempt + 1,
                        exc,
                    )
                    raise LLMError(
                        "MiniMax 请求过于频繁（429），请等待 1～2 分钟后再试；"
                        "若频繁出现可在 .env 将 AGENT_PARALLEL_LLM 设为 false"
                    ) from exc
                wait = rate_limit_retry_delay(exc, attempt, base)
                logger.info(
                    "MiniMax 429, retry %s/%s in %.1fs",
                    attempt + 1,
                    max_retries,
                    wait,
                )
            finally:
                release_llm_slot(slot)

            time.sleep(wait)

        raise LLMError("MiniMax 调用失败") from last_exc

    def complete_json(self, system: str, user: str, max_tokens: int = 2000, temperature: float | None = None) -> dict:
        temp = self.settings.minimax_temperature if temperature is None else temperature
        try:
            completion = self._create_completion(
                model=self.settings.minimax_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temp,
                max_tokens=max_tokens,
            )
        except LLMError:
            raise
        except Exception as exc:
            if is_rate_limit_error(exc):
                raise LLMError(
                    "MiniMax 请求过于频繁（429），请等待 1～2 分钟后再试"
                ) from exc
            raise LLMError(f"MiniMax 调用失败: {exc}") from exc

        self._record_usage(completion)
        if not completion.choices:
            raise LLMError("MiniMax 返回空 choices")
        content = (completion.choices[0].message.content or "").strip()
        return self._parse_json(content)

    def complete_text(self, system: str, user: str, max_tokens: int = 1500) -> str:
        try:
            completion = self._create_completion(
                model=self.settings.minimax_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self.settings.minimax_temperature,
                max_tokens=max_tokens,
            )
        except LLMError:
            raise
        except Exception as exc:
            if is_rate_limit_error(exc):
                raise LLMError(
                    "MiniMax 请求过于频繁（429），请等待 1～2 分钟后再试"
                ) from exc
            raise LLMError(f"MiniMax 调用失败: {exc}") from exc
        self._record_usage(completion)
        return (completion.choices[0].message.content or "").strip()

    def complete_json_safe(
        self, system: str, user: str, max_tokens: int = 2000, temperature: float | None = None
    ) -> dict:
        try:
            return self.complete_json(system, user, max_tokens=max_tokens, temperature=temperature)
        except LLMError:
            return {}

    @staticmethod
    def _strip_markdown_fence(content: str) -> str:
        text = (content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```\s*$", "", text)
        return text.strip()

    def _parse_json(self, content: str) -> dict:
        content = self._strip_markdown_fence(content)
        if not content:
            raise LLMError("MiniMax 返回空内容")
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            snippet = content[:240].replace("\n", " ")
            logger.warning("LLM JSON parse failed, snippet=%s…", snippet)
            raise LLMError("LLM 返回内容无法解析为 JSON")

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        tool_router,
        max_steps: int = 8,
        max_tokens: int = 2000,
    ) -> dict:
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        steps: list[dict] = []

        for _ in range(max_steps):
            try:
                completion = self._create_completion(
                    model=self.settings.minimax_model,
                    messages=messages,
                    temperature=self.settings.minimax_temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                    tool_choice="auto",
                )
            except LLMError:
                raise
            except Exception as exc:
                if is_rate_limit_error(exc):
                    raise LLMError(
                        "MiniMax 请求过于频繁（429），请等待 1～2 分钟后再试"
                    ) from exc
                raise LLMError(f"MiniMax tool 调用失败: {exc}") from exc

            self._record_usage(completion)
            msg = completion.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                content = (msg.content or "").strip()
                return {"steps": steps, "result": self._parse_json(content) if content else {}}

            messages.append(msg.model_dump())
            for call in tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tool_router(name, args)
                steps.append({"tool": name, "args": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        raise LLMError(f"Agent 超过最大步数 {max_steps}")
