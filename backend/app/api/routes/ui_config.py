from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_secret_in_production
from app.core.exceptions import NotFoundError, ServiceUnavailableError
from app.services.system_ui_config_service import SystemUiConfigService

router = APIRouter(prefix="/api/ui-config", tags=["ui-config"])


@router.get("/{config_key}")
def get_ui_config(config_key: str, db: Session = Depends(get_db)):
    try:
        cfg = SystemUiConfigService(db).get(config_key)
    except SQLAlchemyError:
        raise ServiceUnavailableError("配置暂不可用，请确认已执行数据库迁移") from None
    if cfg is None:
        raise NotFoundError(f"未找到配置 {config_key}")
    return cfg


@router.put("/admin/{config_key}")
def update_ui_config(
    config_key: str,
    body: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_secret_in_production),
):
    cfg = SystemUiConfigService(db).upsert(config_key, body)
    db.commit()
    return cfg
