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

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import logging
logger = logging.getLogger("qc.backend")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ADMIN_DIR = os.path.join(FRONTEND_DIR, "admin")
STAFF_DIR = os.path.join(FRONTEND_DIR, "staff")


def create_app() -> Flask:
    """Flask application factory."""
    app = Flask(__name__)
    allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")
    CORS(app, origins=[origin.strip() for origin in allowed_origins if origin.strip()])

    from backend.middleware.security_middleware import SecurityMiddleware
    from backend.services.error_handlers import register_error_handlers
    SecurityMiddleware(app)
    register_error_handlers(app)

    # Init metrics middleware
    try:
        from backend.middleware.metrics_middleware import init_metrics, metrics_bp
        init_metrics(app)
        app.register_blueprint(metrics_bp)
    except Exception as e:
        logger.warning("Metrics middleware not initialized: %s", e)

    # Configure Uploads
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    _ensure_upload_dirs(app)

    # Register route blueprints
    from backend.api.temperature_routes import monitoring_bp
    from backend.api.batch_routes import batch_bp
    from backend.api.qc_routes import qc_bp
    from backend.api.ccp_routes import ccp_bp
    from backend.api.admin_routes import admin_bp
    from backend.api.dashboard_routes import dashboard_bp
    from backend.api.storage_routes import storage_alias_bp, storage_bp
    from backend.api.inspection_routes import inspection_bp
    from backend.api.profile_routes import profile_bp
    from backend.api.staff_routes import staff_bp
    from backend.api.facility_routes import facility_bp

    # Register DI services (repository + service) for use by routes
    try:
        from backend.core.di import register
        from backend.database.supabase_client import get_client
        from backend.repositories.qc_repository import QCRepository
        from backend.services.qc_service import QCService

        def _qc_service_provider():
            sb = get_client()
            repo = QCRepository(sb)

            # storage wrapper
            try:
                from backend.services.storage_service import delete_photo as _delete_fn
                from backend.services.storage_service import upload_file_storage as _upload_file_fn
                from backend.services.storage_service import upload_photo as _upload_fn

                class _StorageWrap:
                    def upload_photo(self, data, filename):
                        return _upload_fn(data, filename)
                    def upload_file_storage(self, file_storage, staff_id="system"):
                        return _upload_file_fn(file_storage, staff_id=staff_id)
                    def delete_photo(self, storage_path):
                        return _delete_fn(storage_path)

                storage = _StorageWrap()
            except Exception:
                storage = None

            try:
                from backend.services import audit_service as audit_mod
            except Exception:
                audit_mod = None

            return QCService(repo, storage_service=storage, audit_service=audit_mod, external_sync=None)

        register("qc_service", _qc_service_provider)
    except Exception as e:
        logger.warning("Failed to register qc_service in DI: %s", e)

    app.register_blueprint(monitoring_bp)
    app.register_blueprint(batch_bp)
    app.register_blueprint(qc_bp)
    app.register_blueprint(ccp_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(storage_bp, url_prefix="/api/storage")
    app.register_blueprint(storage_alias_bp)
    app.register_blueprint(inspection_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(facility_bp)

    # Frontend routes for Vercel/serverless deployment.
    @app.route("/")
    def home():
        return send_from_directory(STAFF_DIR, "login.html")

    @app.route("/api")
    def api_home():
        return {
            "message": "QC Central Kitchen API Running",
            "version": "2.0.0",
            "docs": "/api/qc/health",
        }

    @app.route("/admin")
    @app.route("/admin/")
    def admin_index():
        return send_from_directory(ADMIN_DIR, "admin_panel.html")

    @app.route("/admin/<path:filename>")
    def admin_file(filename):
        if filename == "admin_panel.html":
            return send_from_directory(ADMIN_DIR, "admin_panel.html")
        return send_from_directory(ADMIN_DIR, filename)

    @app.route("/staff/")
    def staff_index():
        return send_from_directory(STAFF_DIR, "index.html")

    @app.route("/staff/<path:filename>")
    def staff_file(filename):
        return send_from_directory(STAFF_DIR, filename)

    @app.route("/<path:filename>.html")
    def frontend_html(filename):
        if filename == "check":
            return send_from_directory(STAFF_DIR, "inspection.html")
        admin_path = os.path.join(ADMIN_DIR, f"{filename}.html")
        if os.path.exists(admin_path):
            return send_from_directory(ADMIN_DIR, f"{filename}.html")
        return send_from_directory(STAFF_DIR, f"{filename}.html")

    @app.route("/css/<path:filename>")
    def frontend_css(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)

    @app.route("/styles/<path:filename>")
    def frontend_styles(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "styles"), filename)

    @app.route("/js/<path:filename>")
    def frontend_js(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

    @app.route("/assets/<path:filename>")
    def frontend_assets(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "assets"), filename)

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(FRONTEND_DIR, "manifest.json")

    @app.route("/sw.js")
    def service_worker():
        return send_from_directory(FRONTEND_DIR, "sw.js")

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
