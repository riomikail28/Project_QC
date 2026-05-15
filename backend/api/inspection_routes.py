"""Inspection real-data API routes."""

from flask import Blueprint, jsonify, request

from backend.middleware.security_middleware import require_auth
from backend.services.inspection_service import InspectionService

inspection_bp = Blueprint("inspection_bp", __name__, url_prefix="/api/inspection")


def _json(envelope, status=200):
    return jsonify(envelope), status


def _service():
    return InspectionService()


@inspection_bp.route("/summary", methods=["GET"])
@require_auth
def summary():
    return _json(_service().summary())


@inspection_bp.route("/active-batches", methods=["GET"])
@require_auth
def active_batches():
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    return _json(_service().active_batches(limit=limit))


@inspection_bp.route("/product-shortcuts", methods=["GET"])
@require_auth
def product_shortcuts():
    limit = min(max(int(request.args.get("limit", 8)), 1), 50)
    return _json(_service().product_shortcuts(limit=limit))


@inspection_bp.route("/recent-submissions", methods=["GET"])
@require_auth
def recent_submissions():
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    return _json(_service().recent_submissions(limit=limit))
