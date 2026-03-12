from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Any, Dict, Optional

from jose import jwt

from .settings import settings


def new_salt() -> str:
    return base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8").rstrip("=")


def _pbkdf2(password: str, salt: str, iterations: int = 200_000) -> str:
    salt_bytes = base64.urlsafe_b64decode(salt + "==")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations, dklen=32)
    return base64.urlsafe_b64encode(dk).decode("utf-8").rstrip("=")


def hash_password(password: str, salt: str) -> str:
    return _pbkdf2(password=password, salt=salt)


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    got = _pbkdf2(password=password, salt=salt)
    return hmac.compare_digest(got, password_hash)


def create_access_token(user_id: int, username: str, role: str) -> str:
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + settings.jwt_exp_seconds,
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer=settings.jwt_issuer)
    except Exception:
        return None
