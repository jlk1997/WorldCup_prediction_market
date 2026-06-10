"""Tests for MiniMax LLM client rate-limit handling."""

from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.core.exceptions import LLMError
from app.services.llm_client import is_rate_limit_error, rate_limit_retry_delay


def test_is_rate_limit_error_from_message():
    assert is_rate_limit_error(Exception("HTTP 429 Too Many Requests"))
    assert is_rate_limit_error(Exception("rate limit exceeded"))
    assert not is_rate_limit_error(Exception("connection timeout"))


def test_rate_limit_retry_delay_exponential():
    assert rate_limit_retry_delay(Exception("429"), 0, 1.5) == 1.5
    assert rate_limit_retry_delay(Exception("429"), 2, 1.5) == 6.0


def test_create_completion_retries_then_raises():
    from app.services.llm_client import LLMClient

    settings = MagicMock()
    settings.minimax_api_key = "test-key"
    settings.minimax_base_url = "https://example.com/v1"
    settings.minimax_model = "test-model"
    settings.minimax_temperature = 0.7
    settings.minimax_max_retries = 2
    settings.minimax_retry_base_seconds = 0.01

    client = LLMClient.__new__(LLMClient)
    client.settings = settings
    client.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    client._usage_lock = __import__("threading").Lock()
    client.client = MagicMock()
    client.client.chat.completions.create.side_effect = RateLimitError(
        "429",
        response=MagicMock(status_code=429),
        body=None,
    )

    with patch("app.services.llm_client.acquire_llm_slot", return_value="thread"), patch(
        "app.services.llm_client.release_llm_slot"
    ), patch(
        "app.services.llm_client.time.sleep"
    ):
        with pytest.raises(LLMError, match="429"):
            client._create_completion(model="m", messages=[])

    assert client.client.chat.completions.create.call_count == 3
