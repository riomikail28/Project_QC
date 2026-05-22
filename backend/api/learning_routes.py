from flask import Blueprint, g, jsonify, request

from backend.middleware.security_middleware import require_auth
from backend.services.learning_service import LearningService

learning_bp = Blueprint("learning_bp", __name__, url_prefix="/api/learning")


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


@learning_bp.route("/modules", methods=["GET"])
@require_auth
def modules():
    return _json(_service().modules(_user()["id"]))


@learning_bp.route("/modules/<module_slug>/complete", methods=["POST"])
@require_auth
def complete_module(module_slug):
    return _json(_service().complete_module(_user()["id"], module_slug))


@learning_bp.route("/progress", methods=["GET"])
@require_auth
def progress():
    return _json(_service().progress(_user()["id"]))


@learning_bp.route("/simulations", methods=["GET"])
@require_auth
def simulations():
    return _json(_service().simulations())


@learning_bp.route("/simulations/<simulation_id>/submit", methods=["POST"])
@require_auth
def submit_simulation(simulation_id):
    payload = request.get_json(silent=True) or {}
    return _json(_service().submit_simulation(
        _user()["id"],
        simulation_id,
        str(payload.get("selected_action") or "").upper(),
    ))


@learning_bp.route("/quizzes", methods=["GET"])
@require_auth
def quizzes():
    return _json(_service().quizzes())


@learning_bp.route("/quizzes/<quiz_id>/submit", methods=["POST"])
@require_auth
def submit_quiz(quiz_id):
    payload = request.get_json(silent=True) or {}
    return _json(_service().submit_quiz(_user()["id"], quiz_id, payload.get("answers") or {}))


@learning_bp.route("/certificate", methods=["POST"])
@require_auth
def certificate():
    return _json(_service().certificate(_user()))
