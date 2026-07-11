"""
Authentication, authorization, and request hardening.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from flask import Flask, current_app, g, jsonify, request

logger = logging.getLogger("qc.security")


PUBLIC_ENDPOINTS = {
    "home",
    "staff_login",
    "health_check",
    "static",
}


class AuthError(Exception):
    """Raised for authentication and authorization failures."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class SecurityMiddleware:
    """Small JWT auth provider with login rate limiting."""

    def __init__(self, app: Flask | None = None):
        self.secret_key = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
        self.issuer = os.getenv("JWT_ISSUER", "qc-traceability-api")
        self.access_token_minutes = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "480"))
        self.failed_logins: dict[str, deque[float]] = defaultdict(deque)
        self.max_login_attempts = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
        self.login_window_seconds = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
        self.revoked_jti: set[str] = set()
        # Optional session-store counters for distributed rate limiting
        try:
            from backend.services.session_store import get_session_store

            self.session_store = get_session_store()
        except Exception:
            self.session_store = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if not self.secret_key:
            if app.config.get("TESTING"):
                self.secret_key = "test-secret-change-me"
            elif os.getenv("VERCEL") or os.getenv("FLASK_ENV") == "production":
                raise RuntimeError("JWT_SECRET_KEY or SECRET_KEY must be configured in production")
            else:
                self.secret_key = "local-dev-secret-change-me"
                logger.warning("JWT_SECRET_KEY/SECRET_KEY not set; using local development secret.")

        app.extensions["security"] = self
        app.before_request(self._load_authenticated_user)
        app.before_request(self._limit_request_size)
        app.after_request(self._security_headers)

    def generate_token(self, user: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user["id"]),
            "user_id": str(user["id"]),
            "username": user["username"],
            "role": user.get("role", "staff"),
            "name": user.get("name") or user.get("full_name") or user["username"],
            "iss": self.issuer,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=self.access_token_minutes),
            "jti": secrets.token_urlsafe(24),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.PyJWTError as exc:
            logger.info("JWT rejected: %s", exc)
            return None
        # Check session-store revoked jti set when available
        jti = payload.get("jti")
        if self.session_store and jti:
            try:
                if self.session_store.sismember("revoked_access_jti", jti):
                    return None
            except Exception:
                pass

        if jti and jti in self.revoked_jti:
            return None
        return payload

    def register_failed_login(self, identity: str) -> None:
        # Prefer session-store counter for distributed deployments
        if self.session_store:
            key = f"login:{identity}"
            try:
                cnt = self.session_store.incr(key)
                # set expiry window on first increment
                if cnt == 1:
                    self.session_store.expire(key, self.login_window_seconds)
            except Exception:
                pass
            return

        bucket = self.failed_logins[identity]
        now = time.time()
        bucket.append(now)
        self._trim_bucket(bucket, now)

    def clear_failed_logins(self, identity: str) -> None:
        if self.session_store:
            try:
                self.session_store.delete(f"login:{identity}")
            except Exception:
                pass
            self.failed_logins.pop(identity, None)
            return
        self.failed_logins.pop(identity, None)

    def is_login_limited(self, identity: str) -> bool:
        if self.session_store:
            try:
                val = int(self.session_store.get(f"login:{identity}") or 0)
                return val >= self.max_login_attempts
            except Exception:
                pass

        bucket = self.failed_logins[identity]
        now = time.time()
        self._trim_bucket(bucket, now)
        return len(bucket) >= self.max_login_attempts

    def _trim_bucket(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.login_window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    def _load_authenticated_user(self):
        g.current_user = None
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ").strip()
        payload = self.verify_token(token)
        if payload:
            g.current_user = payload
            # Block demo_admin from mutating methods (POST, PUT, PATCH, DELETE)
            if payload.get("username") == "demo_admin" and request.method in ("POST", "PUT", "PATCH", "DELETE"):
                # Exception: auth/login/logout endpoints
                if not request.path.endswith("/login") and not request.path.endswith("/logout"):
                    return jsonify({"error": "Akun Demo Admin hanya memiliki akses lihat-saja (read-only)."}), 403
        return None

    def _limit_request_size(self):
        max_bytes = int(os.getenv("MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))
        if request.content_length and request.content_length > max_bytes:
            return jsonify({"error": "Request too large"}), 413
        return None

    def _security_headers(self, response):
        supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        connect_sources = ["'self'", "http://localhost:5000", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdnjs.cloudflare.com"]
        if supabase_url:
            connect_sources.append(supabase_url)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=()")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob: https:; "
            f"connect-src {' '.join(connect_sources)}; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        return response


def _is_public_request() -> bool:
    return request.endpoint in PUBLIC_ENDPOINTS or request.method == "OPTIONS"


def require_auth(func: Callable):
    """Require a valid JWT for an endpoint."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if _is_public_request():
            return func(*args, **kwargs)
        if not getattr(g, "current_user", None):
            raise AuthError("Authentication required", 401)
        return func(*args, **kwargs)

    return wrapper


def require_role(*roles: str):
    """Require one of the listed roles. Admin always passes."""

    allowed_roles = {_normalize_role(role) for role in roles}

    def decorator(func: Callable):
        @wraps(func)
        @require_auth
        def wrapper(*args, **kwargs):
            user = g.current_user or {}
            role = _normalize_role(user.get("role", "qc_staff"))
            admin_roles = {"admin", "supervisor", "manager"}
            if role not in admin_roles and role not in allowed_roles:
                raise AuthError("Insufficient permissions", 403)
            if role in {"supervisor", "manager"} and "admin" not in allowed_roles and role not in allowed_roles:
                raise AuthError("Insufficient permissions", 403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _normalize_role(role: str | None) -> str:
    value = str(role or "qc_staff").strip().lower()
    return {"staff": "qc_staff", "qc": "qc_staff", "super_admin": "admin"}.get(value, value)


def get_security() -> SecurityMiddleware:
    security = current_app.extensions.get("security")
    if not security:
        raise RuntimeError("Security middleware is not configured")
    return security
