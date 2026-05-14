import logging

from flask import Blueprint, jsonify

from backend.middleware.security_middleware import require_auth
from backend.services.dashboard_service import DashboardService

logger = logging.getLogger("qc.routes.dashboard")

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/api/dashboard")


def _service():
    return DashboardService()


def _json(result):
    status = 200 if result.get("success") else 500
    return jsonify(result), status


@dashboard_bp.route("/summary", methods=["GET"])
@require_auth
def summary():
    return _json(_service().summary())


@dashboard_bp.route("/production-trend", methods=["GET"])
@require_auth
def production_trend():
    return _json(_service().production_trend())


@dashboard_bp.route("/qc-status", methods=["GET"])
@require_auth
def qc_status():
    return _json(_service().qc_status())


@dashboard_bp.route("/realtime-monitoring", methods=["GET"])
@require_auth
def realtime_monitoring():
    return _json(_service().realtime_monitoring())


@dashboard_bp.route("/alerts", methods=["GET"])
@require_auth
def alerts():
    return _json(_service().alerts())


@dashboard_bp.route("/today-summary", methods=["GET"])
@require_auth
def today_summary():
    return _json(_service().today_summary())
