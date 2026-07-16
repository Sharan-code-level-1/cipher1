"""Cryptography, password hashing, and JWT helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    *,
    role: str,
    permissions: list[str] | None = None,
    expires_delta: Optional[timedelta] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "permissions": permissions or [],
        "type": "access",
        "jti": str(uuid4()),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, *, family_id: Optional[str] = None) -> tuple[str, str, str]:
    """Return (token, jti, family_id). Family supports rotation reuse detection."""
    settings = get_settings()
    jti = str(uuid4())
    family = family_id or str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": jti,
        "family": family,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, family


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def safe_decode(token: str) -> Optional[Dict[str, Any]]:
    try:
        return decode_token(token)
    except JWTError:
        return None


def generate_secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def encrypt_at_rest(plaintext: bytes) -> bytes:
    """AES-256-GCM encryption for sensitive fields / files."""
    settings = get_settings()
    key = hashlib.sha256(settings.aes_master_key.encode("utf-8")).digest()
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_at_rest(blob: bytes) -> bytes:
    settings = get_settings()
    key = hashlib.sha256(settings.aes_master_key.encode("utf-8")).digest()
    nonce, ciphertext = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def b64_encrypt(plaintext: str) -> str:
    return base64.urlsafe_b64encode(encrypt_at_rest(plaintext.encode("utf-8"))).decode("ascii")


def b64_decrypt(token: str) -> str:
    return decrypt_at_rest(base64.urlsafe_b64decode(token.encode("ascii"))).decode("utf-8")
