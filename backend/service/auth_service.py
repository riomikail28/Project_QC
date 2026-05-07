"""Auth service: refresh tokens, rotation, session invalidation."""
import os
import json
from datetime import datetime, timedelta, timezone
import secrets
import jwt
from typing import Optional, Tuple

from backend.service.redis_client import get_redis
from backend.middleware.security_middleware import get_security

REDIS_PREFIX = "refresh"


class AuthService:
    def __init__(self):
        self.redis = get_redis()
        self.secret = os.environ.get("JWT_SECRET_KEY")
        self.issuer = os.environ.get("JWT_ISSUER", "qc-traceability-api")
        self.refresh_days = int(os.environ.get("REFRESH_TOKEN_DAYS", "14"))

    def _make_refresh_jti(self) -> str:
        return secrets.token_urlsafe(32)

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        jti = self._make_refresh_jti()
        exp = now + timedelta(days=self.refresh_days)
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "iss": self.issuer,
            "iat": now.timestamp(),
            "exp": exp.timestamp(),
        }
        token = jwt.encode(payload, self.secret, algorithm="HS256")
        # store mapping in redis for rotation/validation
        key = f"{REDIS_PREFIX}:{jti}"
        self.redis.set(key, json.dumps({"user_id": user_id, "created_at": now.isoformat()}), ex=self.refresh_days * 24 * 3600)
        return token

    def verify_refresh_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"], issuer=self.issuer, options={"require": ["exp", "sub", "jti"]})
        except jwt.PyJWTError:
            return None
        jti = payload.get("jti")
        if not jti:
            return None
        key = f"{REDIS_PREFIX}:{jti}"
        data = self.redis.get(key)
        if not data:
            return None
        try:
            info = json.loads(data)
        except Exception:
            return None
        return {"user_id": info.get("user_id"), "jti": jti}

    def rotate_refresh_token(self, old_token: str) -> Optional[str]:
        info = self.verify_refresh_token(old_token)
        if not info:
            return None
        old_jti = info["jti"]
        user_id = info["user_id"]
        # delete old
        self.redis.delete(f"{REDIS_PREFIX}:{old_jti}")
        # create new
        new_token = self.create_refresh_token(user_id)
        return new_token

    def invalidate_refresh_token(self, token: str) -> bool:
        info = self.verify_refresh_token(token)
        if not info:
            return False
        jti = info["jti"]
        self.redis.delete(f"{REDIS_PREFIX}:{jti}")
        return True

    def revoke_access_jti(self, jti: str):
        # Mark access token jti as revoked in SecurityMiddleware
        try:
            sec = get_security()
            sec.revoked_jti.add(jti)
        except Exception:
            pass

        # Also persist to Redis set for cross-process revocation
        try:
            r = get_redis()
            r.sadd("revoked_access_jti", jti)
        except Exception:
            pass
        return None
