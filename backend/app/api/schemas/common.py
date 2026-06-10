from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeamBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
    fifa_ranking: int | None
    group_name: str | None
    coach: str | None


class ScheduleItem(BaseModel):
    id: int | None = None
    group: str | None
    date: str | None
    time: str | None
    team1: str | None
    team2: str | None
    stadium: str | None
    status: str | None = "scheduled"
    home_score: int | None = None
    away_score: int | None = None
    minute: int | None = None
    period: str | None = None
    is_live: bool = False


class PlayerBrief(BaseModel):
    id: int
    name: str
    position: str | None
    age: int | None
    jersey_number: int | None = None
    is_key_player: bool = False
    team_name: str | None = None


class PlayerDetailedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int | None
    position: str | None
    club: str | None
    is_starter: bool
    description: str | None
    height: int | None
    weight: int | None
    preferred_foot: str | None
    birth_date: str | None
    overall_rating: int | None
    stats: dict | None
    honors: list | None
    transfers: list | None
    injuries: list | None
    injury_status: str | None = None
    injury_detail: str | None = None
    market_value: str | None = None
    form_rating: float | None = None


class TeamDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
    group_name: str | None
    fifa_ranking: int | None
    total_value: str | None
    avg_age: float | None
    coach: str | None
    formation: str | None
    logo_url: str | None
    founded: str | None
    city: str | None
    stadium: str | None
    capacity: str | None
    players: list[PlayerDetailedOut]


class TeamDetailResponse(BaseModel):
    status: str = "success"
    data: TeamDetail


class FifaPredictionRequest(BaseModel):
    team1_id: int
    team2_id: int


class FifaPredictionResponse(BaseModel):
    team1: str
    team2: str
    team1_win_rate: str
    draw_rate: str
    team2_win_rate: str
    analysis: str


class AnalysisRequest(BaseModel):
    team1_name: str
    team2_name: str
    force_refresh: bool = False


class AnalysisData(BaseModel):
    score: str
    total_goals: str
    red_cards: str
    penalties: str
    advice: str


class AnalysisResponse(BaseModel):
    status: str
    cached: bool
    data: AnalysisData


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


class LiveMatchOut(ScheduleItem):
    events: list | dict | None = None
    live_updated_at: datetime | None = None


class NewsArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str | None
    source: str | None
    published_at: datetime | None
    summary: str | None
    lang: str = "en"
    team_tags: list[str] | None = None
    for_my_team: bool = False
    for_sub_team: bool = False


class AgentAnalyzeRequest(BaseModel):
    team1_name: str
    team2_name: str
    mode: str = "pre_match"
    force_refresh: bool = False


class AgentStepOut(BaseModel):
    agent: str
    action: str
    output: str | dict | list | None = None


class ReasoningTraceStepOut(BaseModel):
    agent: str
    action: str
    summary: str


class AgentReportOut(BaseModel):
    summary: str
    predicted_score: str
    win_probability: dict[str, float]
    key_factors: list[str]
    injury_impact: str
    tactical_edge: str
    betting_notes: str
    confidence: float
    sources: list[dict]
    agent_steps: list[AgentStepOut] = []
    reasoning_trace: list[ReasoningTraceStepOut] = []
    betting_guide: dict = {}
    watch_points: list[str] = []
    mode: str | None = None
    news_digest: str = ""
    scenario_analysis: str = ""
    critic_notes: str = ""
    critic_issues: list[str] = []
    tactical_brief: dict = {}
    validation_warnings: list[str] = []
    live_context: str | None = None
    score: str | None = None
    total_goals: str | None = None
    red_cards: str | None = None
    penalties: str | None = None
    advice: str | None = None


class AgentAnalyzeResponse(BaseModel):
    status: str
    cached: bool = False
    run_id: int | None = None
    data: AgentReportOut
    validation_warnings: list[str] = []
    billing: dict | None = None


class AgentInsightOut(BaseModel):
    has_data: bool = False
    run_id: int | None = None
    summary: str = ""
    predicted_score: str = "-"
    confidence: float | None = None
    win_probability: dict[str, float] | None = None
    mode: str | None = None
    created_at: datetime | None = None


class AgentInsightPairRequest(BaseModel):
    team1: str
    team2: str
    mode: str = "pre_match"


class AgentBatchInsightRequest(BaseModel):
    pairs: list[AgentInsightPairRequest]
