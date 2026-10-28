from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

passwords = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(value: str) -> str:
    return passwords.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return passwords.verify(value, hashed)


def create_token(user_id: str, tenant_id: str, email: str = "") -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "tenant_id": tenant_id, "email": email, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
