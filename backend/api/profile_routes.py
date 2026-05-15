"""Profile real-data API routes."""

from flask import Blueprint, g, jsonify

from backend.middleware.security_middleware import require_auth
from backend.services.profile_service import ProfileService

profile_bp = Blueprint("profile_bp", __name__, url_prefix="/api/profile")


def _json(envelope, status=200):
    return jsonify(envelope), status


def _service():
    return ProfileService()


@profile_bp.route("/me", methods=["GET"])
@require_auth
def me():
    return _json(_service().me(getattr(g, "current_user", {}) or {}))


@profile_bp.route("/activity-summary", methods=["GET"])
@require_auth
def activity_summary():
    return _json(_service().activity_summary(getattr(g, "current_user", {}) or {}))
