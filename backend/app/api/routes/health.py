from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/")
def read_root():
    return {
        "message": (
            "世界杯预测协助系统后端服务运行正常，"
            "请访问前端地址 (如 http://localhost:10087) "
            "或 API 文档 (http://localhost:10086/docs)"
        )
    }


@router.get("/health/live")
def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    settings = get_settings()
    checks = {"database": "ok", "llm_configured": settings.minimax_configured()}
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return {"status": "not_ready", "checks": {**checks, "database": str(exc)}}
    ready = checks["database"] == "ok"
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
