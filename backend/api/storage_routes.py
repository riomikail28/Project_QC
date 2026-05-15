from flask import Blueprint, request, jsonify
from backend.services.storage_service import upload_photo
from backend.api.auth_middleware import token_required

storage_bp = Blueprint("storage", __name__)

@storage_bp.route("/upload", methods=["POST"])
@token_required
def upload_standalone(current_user):
    """Generic photo upload endpoint for standalone use."""
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400
    
    file = request.files["photo"]
    try:
        url = upload_photo(file.read(), file.filename, staff_id=current_user.get("id", "system"))
        return jsonify({"success": True, "url": url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
