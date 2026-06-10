from pydantic import BaseModel, Field, ValidationError

from app.core.exceptions import LLMError, NotFoundError
from app.db.models import PlayerDetailed, Team
from app.db.repositories.prediction_repository import PredictionRepository
from app.db.repositories.team_repository import TeamRepository
from app.services.llm_client import LLMClient
from sqlalchemy.orm import Session


class AnalysisResult(BaseModel):
    score: str = Field(..., min_length=1)
    total_goals: str = Field(..., min_length=1)
    red_cards: str = Field(..., min_length=1)
    penalties: str = Field(..., min_length=1)
    advice: str = Field(..., min_length=1)


ANALYSIS_SYSTEM_PROMPT = (
    "你是资深的足球预测专家和精算师。"
    "必须只输出一个 JSON 对象，不要 Markdown，不要解释，不要前缀。"
    '字段: score, total_goals, red_cards, penalties, advice。'
)


class PredictionService:
    def __init__(self, db: Session):
        self.db = db
        self.teams = TeamRepository(db)
        self.predictions = PredictionRepository(db)

    def get_analysis(self, team1_name: str, team2_name: str, force_refresh: bool = False) -> dict:
        cached = self.predictions.get(team1_name, team2_name)
        if not force_refresh and self.predictions.is_complete(cached):
            return self._wrap(cached, cached=True)

        team1 = self.teams.get_by_name(team1_name)
        team2 = self.teams.get_by_name(team2_name)
        if not team1:
            raise NotFoundError(f"球队 {team1_name} 未找到")
        if not team2:
            raise NotFoundError(f"球队 {team2_name} 未找到")

        context = self._build_context(team1, team2)
        user_prompt = (
            f"{context}\n\n"
            f"请基于以上数据，对 {team1_name} vs {team2_name} 给出完整分析。\n"
            "输出 JSON，字段要求：\n"
            '- score: 预测比分，如 "2:1"\n'
            '- total_goals: 总进球，如 "3球"\n'
            '- red_cards: 红牌预警，一句话\n'
            '- penalties: 点球预测，一两句话\n'
            '- advice: 专家投注建议，约500字，纯文本'
        )

        llm = LLMClient()
        last_error: Exception | None = None
        for _ in range(2):
            try:
                raw = llm.complete_json(ANALYSIS_SYSTEM_PROMPT, user_prompt, max_tokens=2000)
                result = AnalysisResult.model_validate(raw)
                row = self.predictions.upsert(
                    team1_name,
                    team2_name,
                    score=result.score,
                    total_goals=result.total_goals,
                    red_cards=result.red_cards,
                    penalties=result.penalties,
                    advice=result.advice,
                )
                return self._wrap(row, cached=False)
            except (LLMError, ValidationError, ValueError) as exc:
                last_error = exc
                user_prompt += "\n上次输出格式无效，请严格只返回合法 JSON 对象。"

        raise LLMError(str(last_error) if last_error else "LLM 分析失败")

    def _wrap(self, row, cached: bool) -> dict:
        return {
            "status": "success",
            "cached": cached,
            "data": {
                "score": row.score,
                "total_goals": row.total_goals,
                "red_cards": row.red_cards,
                "penalties": row.penalties,
                "advice": row.advice,
            },
        }

    def _build_context(self, team1: Team, team2: Team) -> str:
        parts = [
            "你是一个专业的足球赛事分析师和彩票精算师。请基于以下详细的真实数据进行分析。\n"
        ]
        parts.append(self._format_team(team1))
        parts.append(self._format_team(team2))
        return "\n".join(parts)

    def _format_team(self, team: Team) -> str:
        players = sorted(
            team.players_detailed or [],
            key=lambda p: (p.overall_rating or 0),
            reverse=True,
        )[:6]
        lines = [
            f"【{team.name}】",
            f"FIFA排名：{team.fifa_ranking}",
            f"主教练：{team.coach}",
            f"阵型：{team.formation}",
            f"身价：{team.total_value}",
            f"平均年龄：{team.avg_age}",
            "部分核心球员(按综合评分降序)：",
        ]
        for p in players:
            stats_str = ""
            if p.stats:
                stats_str = " | ".join(f"{k}:{v}" for k, v in p.stats.items())
            lines.append(
                f"- {p.name} ({p.position}, 评分: {p.overall_rating}) : {stats_str}"
            )
        lines.append("")
        return "\n".join(lines)
