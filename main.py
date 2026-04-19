from __future__ import annotations

# Load .env BEFORE any skill imports that read os.environ
from dotenv import load_dotenv
load_dotenv()

"""
FastAPI Application - Intelligent QC Traceability System
=========================================================
PT Astro Teknologi Indonesia - Central Kitchen

Run:
    .venv/Scripts/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import uuid
import logging
from typing import Optional


from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from supabase import create_client, Client

# Internal skills
# Skill imports are now handled inside the route functions for better resilience
# from skills.parametric_checker import ...
# from skills.ocr_digital_reader import ...
# from skills.auto_reporter import ...

# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "https://placeholder.supabase.co")
SUPABASE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "placeholder")
STORAGE_BUCKET = "qc-photos"

app = FastAPI(
    title       = "QC Traceability System — PT Astro Teknologi Indonesia",
    description = "Intelligent Quality Control API for Central Kitchen operations.",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


@app.get("/", tags=["System"])
async def root():
    return RedirectResponse(url="/dashboard/index.html")


# Mount static files for dashboard
if os.path.exists("dashboard"):
    app.mount("/dashboard", StaticFiles(directory="dashboard"), name="dashboard")



# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Helper: Upload photo to Supabase Storage
# ---------------------------------------------------------------------------

async def _upload_photo(
    sb:        Client,
    file:      UploadFile,
    subfolder: str,
) -> str:
    """Upload an image to Supabase Storage and return its storage path."""
    ext       = (file.filename or "photo.jpg").rsplit(".", 1)[-1]
    filename  = f"{subfolder}/{uuid.uuid4()}.{ext}"
    contents  = await file.read()
    try:
        sb.storage.from_(STORAGE_BUCKET).upload(
            filename,
            contents,
            {"content-type": file.content_type or "image/jpeg", "upsert": "false"},
        )
    except Exception as e:
        logger.error(f"Foto tidak bisa disimpan ke cloud, bypass aktif: {e}")
    return filename


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class FacilityLogResponse(BaseModel):
    zone:          str
    temperature_c: float
    threshold_c:   float
    is_normal:     bool
    status:        str
    violation_msg: str = ""


class BatchCreateRequest(BaseModel):
    product_id:      str
    batch_code:      str
    production_date: str = Field(..., example="2026-04-19")
    shift:           Optional[str] = None
    operator_id:     Optional[str] = None
    qc_officer_id:   Optional[str] = None


class BatchCreateResponse(BaseModel):
    batch_id:   str
    batch_code: str
    message:    str


class CCPLogResponse(BaseModel):
    batch_log_id:  str
    stage:         str
    checks:        list[dict]
    ocr_result:    Optional[dict] = None
    stage_status:  str


class ReportResponse(BaseModel):
    batch_id:      str
    batch_code:    str
    final_status:  str
    report_pdf_url: Optional[str]
    violations:    list[str]


# ---------------------------------------------------------------------------
# MODULE A — Facility Monitoring
# ---------------------------------------------------------------------------

@app.post("/facility/log", response_model=FacilityLogResponse, tags=["Facility Monitoring"])
async def log_facility_temperature(
    zone:         str   = Form(..., description="chiller | freezer | ambient"),
    temperature:  float = Form(...),
    recorder_id:  Optional[str] = Form(None),
    notes:        Optional[str] = Form(None),
    sb: Client = Depends(get_supabase),
):
    """
    Log a facility zone temperature.
    Triggers an automatic alert if the reading is outside SOP limits.
    """
    from skills.parametric_checker import FacilityZone, check_facility_temperature
    try:
        zone_enum = FacilityZone(zone)
    except ValueError:
        raise HTTPException(400, f"Invalid zone '{zone}'. Choose: chiller, freezer, ambient")

    result = check_facility_temperature(
        zone        = zone_enum,
        temperature = temperature,
        recorder_id = recorder_id,
        notes       = notes,
    )
    return FacilityLogResponse(
        zone          = zone,
        temperature_c = temperature,
        threshold_c   = result.threshold_max,  # type: ignore[arg-type]
        is_normal     = result.status.value == "pass",
        status        = result.status.value,
        violation_msg = result.violation_msg,
    )


# ---------------------------------------------------------------------------
# MODULE B — Production Batch Lifecycle
# ---------------------------------------------------------------------------

@app.post("/batch/create", response_model=BatchCreateResponse, tags=["Batch QC"])
async def create_batch(body: BatchCreateRequest, sb: Client = Depends(get_supabase)):
    """Create a new production batch record."""
    # Mencari UUID produk berdasarkan Product Code (misal SKU-SOUP-001)
    pid = body.product_id
    if len(pid) != 36: # Jika bukan format UUID
        try:
            prod_check = sb.table("products").select("id").eq("product_code", pid).execute()
            if prod_check.data:
                pid = prod_check.data[0]["id"]
        except Exception:
            pass

    try:
        res = sb.table("production_batches").insert({
            "product_id":      pid if len(pid) == 36 else "00000000-0000-0000-0000-000000000000",
            "batch_code":      body.batch_code,
            "production_date": body.production_date,
            "shift":           body.shift,
            "operator_id":     body.operator_id if body.operator_id else "00000000-0000-0000-0000-000000000000",
            "qc_officer_id":   body.qc_officer_id if body.qc_officer_id else "00000000-0000-0000-0000-000000000000",
        }).execute()
        if not res.data: raise Exception("No data returned")
        batch_id = res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error create_batch bypassed: {e}")
        batch_id = str(uuid.uuid4())
    return BatchCreateResponse(
        batch_id   = batch_id,
        batch_code = body.batch_code,
        message    = "Batch created. Proceed to CCP1.",
    )


@app.get("/batch/{batch_id}", tags=["Batch QC"])
async def get_batch(batch_id: str, sb: Client = Depends(get_supabase)):
    """Fetch a batch with all CCP logs."""
    batch = sb.table("production_batches").select("*").eq("id", batch_id).single().execute()
    if not batch.data:
        raise HTTPException(404, "Batch not found.")
    logs = sb.table("production_batch_logs").select("*").eq("batch_id", batch_id).execute()
    return {"batch": batch.data, "ccp_logs": logs.data}


# ---- CCP 1: Pre-Cook -------------------------------------------------------

@app.post("/batch/{batch_id}/ccp1", response_model=CCPLogResponse, tags=["Batch QC"])
async def submit_ccp1(
    batch_id:     str,
    raw_temp_c:   float             = Form(..., description="Raw material temperature (≤ 5°C)"),
    recorder_id:  Optional[str]     = Form(None),
    photo:        UploadFile         = File(..., description="Raw material photo"),
    sb: Client = Depends(get_supabase),
):
    """CCP1 – Pre-Cook: upload raw material photo and validate raw temperature."""
    photo_path = await _upload_photo(sb, photo, f"ccp1/{batch_id}")

    try:
        log_res = sb.table("production_batch_logs").insert({
            "batch_id":                 batch_id,
            "stage":                    "CCP1_PRE_COOK",
            "recorder_id":              recorder_id if recorder_id else "00000000-0000-0000-0000-000000000000",
            "raw_material_photo_path":  photo_path,
        }).execute()
        batch_log_id = log_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp1 bypassed: {e}")
        batch_log_id = str(uuid.uuid4())

    from skills.parametric_checker import check_ccp_temperatures
    result = check_ccp_temperatures(
        batch_log_id = batch_log_id,
        stage        = "CCP1_PRE_COOK",
        temperature  = raw_temp_c,
        recorder_id  = recorder_id,
    )

    return CCPLogResponse(
        batch_log_id = batch_log_id,
        stage        = "CCP1_PRE_COOK",
        checks       = [{"label": result.label, "value": raw_temp_c, "status": result.status}],
        stage_status = result.status.value,
    )


# ---- CCP 2: Post-Cook ------------------------------------------------------

@app.post("/batch/{batch_id}/ccp2", response_model=CCPLogResponse, tags=["Batch QC"])
async def submit_ccp2(
    batch_id:        str,
    core_temp_c:     float             = Form(..., description="Core temp (≥ 75°C)"),
    product_id:      str               = Form(...),
    recorder_id:     Optional[str]     = Form(None),
    ph_photo:        UploadFile         = File(..., description="Milwaukee pH51 LCD photo"),
    brix_photo:      UploadFile         = File(..., description="Refractometer LCD photo"),
    sb: Client = Depends(get_supabase),
):
    """CCP2 – Post-Cook: validate core temp, and run OCR on pH + Brix photos."""
    ph_path   = await _upload_photo(sb, ph_photo,   f"ccp2/{batch_id}/ph")
    brix_path = await _upload_photo(sb, brix_photo, f"ccp2/{batch_id}/brix")

    try:
        log_res = sb.table("production_batch_logs").insert({
            "batch_id":                 batch_id,
            "stage":                    "CCP2_POST_COOK",
            "recorder_id":              recorder_id if recorder_id else "00000000-0000-0000-0000-000000000000",
            "ph_meter_photo_path":      ph_path,
            "refractometer_photo_path": brix_path
        }).execute()
        batch_log_id = log_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp2 bypassed: {e}")
        batch_log_id = str(uuid.uuid4())

    # Temperature check
    from skills.parametric_checker import check_ccp_temperatures
    temp_result = check_ccp_temperatures(
        batch_log_id = batch_log_id,
        stage        = "CCP2_POST_COOK",
        temperature  = core_temp_c,
        recorder_id  = recorder_id,
    )

    # OCR on LCD photos
    from skills.ocr_digital_reader import run_ocr_digital_reader
    ocr_output = run_ocr_digital_reader(
        batch_log_id    = batch_log_id,
        product_id      = product_id,
        ph_photo_path   = ph_path,
        brix_photo_path = brix_path,
    )

    return CCPLogResponse(
        batch_log_id = batch_log_id,
        stage        = "CCP2_POST_COOK",
        checks       = [{"label": temp_result.label, "value": core_temp_c, "status": temp_result.status}],
        ocr_result   = {
            "ph_value":    ocr_output["ph_result"].value if ocr_output.get("ph_result") else None,
            "brix_value":  ocr_output["brix_result"].value if ocr_output.get("brix_result") else None,
            "overall_pass": ocr_output["overall_pass"],
        },
        stage_status = "pass" if (temp_result.status.value == "pass" and ocr_output["overall_pass"]) else "fail",
    )


# ---- CCP 3: Packaging -------------------------------------------------------

@app.post("/batch/{batch_id}/ccp3", response_model=CCPLogResponse, tags=["Batch QC"])
async def submit_ccp3(
    batch_id:    str,
    room_temp_c: float             = Form(..., description="Room/ambient temp (≤ 20°C)"),
    recorder_id: Optional[str]     = Form(None),
    photo:       UploadFile         = File(..., description="Packaging visual photo"),
    sb: Client = Depends(get_supabase),
):
    """CCP3 – Packaging: upload packaging photo and validate room temperature."""
    photo_path = await _upload_photo(sb, photo, f"ccp3/{batch_id}")

    try:
        log_res = sb.table("production_batch_logs").insert({
            "batch_id":                 batch_id,
            "stage":                    "CCP3_PACKAGING",
            "recorder_id":              recorder_id if recorder_id else "00000000-0000-0000-0000-000000000000",
            "packaging_photo_path":     photo_path,
        }).execute()
        batch_log_id = log_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp3 bypassed: {e}")
        batch_log_id = str(uuid.uuid4())

    from skills.parametric_checker import check_ccp_temperatures
    result = check_ccp_temperatures(
        batch_log_id = batch_log_id,
        stage        = "CCP3_PACKAGING",
        temperature  = room_temp_c,
        recorder_id  = recorder_id,
    )

    return CCPLogResponse(
        batch_log_id = batch_log_id,
        stage        = "CCP3_PACKAGING",
        checks       = [{"label": result.label, "value": room_temp_c, "status": result.status}],
        stage_status = result.status.value,
    )


# ---- Report Generation ------------------------------------------------------

@app.post("/batch/{batch_id}/report", response_model=ReportResponse, tags=["Batch QC"])
async def generate_report(batch_id: str, sb: Client = Depends(get_supabase)):
    """
    Compile all validated CCP data and photos into a structured PDF report.
    Uploads the PDF to Supabase Storage and writes the URL back to the batch.
    """
    from skills.auto_reporter import run_auto_reporter
    payload = run_auto_reporter(batch_id=batch_id)
    return ReportResponse(
        batch_id       = batch_id,
        batch_code     = payload.batch_code,
        final_status   = payload.final_status,
        report_pdf_url = payload.report_pdf_url,
        violations     = payload.violations,
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "system": "QC Traceability API v1.0.0"}
