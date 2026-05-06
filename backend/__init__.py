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


def create_app() -> Flask:
    """Flask application factory.

    Creates and configures the Flask app with:
    - CORS enabled for all origins
    - Three main route blueprints registered
    - Staff auth routes included
    """
    app = Flask(__name__)
    CORS(app)

    # Configure Uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    _ensure_upload_dirs(app)

    # Register route blueprints
    from backend.routes.temperature_routes import temperature_bp
    from backend.routes.batch_routes import batch_bp
    from backend.routes.qc_routes import qc_bp
    from backend.routes.ccp_routes import ccp_bp

    app.register_blueprint(temperature_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(qc_bp)
    app.register_blueprint(ccp_bp)

    # Register staff auth routes
    _register_staff_routes(app)

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
    """Register staff management routes directly on the app.

    These are thin route handlers that delegate to the staff_manager skill.
    """
    from flask import request, jsonify
    from backend.skills.staff_manager import login, list_staff, create_staff, delete_staff

    @app.route("/api/staff/login", methods=["POST"])
    def staff_login():
        data = request.json
        try:
            result = login(data.get("username", ""), data.get("password", ""))
            return jsonify(result)
        except ValueError as e:
            return jsonify({"detail": str(e)}), 401
        except Exception as e:
            return jsonify({"detail": f"Login error: {str(e)}"}), 500

    @app.route("/api/staff", methods=["GET"])
    def staff_list():
        return jsonify(list_staff())

    @app.route("/api/staff", methods=["POST"])
    def staff_create():
        data = request.json
        try:
            result = create_staff(
                username=data.get("username"),
                password=data.get("password"),
                role=data.get("role", "staff"),
            )
            return jsonify(result), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/staff/<staff_id>", methods=["DELETE"])
    def staff_delete(staff_id):
        success = delete_staff(staff_id)
        if success:
            return jsonify({"message": "Staff deleted successfully"})
        return jsonify({"error": "Failed to delete staff"}), 500
