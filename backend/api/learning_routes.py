import logging
from io import BytesIO

from flask import Blueprint, g, jsonify, request, send_file

from backend.middleware.security_middleware import require_auth
from backend.services.learning_service import LearningService

learning_bp = Blueprint("learning_bp", __name__, url_prefix="/api/learning")
logger = logging.getLogger("qc.routes.learning")


def _service():
    return LearningService()


def _user():
    current = g.current_user or {}
    return {
        "id": str(current.get("user_id") or current.get("sub") or current.get("id") or "anonymous"),
        "username": current.get("username"),
        "name": current.get("name") or current.get("full_name"),
        "role": current.get("role", "staff"),
    }


def _json(result):
    status = result.pop("status", None) or (200 if result.get("success") else 400)
    return jsonify(result), status


def _safe(handler):
    try:
        return _json(handler())
    except Exception as exc:
        logger.exception("Learning API error on %s: %s", request.path, exc)
        return jsonify(
            {
                "success": False,
                "message": "Learning request failed",
            }
        ), 500


@learning_bp.route("/modules", methods=["GET"])
@require_auth
def modules():
    return _safe(lambda: _service().modules(_user()["id"]))


@learning_bp.route("/modules/<module_slug>", methods=["GET"])
@require_auth
def module_detail(module_slug):
    return _safe(lambda: _service().module_detail(_user()["id"], module_slug))


@learning_bp.route("/modules/<module_slug>/mini-quiz", methods=["POST"])
@require_auth
def module_mini_quiz(module_slug):
    payload = request.get_json(silent=True) or {}
    return _safe(lambda: _service().submit_module_mini_quiz(_user()["id"], module_slug, payload.get("answers") or {}))


@learning_bp.route("/modules/<module_slug>/complete", methods=["POST"])
@require_auth
def complete_module(module_slug):
    return _safe(lambda: _service().complete_module(_user()["id"], module_slug))


@learning_bp.route("/progress", methods=["GET"])
@require_auth
def progress():
    return _safe(lambda: _service().progress(_user()["id"]))


@learning_bp.route("/career-recommendation", methods=["GET"])
@require_auth
def career_recommendation():
    return _safe(lambda: _service().career_recommendation(_user()["id"]))


@learning_bp.route("/mentor", methods=["POST"])
@require_auth
def mentor():
    payload = request.get_json(silent=True) or {}
    return _safe(lambda: _service().mentor_answer(_user()["id"], payload.get("question")))


@learning_bp.route("/mentor/history", methods=["GET"])
@require_auth
def mentor_history():
    return _safe(lambda: _service().mentor_history(_user()["id"]))


@learning_bp.route("/simulations", methods=["GET"])
@require_auth
def simulations():
    return _safe(lambda: _service().simulations())


@learning_bp.route("/simulations/<simulation_id>/submit", methods=["POST"])
@require_auth
def submit_simulation(simulation_id):
    payload = request.get_json(silent=True) or {}
    return _safe(
        lambda: _service().submit_simulation(
            _user()["id"],
            simulation_id,
            str(payload.get("selected_action") or "").upper(),
        )
    )


@learning_bp.route("/quizzes", methods=["GET"])
@require_auth
def quizzes():
    return _safe(lambda: _service().quizzes())


@learning_bp.route("/quizzes/<quiz_id>/submit", methods=["POST"])
@require_auth
def submit_quiz(quiz_id):
    payload = request.get_json(silent=True) or {}
    return _safe(lambda: _service().submit_quiz(_user()["id"], quiz_id, payload.get("answers") or {}))


@learning_bp.route("/certificate", methods=["POST"])
@require_auth
def certificate():
    return _safe(lambda: _service().certificate(_user()))


@learning_bp.route("/certificate/pdf", methods=["GET"])
@require_auth
def certificate_pdf():
    try:
        result = _service().certificate_pdf(_user())
        if not result.get("success"):
            status = result.pop("status", None) or 400
            return jsonify(result), status
        data = result["data"]
        return send_file(
            BytesIO(data["bytes"]),
            mimetype=data["content_type"],
            as_attachment=True,
            download_name=data["filename"],
        )
    except Exception as exc:
        logger.exception("Learning certificate PDF error on %s: %s", request.path, exc)
        return jsonify(
            {
                "success": False,
                "message": "Learning certificate PDF failed",
            }
        ), 500
