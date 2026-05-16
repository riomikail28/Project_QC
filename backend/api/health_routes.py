"""Production health endpoints."""

from flask import Blueprint, jsonify

from backend.database.supabase_client import validate_supabase_connection

health_bp = Blueprint("health_bp", __name__, url_prefix="/api/health")


@health_bp.route("/supabase", methods=["GET"])
def health_supabase():
    result = validate_supabase_connection()
    return jsonify(result), 200 if result.get("success") else 503
