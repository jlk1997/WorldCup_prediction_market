from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.common import (
    FifaPredictionRequest,
    FifaPredictionResponse,
)
from app.core.exceptions import AppError, NotFoundError, ServiceUnavailableError
from app.db.repositories.team_repository import TeamRepository
from app.services.fifa_predictor import predict_by_fifa_ranking

router = APIRouter(prefix="/api", tags=["predictions"])


@router.post("/predict", response_model=FifaPredictionResponse)
def predict_match(req: FifaPredictionRequest, db: Session = Depends(get_db)):
    try:
        repo = TeamRepository(db)
        t1 = repo.get_by_id(req.team1_id)
        t2 = repo.get_by_id(req.team2_id)
        if not t1 or not t2:
            raise NotFoundError("球队未找到")
        return predict_by_fifa_ranking(t1, t2)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(str(exc)) from exc


@router.post("/predict/analysis")
async def predict_analysis_deprecated():
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=410,
        content={
            "status": "error",
            "message": "该接口已废弃，请登录后使用 POST /api/agent/analyze",
        },
    )
