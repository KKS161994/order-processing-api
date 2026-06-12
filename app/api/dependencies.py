from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from fastapi import Depends, HTTPException,status
from app.db.session import get_db
from sqlalchemy.orm import Session

from app.models.user import User
from app.repository.user_repository import UserRepository
from app.security.tokens import TokenError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
        credentials : HTTPAuthorizationCredentials|None = Depends(bearer_scheme),
        db:Session = Depends(get_db),
)->User:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    user_id = payload["sub"]
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="user not found",
        )
    return user
