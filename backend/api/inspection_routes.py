"""Inspection real-data API routes."""

from flask import Blueprint, current_app, g, jsonify, request

from backend.middleware.security_middleware import require_auth
from backend.services.inspection_service import InspectionService
from backend.database.supabase_client import get_client, supabase_error_response

inspection_bp = Blueprint("inspection_bp", __name__, url_prefix="/api/inspection")


def _json(envelope, status=200):
    return jsonify(envelope), status


def _service():
    return InspectionService()


def _require_supabase():
    if current_app.config.get("TESTING"):
        return True, None
    sb = get_client()
    if not sb:
        body, status = supabase_error_response()
        return None, _json(body, status)
    return sb, None


@inspection_bp.route("/summary", methods=["GET"])
@require_auth
def summary():
    _, error = _require_supabase()
    if error:
        return error
    return _json(_service().summary())


@inspection_bp.route("/active-batches", methods=["GET"])
@require_auth
def active_batches():
    _, error = _require_supabase()
    if error:
        return error
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    return _json(_service().active_batches(limit=limit))


@inspection_bp.route("/batches/active", methods=["GET"])
@require_auth
def active_batches_for_sku():
    _, error = _require_supabase()
    if error:
        return error
    sku = request.args.get("sku") or request.args.get("barcode") or ""
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    return _json(_service().active_batches_for_sku(sku=sku, limit=limit))


@inspection_bp.route("/product-shortcuts", methods=["GET"])
@require_auth
def product_shortcuts():
    _, error = _require_supabase()
    if error:
        return error
    limit = min(max(int(request.args.get("limit", 8)), 1), 50)
    return _json(_service().product_shortcuts(limit=limit))


@inspection_bp.route("/recent-submissions", methods=["GET"])
@require_auth
def recent_submissions():
    _, error = _require_supabase()
    if error:
        return error
    limit = min(max(int(request.args.get("limit", 10)), 1), 50)
    return _json(_service().recent_submissions(limit=limit))


@inspection_bp.route("/submit", methods=["POST"])
@inspection_bp.route("/qc-submit", methods=["POST"])
@require_auth
def submit_qc():
    _, error = _require_supabase()
    if error:
        return error
    payload = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    actor = getattr(g, "current_user", {}) or {}
    files = {
        "photo": request.files.getlist("photo") or request.files.getlist("evidence"),
        "cooking_photo": request.files.getlist("cooking_photo"),
        "barcode_photo": request.files.getlist("barcode_photo"),
        "label_photo": request.files.getlist("label_photo"),
    }
    result = _service().submit_qc(payload, files=files, actor_id=actor.get("id") or actor.get("sub"))
    return _json(result, 200 if result.get("success") else 400)
