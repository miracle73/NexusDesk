"""Immediate email/password signup and JWT login: no OTP, no email verification."""
import re
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.core.security import create_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.store import repository

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest) -> TokenResponse:
    if repository.get_user(data.email):
        raise HTTPException(409, "Email already registered")
    base = re.sub(r"[^a-z0-9]+", "-", data.company_name.lower()).strip("-") or "company"
    tenant = repository.create_tenant(data.company_name.strip(), f"{base}-{str(uuid4())[:6]}")
    user = repository.create_user(data.email, hash_password(data.password), tenant["id"])
    return TokenResponse(
        access_token=create_token(user["id"], tenant["id"], user["email"]),
        tenant_id=tenant["id"],
        company_name=tenant["name"],
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest) -> TokenResponse:
    user = repository.get_user(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    tenant = repository.get_tenant(user["tenant_id"]) or {}
    return TokenResponse(
        access_token=create_token(user["id"], user["tenant_id"], user["email"]),
        tenant_id=user["tenant_id"],
        company_name=tenant.get("name", ""),
    )
