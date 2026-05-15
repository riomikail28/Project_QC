"""Staff authentication and management routes."""

import logging
import os

import jwt
from flask import Blueprint, jsonify, request

from backend.middleware.security_middleware import get_security, require_auth, require_role
from backend.services.audit_service import write_audit
from backend.services.request_validation import LoginRequest, validate_model

logger = logging.getLogger("qc.routes.staff")

staff_bp = Blueprint("staff_bp", __name__)


@staff_bp.route("/api/staff/login", methods=["POST"])
def staff_login():
    data = request.get_json(silent=True) or {}
    login_data = validate_model(LoginRequest, data)
    identity = f"{request.remote_addr}:{login_data.username.lower()}"
    security = get_security()
    if security.is_login_limited(identity):
        return jsonify({"detail": "Too many login attempts"}), 429

    try:
        from backend.auth.staff_manager import login

        result = login(login_data.username, login_data.password)
        access_token = security.generate_token(result)

        try:
            from backend.services.auth_service import AuthService

            refresh_token = AuthService().create_refresh_token(result.get("id"))
        except Exception:
            refresh_token = None

        resp = jsonify({
            "id": result.get("id"),
            "username": result.get("username"),
            "role": result.get("role"),
            "token": access_token,
        })
        if refresh_token:
            cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
            secure_flag = False if os.environ.get("DEV_HTTP", "false").lower() in ("1", "true") else True
            resp.set_cookie(
                cookie_name,
                refresh_token,
                httponly=True,
                secure=secure_flag,
                samesite="Lax",
                max_age=int(os.environ.get("REFRESH_TOKEN_DAYS", "14")) * 24 * 3600,
                path="/api/staff",
            )

        security.clear_failed_logins(identity)
        write_audit("login", "staff_account", str(result.get("id")), after={"username": result.get("username")})
        return resp
    except ValueError as exc:
        security.register_failed_login(identity)
        return jsonify({"detail": str(exc)}), 401
    except Exception as exc:
        logger.exception("Login exception")
        return jsonify({"detail": "Internal Server Error", "message": str(exc)}), 500


@staff_bp.route("/api/staff", methods=["GET"])
@require_role("admin")
def staff_list():
    from backend.auth.staff_manager import list_staff

    return jsonify(list_staff())


@staff_bp.route("/api/staff/refresh", methods=["POST"])
def staff_refresh():
    from backend.auth.staff_manager import get_staff_by_id
    from backend.services.auth_service import AuthService

    cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
    token = request.cookies.get(cookie_name)
    if not token:
        return jsonify({"detail": "Refresh token missing"}), 401

    auth_service = AuthService()
    old_payload = auth_service.verify_refresh_token(token)
    if not old_payload:
        return jsonify({"detail": "Invalid refresh token"}), 401

    new_refresh = auth_service.rotate_refresh_token(token)
    if not new_refresh:
        return jsonify({"detail": "Invalid refresh token"}), 401

    user_id = old_payload.get("sub")
    try:
        user = get_staff_by_id(user_id) if user_id else None
    except Exception:
        user = None

    access = get_security().generate_token(user or {"id": user_id, "username": user_id, "role": "staff"})
    resp = jsonify({"token": access})
    secure_flag = False if os.environ.get("DEV_HTTP", "false").lower() in ("1", "true") else True
    resp.set_cookie(
        cookie_name,
        new_refresh,
        httponly=True,
        secure=secure_flag,
        samesite="Lax",
        max_age=int(os.environ.get("REFRESH_TOKEN_DAYS", "14")) * 24 * 3600,
        path="/api/staff",
    )
    return resp


@staff_bp.route("/api/staff/logout", methods=["POST"])
@require_auth
def staff_logout():
    from backend.services.auth_service import AuthService

    cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
    token = request.cookies.get(cookie_name)
    auth_service = AuthService()
    if token:
        auth_service.invalidate_refresh_token(token)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(access_token, os.environ.get("JWT_SECRET_KEY"), algorithms=["HS256"], options={})
            jti = payload.get("jti")
            if jti:
                auth_service.revoke_access_jti(jti)
        except Exception:
            pass

    resp = jsonify({"success": True})
    resp.delete_cookie(cookie_name, path="/api/staff")
    return resp


@staff_bp.route("/api/staff", methods=["POST"])
@require_role("admin")
def staff_create():
    from backend.auth.staff_manager import create_staff

    try:
        staff = create_staff(request.get_json(silent=True) or {})
        write_audit("create", "staff_account", str(staff.get("id")) if staff else None, after=staff)
        return jsonify(staff)
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400


@staff_bp.route("/api/staff/<staff_id>", methods=["PATCH", "PUT", "DELETE"])
@require_role("admin")
def staff_detail(staff_id):
    from backend.auth.staff_manager import delete_staff, update_staff

    if request.method in ("PATCH", "PUT"):
        try:
            updated = update_staff(staff_id, request.get_json(silent=True) or {})
            write_audit("update", "staff_account", staff_id, after=updated)
            return jsonify(updated)
        except ValueError as exc:
            return jsonify({"detail": str(exc)}), 400

    success = delete_staff(staff_id)
    write_audit("delete", "staff_account", staff_id, after={"success": success})
    return jsonify({"success": success})
