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

from flask import Flask, send_from_directory, g
from flask_cors import CORS
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import logging
import jwt

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

    from backend.middleware.security_middleware import SecurityMiddleware, require_role
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
                from backend.services.storage_service import upload_photo as _upload_fn

                class _StorageWrap:
                    def upload_photo(self, data, filename):
                        return _upload_fn(data, filename)

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

    # Register staff auth routes
    try:
        _register_staff_routes(app)
    except Exception as e:
        logger.error("Failed to register staff routes: %s", e)

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

    @app.route("/admin/")
    def admin_index():
        return send_from_directory(ADMIN_DIR, "admin_panel.html")

    @app.route("/admin/<path:filename>")
    def admin_file(filename):
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


def _register_staff_routes(app: Flask):
    """Register staff management routes directly on the app."""
    from flask import request, jsonify
    from backend.middleware.security_middleware import get_security, require_auth, require_role
    from backend.services.audit_service import write_audit
    from backend.services.request_validation import LoginRequest, request_payload, validate_model
    
    try:
        from backend.auth.staff_manager import login, list_staff, create_staff, delete_staff, update_staff
    except ImportError as e:
        logger.error("Could not import staff_manager: %s", e)
        return

    @app.route("/api/staff/login", methods=["POST"])
    def staff_login():
        data = request.get_json(silent=True) or {}
        login_data = validate_model(LoginRequest, data)
        identity = f"{request.remote_addr}:{login_data.username.lower()}"
        security = get_security()
        if security.is_login_limited(identity):
            return jsonify({"detail": "Too many login attempts"}), 429

        try:
            result = login(login_data.username, login_data.password)
            access_token = security.generate_token(result)

            # Create refresh token and set as secure HttpOnly cookie
            try:
                from backend.services.auth_service import AuthService
                authsvc = AuthService()
                refresh_token = authsvc.create_refresh_token(result.get("id"))
            except Exception:
                refresh_token = None

            resp = jsonify({"id": result.get("id"), "username": result.get("username"), "role": result.get("role"), "token": access_token})
            if refresh_token:
                cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
                secure_flag = False if os.environ.get("DEV_HTTP", "false").lower() in ("1", "true") else True
                resp.set_cookie(cookie_name, refresh_token, httponly=True, secure=secure_flag, samesite='Lax', max_age=int(os.environ.get("REFRESH_TOKEN_DAYS", "14")) * 24 * 3600, path='/api/staff')

            security.clear_failed_logins(identity)
            write_audit("login", "staff_account", str(result.get("id")), after={"username": result.get("username")})
            return resp
        except ValueError as e:
            security.register_failed_login(identity)
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
    @require_role("admin")
    def staff_list():
        return jsonify(list_staff())

    @app.route('/api/staff/refresh', methods=['POST'])
    def staff_refresh():
        from backend.services.auth_service import AuthService
        cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
        token = request.cookies.get(cookie_name)
        if not token:
            return jsonify({"detail": "Refresh token missing"}), 401
        authsvc = AuthService()
        new_refresh = authsvc.rotate_refresh_token(token)
        if not new_refresh:
            return jsonify({"detail": "Invalid refresh token"}), 401
        # create new access token
        try:
            payload = jwt.decode(new_refresh, os.environ.get("JWT_SECRET_KEY"), algorithms=["HS256"], options={"verify_signature": False})
            user_id = payload.get('sub')
        except Exception:
            user_id = None
        # For safety, fetch user info via staff manager
        try:
            from backend.auth.staff_manager import get_staff_by_id
            user = get_staff_by_id(user_id) if user_id else None
        except Exception:
            user = None
        security = get_security()
        access = security.generate_token(user or {"id": user_id, "username": user_id, "role": "staff"})
        resp = jsonify({"token": access})
        secure_flag = False if os.environ.get("DEV_HTTP", "false").lower() in ("1", "true") else True
        resp.set_cookie(cookie_name, new_refresh, httponly=True, secure=secure_flag, samesite='Lax', max_age=int(os.environ.get("REFRESH_TOKEN_DAYS", "14")) * 24 * 3600, path='/api/staff')
        return resp

    @app.route('/api/staff/logout', methods=['POST'])
    @require_auth
    def staff_logout():
        from backend.services.auth_service import AuthService
        cookie_name = os.environ.get("REFRESH_TOKEN_COOKIE", "refresh_token")
        token = request.cookies.get(cookie_name)
        authsvc = AuthService()
        if token:
            authsvc.invalidate_refresh_token(token)
        # Revoke current access token jti
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.removeprefix('Bearer ').strip()
            try:
                payload = jwt.decode(token, os.environ.get("JWT_SECRET_KEY"), algorithms=["HS256"], options={})
                jti = payload.get('jti')
                if jti:
                    authsvc.revoke_access_jti(jti)
            except Exception:
                pass
        resp = jsonify({"success": True})
        resp.delete_cookie(cookie_name, path='/api/staff')
        return resp

    @app.route("/api/staff", methods=["POST"])
    @require_role("admin")
    def staff_create():
        try:
            staff = create_staff(request.get_json(silent=True) or {})
            write_audit("create", "staff_account", str(staff.get("id")) if staff else None, after=staff)
            return jsonify(staff)
        except ValueError as e:
            return jsonify({"detail": str(e)}), 400

    @app.route("/api/staff/<staff_id>", methods=["PATCH", "PUT", "DELETE"])
    @require_role("admin")
    def staff_detail(staff_id):
        if request.method in ("PATCH", "PUT"):
            try:
                updated = update_staff(staff_id, request.get_json(silent=True) or {})
                write_audit("update", "staff_account", staff_id, after=updated)
                return jsonify(updated)
            except ValueError as e:
                return jsonify({"detail": str(e)}), 400
        success = delete_staff(staff_id)
        write_audit("delete", "staff_account", staff_id, after={"success": success})
        return jsonify({"success": success})

    # --- Facility Management Routes ---
    @app.route("/api/facility/structure", methods=["GET"])
    @require_auth
    def facility_structure():
        from backend.monitoring.facility_manager import get_monitoring_structure
        return jsonify(get_monitoring_structure())

    @app.route("/api/facility/rooms", methods=["GET", "POST"])
    @require_auth
    def facility_rooms():
        from backend.monitoring.facility_manager import list_rooms, add_room
        if request.method == "POST":
            if (g.current_user or {}).get("role") != "admin":
                return jsonify({"detail": "Insufficient permissions"}), 403
            data = request.get_json(silent=True) or {}
            room = add_room(data.get("name"), data.get("description", ""))
            if not room:
                return jsonify({"detail": "Gagal menambah ruangan. Database belum terhubung atau data tidak valid."}), 503
            write_audit("create", "facility_room", str(room.get("id")), after=room)
            return jsonify(room)
        return jsonify(list_rooms())

    @app.route("/api/facility/rooms/<room_id>", methods=["PATCH", "PUT", "DELETE"])
    @require_role("admin")
    def facility_room_detail(room_id):
        from backend.monitoring.facility_manager import delete_room, update_room
        if request.method in ("PATCH", "PUT"):
            room = update_room(room_id, request.get_json(silent=True) or {})
            if not room:
                return jsonify({"detail": "Gagal mengubah ruangan"}), 503
            write_audit("update", "facility_room", room_id, after=room)
            return jsonify(room)
        success = delete_room(room_id)
        write_audit("delete", "facility_room", room_id, after={"success": success})
        status = 200 if success else 503
        return jsonify({"success": success}), status

    @app.route("/api/facility/devices", methods=["GET", "POST"])
    @require_auth
    def facility_devices():
        from backend.monitoring.facility_manager import list_devices, add_device
        if request.method == "POST":
            if (g.current_user or {}).get("role") != "admin":
                return jsonify({"detail": "Insufficient permissions"}), 403
            data = request.get_json(silent=True) or {}
            device = add_device(
                data.get("room_id"), 
                data.get("name"), 
                data.get("type"), 
                data.get("threshold", 5.0)
            )
            if not device:
                return jsonify({"detail": "Gagal menambah unit. Database belum terhubung atau data tidak valid."}), 503
            write_audit("create", "facility_device", str(device.get("id")), after=device)
            return jsonify(device)
        return jsonify(list_devices(request.args.get("room_id")))

    @app.route("/api/facility/devices/<device_id>", methods=["PATCH", "PUT", "DELETE"])
    @require_role("admin")
    def facility_device_detail(device_id):
        from backend.monitoring.facility_manager import delete_device, update_device
        if request.method in ("PATCH", "PUT"):
            device = update_device(device_id, request.get_json(silent=True) or {})
            if not device:
                return jsonify({"detail": "Gagal mengubah unit"}), 503
            write_audit("update", "facility_device", device_id, after=device)
            return jsonify(device)
        success = delete_device(device_id)
        write_audit("delete", "facility_device", device_id, after={"success": success})
        status = 200 if success else 503
        return jsonify({"success": success}), status
