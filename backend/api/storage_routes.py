from flask import Blueprint, g, request, jsonify
from backend.database.supabase_client import get_client
from backend.services.storage_service import upload_file_storage
from backend.middleware.security_middleware import require_auth

storage_bp = Blueprint("storage", __name__)
storage_alias_bp = Blueprint("storage_alias", __name__)

@storage_bp.route("/upload", methods=["POST"])
@require_auth
def upload_standalone():
    """Generic photo upload endpoint for standalone use."""
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400
    
    file = request.files["photo"]
    try:
        current_user = getattr(g, "current_user", {}) or {}
        staff_id = request.form.get("staff_id") or current_user.get("id") or current_user.get("sub") or "system"
        related_type = request.form.get("related_type") or request.form.get("category") or "inspection"
        related_id = request.form.get("related_id")
        uploaded = upload_file_storage(file, staff_id=staff_id, category=related_type, related_id=related_id)
        evidence = _record_evidence(uploaded, staff_id, related_type, related_id)
        return jsonify({
            "success": True,
            "data": {
                "url": uploaded.url,
                "public_url": uploaded.url,
                "storage_path": uploaded.storage_path,
                "bucket": uploaded.bucket,
                "evidence": evidence,
            },
            "url": uploaded.url,
            "public_url": uploaded.url,
            "storage_path": uploaded.storage_path,
            "bucket": uploaded.bucket,
            "message": "OK",
        })
    except ValueError as e:
        return jsonify({"success": False, "message": str(e), "error": str(e)}), 400
    except Exception as e:
        message = str(e) or "Upload gagal"
        return jsonify({"success": False, "message": message, "error": message}), 500


@storage_alias_bp.route("/api/upload", methods=["POST"])
@storage_alias_bp.route("/api/qc/upload", methods=["POST"])
@storage_alias_bp.route("/api/evidence", methods=["POST"])
@require_auth
def upload_standalone_alias():
    return upload_standalone()


def _record_evidence(uploaded, staff_id, related_type, related_id):
    sb = get_client()
    if not sb:
        return None
    payload = {
        "file_name": uploaded.file_name,
        "file_type": uploaded.file_type,
        "mime_type": uploaded.file_type,
        "file_size": uploaded.file_size,
        "bucket": uploaded.bucket,
        "storage_path": uploaded.storage_path,
        "public_url": uploaded.url,
        "uploaded_by": staff_id,
        "related_type": related_type,
        "related_id": related_id,
    }
    try:
        return (sb.table("qc_evidence").insert(payload).execute().data or [None])[0]
    except Exception:
        return None
