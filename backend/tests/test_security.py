from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_and_tenant_claim() -> None:
    hashed = hash_password("secure-password")
    assert verify_password("secure-password", hashed)
    assert not verify_password("wrong-password", hashed)
    payload = decode_token(create_token("user-1", "tenant-1"))
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-1"
