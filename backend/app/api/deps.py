from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.store import repository

bearer = HTTPBearer()


class Principal:
    def __init__(self, user_id: str, tenant_id: str, email: str) -> None:
        self.id = user_id
        self.tenant_id = tenant_id
        self.email = email


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> Principal:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    email, tenant_id = payload.get("email"), payload.get("tenant_id")
    if not email or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = repository.get_user(email)
    if not user or user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return Principal(user["id"], tenant_id, email)
