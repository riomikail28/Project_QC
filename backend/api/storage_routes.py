from flask import Blueprint, g, request, jsonify
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
        uploaded = upload_file_storage(file, staff_id=current_user.get("id", "system"))
        return jsonify({
            "success": True,
            "url": uploaded.url,
            "storage_path": uploaded.storage_path,
            "bucket": uploaded.bucket,
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@storage_alias_bp.route("/api/upload", methods=["POST"])
@storage_alias_bp.route("/api/qc/upload", methods=["POST"])
@storage_alias_bp.route("/api/evidence", methods=["POST"])
@require_auth
def upload_standalone_alias():
    return upload_standalone()
