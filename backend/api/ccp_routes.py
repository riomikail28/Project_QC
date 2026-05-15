"""
CCP Routes
==========
Blueprint for Critical Control Point (CCP) inspection stages.
Handles stage-specific submissions, photo uploads, and OCR integration.

Stages:
  1. Material Incoming (Suhu Bahan Baku)
  2. Cooking / Processing (Suhu Core & OCR)
  3. Cooling (Suhu Penurunan)
  4. Packaging (Brix, pH, TDS)
"""

from flask import Blueprint, request, jsonify
import logging

from backend.services.ccp_service import upload_photo, submit_ccp_log, process_ocr
from backend.qc.parameter_checker import check_temperature, check_product_parameters
from backend.qc.product_catalog import product_by_code
from backend.database.supabase_client import get_client
from backend.middleware.security_middleware import require_auth
from backend.services.audit_service import current_actor_id, write_audit
from backend.services.request_validation import RequestValidationError, parse_form_json

logger = logging.getLogger("qc.routes.ccp")

ccp_bp = Blueprint("ccp_bp", __name__)


# ---------------------------------------------------------------------------
# POST /api/ccp/submit-stage — Generic CCP stage submission
# ---------------------------------------------------------------------------
@ccp_bp.route("/api/ccp/submit-stage", methods=["POST"])
@require_auth
def submit_stage():
    """Submit a CCP inspection stage.

    Expects multipart/form-data:
        batch_id (str): UUID
        stage (str): Stage name
        operator_id (str): Staff UUID
        photo (file, optional): Supporting photo
        metrics (json string): Metrics to validate
    """
    batch_id = request.form.get("batch_id")
    stage = request.form.get("stage")
    operator_id = request.form.get("operator_id") or current_actor_id()
    
    if not batch_id or not stage:
        return jsonify({"error": "batch_id and stage are required"}), 400

    # 1. Handle Photo Upload (Hybrid: File or URL)
    photo_urls = []
    
    # Check for pre-uploaded URLs in JSON body
    body = request.get_json(silent=True) or {}
    if "photo_url" in body and body["photo_url"]:
        photo_urls.append(body["photo_url"])
    
    # Check for files in multipart request
    photo_files = request.files.getlist("photo")
    for p_file in photo_files:
        if p_file:
            p_url = upload_photo(p_file.read(), p_file.filename, staff_id=operator_id)
            photo_urls.append(p_url)
    
    photo_url = ";".join(photo_urls) if photo_urls else None

    # 2. Parse Metrics
    metrics_raw = parse_form_json("metrics", {})
    if not isinstance(metrics_raw, dict):
        raise RequestValidationError({"metrics": "metrics must be a JSON object"})
    
    # 3. Validate Metrics based on stage
    # (Simplified for the blueprint, delegating to skills)
    # This would involve looking up the product and checking SOPs
    
    # 4. Persist Log
    try:
        log = submit_ccp_log(
            batch_id=batch_id,
            stage=stage,
            operator_id=operator_id,
            photo_url=photo_url,
            metrics=metrics_raw
        )
        write_audit("create", "production_batch_log", str(log.get("id")) if isinstance(log, dict) else None, after=log)
        return jsonify({"success": True, "log": log})
    except Exception as e:
        logger.error("CCP submission failed: %s", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/ccp/ocr — Process OCR for a photo
# ---------------------------------------------------------------------------
@ccp_bp.route("/api/ccp/ocr", methods=["POST"])
@require_auth
def run_ocr():
    """Run OCR on an uploaded image and return extracted text."""
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400
        
    photo = request.files["photo"]
    result = process_ocr(photo.read())
    return jsonify(result)
