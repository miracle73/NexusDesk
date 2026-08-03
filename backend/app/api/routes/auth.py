import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Tenant, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()


def response_for(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_token(user.id, user.tenant_id), tenant_id=user.tenant_id, company_name=user.tenant.name)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    base = re.sub(r"[^a-z0-9]+", "-", data.company_name.lower()).strip("-") or "company"
    tenant = Tenant(name=data.company_name.strip(), slug=f"{base}-{str(uuid4())[:6]}")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password), tenant=tenant)
    db.add(user)
    db.commit()
    db.refresh(user)
    return response_for(user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return response_for(user)
