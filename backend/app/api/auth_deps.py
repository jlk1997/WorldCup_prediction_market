from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.db.models.commerce import User
from app.db.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

from .deps import get_db

_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    if not creds or creds.scheme.lower() != "bearer":
        return None
    auth = AuthService(db)
    user_id = auth.decode_user_id(creds.credentials)
    user = UserRepository(db).get_by_id(user_id)
    if user and user.status != "active":
        return None
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if not user:
        raise UnauthorizedError()
    if user.status != "active":
        raise UnauthorizedError("账号已停用")
    return user
