"""Security unit tests."""
from app.core.security import (
    create_access_token,
    hash_password,
    safe_decode,
    verify_password,
    encrypt_at_rest,
    decrypt_at_rest,
)
from app.core.permissions import has_permission, permissions_for_role


def test_password_hash_and_verify():
    h = hash_password("StrongPass!234")
    assert verify_password("StrongPass!234", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    token = create_access_token("user-1", role="customer", permissions=["claim:create"])
    payload = safe_decode(token)
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"


def test_encrypt_at_rest():
    blob = encrypt_at_rest(b"sensitive")
    assert decrypt_at_rest(blob) == b"sensitive"


def test_rbac_customer_cannot_manage_users():
    assert has_permission("customer", "claim:create")
    assert not has_permission("customer", "user:manage")
    assert "system:backup" in permissions_for_role("super_admin")
