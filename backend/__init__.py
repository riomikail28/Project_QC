"""
QC Central Kitchen - Backend Package
=====================================
Flask application factory with Blueprint registration.

Architecture:
  backend/
    ├── routes/          → Flask Blueprints (HTTP layer)
    ├── service/         → Business logic (validation, scoring)
    ├── database/        → Supabase client singleton
    └── skills/          → Domain-specific modules (product catalog, staff, etc.)
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
import os


import logging

logger = logging.getLogger("qc.backend")


def create_app() -> Flask:
    """Flask application factory."""
    app = Flask(__name__)
    CORS(app)

    # Configure Uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    _ensure_upload_dirs(app)

    # Register route blueprints
    from backend.routes.temperature_routes import monitoring_bp
    from backend.routes.batch_routes import batch_bp
    from backend.routes.qc_routes import qc_bp
    from backend.routes.ccp_routes import ccp_bp

    app.register_blueprint(monitoring_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(qc_bp)
    app.register_blueprint(ccp_bp)

    # Register staff auth routes
    try:
        _register_staff_routes(app)
    except Exception as e:
        logger.error("Failed to register staff routes: %s", e)

    # Health endpoint at root
    @app.route("/")
    def home():
        return {
            "message": "QC Central Kitchen API Running",
            "version": "2.0.0",
            "docs": "/api/qc/health",
        }

    # Serve uploaded files (for development)
    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app


def _ensure_upload_dirs(app: Flask):
    """Ensure upload directories exist."""
    # Skip directory creation if running on Vercel (Read-only filesystem)
    if os.environ.get('VERCEL'):
        return

    paths = [
        os.path.join(app.config['UPLOAD_FOLDER'], 'qc_photos'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'reports')
    ]
    for path in paths:
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        except OSError:
            # Fallback for other read-only environments
            pass


def _register_staff_routes(app: Flask):
    """Register staff management routes directly on the app."""
    from flask import request, jsonify
    
    try:
        from backend.skills.staff_manager import login, list_staff, create_staff, delete_staff
    except ImportError as e:
        logger.error("Could not import staff_manager: %s", e)
        return

    @app.route("/api/staff/login", methods=["POST"])
    def staff_login():
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"detail": "Invalid JSON body"}), 400
            
        try:
            result = login(data.get("username", ""), data.get("password", ""))
            return jsonify(result)
        except ValueError as e:
            return jsonify({"detail": str(e)}), 401
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            logger.error("Login exception: %s\n%s", e, err_msg)
            return jsonify({
                "detail": "Internal Server Error",
                "message": str(e),
                "trace": err_msg if os.environ.get('VERCEL') else None
            }), 500

    @app.route("/api/staff", methods=["GET"])
    def staff_list():
        return jsonify(list_staff())

    @app.route("/api/staff", methods=["POST"])
    def staff_create():
        try:
            return jsonify(create_staff(request.json))
        except ValueError as e:
            return jsonify({"detail": str(e)}), 400

    @app.route("/api/staff/<staff_id>", methods=["DELETE"])
    def staff_delete(staff_id):
        return jsonify({"success": delete_staff(staff_id)})

    # --- Facility Management Routes ---
    @app.route("/api/facility/structure", methods=["GET"])
    def facility_structure():
        from backend.skills.facility_manager import get_monitoring_structure
        return jsonify(get_monitoring_structure())

    @app.route("/api/facility/rooms", methods=["GET", "POST"])
    def facility_rooms():
        from backend.skills.facility_manager import list_rooms, add_room
        if request.method == "POST":
            data = request.json
            return jsonify(add_room(data.get("name"), data.get("description", "")))
        return jsonify(list_rooms())

    @app.route("/api/facility/rooms/<room_id>", methods=["DELETE"])
    def facility_room_delete(room_id):
        from backend.skills.facility_manager import delete_room
        return jsonify({"success": delete_room(room_id)})

    @app.route("/api/facility/devices", methods=["GET", "POST"])
    def facility_devices():
        from backend.skills.facility_manager import list_devices, add_device
        if request.method == "POST":
            data = request.json
            return jsonify(add_device(
                data.get("room_id"), 
                data.get("name"), 
                data.get("type"), 
                data.get("threshold", 5.0)
            ))
        return jsonify(list_devices(request.args.get("room_id")))

    @app.route("/api/facility/devices/<device_id>", methods=["DELETE"])
    def facility_device_delete(device_id):
        from backend.skills.facility_manager import delete_device
        return jsonify({"success": delete_device(device_id)})
