from pydantic import BaseModel, Field


class ProfileSetupRequest(BaseModel):
    main_team_id: int
    secondary_team_id: int | None = None
    player_ids: list[int] = Field(default_factory=list, max_length=3)


class ProfilePatchRequest(BaseModel):
    main_team_id: int | None = None
    secondary_team_id: int | None = None
    player_ids: list[int] | None = Field(default=None, max_length=3)


class CheerSubmitRequest(BaseModel):
    match_id: int
    team_id: int


class QuizAnswerRequest(BaseModel):
    answer_index: int = Field(ge=0, le=3)
