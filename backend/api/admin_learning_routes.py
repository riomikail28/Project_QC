"""Admin-only ITDV Learning CRUD routes."""

import logging

from flask import Blueprint, jsonify, request

from backend.middleware.security_middleware import require_role
from backend.services.admin_learning_service import AdminLearningService

logger = logging.getLogger("qc.routes.admin_learning")

admin_learning_bp = Blueprint("admin_learning", __name__, url_prefix="/api/admin/learning")


def _service():
    return AdminLearningService()


def _json(result):
    status = int(result.pop("status", None) or (200 if result.get("success") else 400))
    return jsonify(result), status


def _safe(handler):
    try:
        return _json(handler())
    except Exception as exc:
        logger.exception("Admin learning route failed: %s", exc)
        return jsonify({
            "success": False,
            "message": "Learning admin request failed",
            "error_code": "LEARNING_ADMIN_ERROR",
        }), 500


@admin_learning_bp.route("/modules", methods=["GET"])
@require_role("admin")
def list_modules():
    return _safe(lambda: _service().list_modules())


@admin_learning_bp.route("/modules", methods=["POST"])
@require_role("admin")
def create_module():
    return _safe(lambda: _service().create_module(request.get_json(silent=True) or {}))


@admin_learning_bp.route("/modules/<module_id>", methods=["PUT", "PATCH"])
@require_role("admin")
def update_module(module_id):
    return _safe(lambda: _service().update_module(module_id, request.get_json(silent=True) or {}))


@admin_learning_bp.route("/modules/<module_id>", methods=["DELETE"])
@require_role("admin")
def delete_module(module_id):
    return _safe(lambda: _service().delete_module(module_id))


@admin_learning_bp.route("/modules/<module_id>/mini-quiz", methods=["GET"])
@require_role("admin")
def list_mini_quiz(module_id):
    return _safe(lambda: _service().list_mini_quiz(module_id))


@admin_learning_bp.route("/modules/<module_id>/mini-quiz", methods=["POST"])
@require_role("admin")
def create_mini_quiz(module_id):
    return _safe(lambda: _service().create_mini_quiz(module_id, request.get_json(silent=True) or {}))


@admin_learning_bp.route("/mini-quiz/<quiz_id>", methods=["PUT", "PATCH"])
@require_role("admin")
def update_mini_quiz(quiz_id):
    return _safe(lambda: _service().update_mini_quiz(quiz_id, request.get_json(silent=True) or {}))


@admin_learning_bp.route("/mini-quiz/<quiz_id>", methods=["DELETE"])
@require_role("admin")
def delete_mini_quiz(quiz_id):
    return _safe(lambda: _service().delete_mini_quiz(quiz_id))


@admin_learning_bp.route("/simulations", methods=["GET"])
@require_role("admin")
def list_simulations():
    return _safe(lambda: _service().list_simulations())


@admin_learning_bp.route("/simulations", methods=["POST"])
@require_role("admin")
def create_simulation():
    return _safe(lambda: _service().create_simulation(request.get_json(silent=True) or {}))


@admin_learning_bp.route("/simulations/<simulation_id>", methods=["PUT", "PATCH"])
@require_role("admin")
def update_simulation(simulation_id):
    return _safe(lambda: _service().update_simulation(simulation_id, request.get_json(silent=True) or {}))


@admin_learning_bp.route("/simulations/<simulation_id>", methods=["DELETE"])
@require_role("admin")
def delete_simulation(simulation_id):
    return _safe(lambda: _service().delete_simulation(simulation_id))


@admin_learning_bp.route("/quizzes", methods=["GET"])
@require_role("admin")
def list_quizzes():
    return _safe(lambda: _service().list_quizzes())


@admin_learning_bp.route("/quizzes", methods=["POST"])
@require_role("admin")
def create_quiz():
    return _safe(lambda: _service().create_quiz(request.get_json(silent=True) or {}))


@admin_learning_bp.route("/quizzes/<quiz_id>", methods=["PUT", "PATCH"])
@require_role("admin")
def update_quiz(quiz_id):
    return _safe(lambda: _service().update_quiz(quiz_id, request.get_json(silent=True) or {}))


@admin_learning_bp.route("/quizzes/<quiz_id>", methods=["DELETE"])
@require_role("admin")
def delete_quiz(quiz_id):
    return _safe(lambda: _service().delete_quiz(quiz_id))


@admin_learning_bp.route("/progress", methods=["GET"])
@require_role("admin")
def progress():
    return _safe(lambda: _service().progress())
