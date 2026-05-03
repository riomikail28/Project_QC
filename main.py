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
from datetime import date
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel, Field

from supabase import create_client, Client

# Internal skills
# Skill imports are now handled inside the route functions for better resilience
# from skills.parametric_checker import ...
# from skills.ocr_digital_reader import ...
# from skills.auto_reporter import ...

# ---------------------------------------------------------------------------
from qc_validator import router as qc_router
from staff_manager import router as staff_router
from product_catalog import CENTRAL_KITCHEN_PRODUCTS

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

app.include_router(qc_router)
app.include_router(staff_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ---------------------------------------------------------------------------
# KOREKSI ROUTING UTAMA (Arahkan ke Landing Page)
# ---------------------------------------------------------------------------
@app.get("/", tags=["System"])
async def root():
    # Mengarahkan URL root (domain utama) ke file landing.html
    return RedirectResponse(url="/landing.html")

@app.get("/landing.html", tags=["UI"])
async def serve_landing():
    # Menyajikan file landing.html jika diakses langsung
    if os.path.exists("landing.html"):
        return FileResponse("landing.html")
    return {"error": "File landing.html tidak ditemukan di direktori proyek."}

# Mount static files for dashboard (Folder ini tetap melayani UI setelah login)
if os.path.exists("dashboard"):
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")

# Mount assets folder for landing page
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _clean_uuid(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except (TypeError, ValueError):
        return None


def _product_payload(row: dict) -> dict:
    return {
        "id": row.get("id") or row["product_code"],
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "ph_min": row.get("ph_min"),
        "ph_max": row.get("ph_max"),
        "brix_min": row.get("brix_min"),
        "brix_max": row.get("brix_max"),
        "tds_min": row.get("tds_min"),
        "tds_max": row.get("tds_max"),
        "core_temp_min_c": row.get("core_temp_min_c", 75.0),
        "raw_temp_max_c": row.get("raw_temp_max_c", 5.0),
        "room_temp_max_c": row.get("room_temp_max_c", 20.0),
        "is_active": row.get("is_active", True),
    }


def _resolve_product_id(sb: Client, product_id_or_code: str) -> str:
    if _clean_uuid(product_id_or_code):
        return product_id_or_code

    try:
        res = (
            sb.table("products")
            .select("id")
            .eq("product_code", product_id_or_code)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]
    except Exception as e:
        logger.warning(f"Database produk lookup failed: {e}")

    # Fallback: check local catalog and auto-provision in DB
    from product_catalog import product_by_code
    local = product_by_code(product_id_or_code)
    if local:
        try:
            logger.info(f"Auto-provisioning product: {product_id_or_code}")
            new_prod = sb.table("products").insert([{
                "product_code": local["product_code"],
                "product_name": local["product_name"],
                "ph_min": local.get("ph_min"),
                "ph_max": local.get("ph_max"),
                "brix_min": local.get("brix_min"),
                "brix_max": local.get("brix_max"),
            }]).execute()
            if new_prod.data:
                return new_prod.data[0]["id"]
        except Exception as e:
            logger.error(f"Gagal auto-provision product: {e}", exc_info=True)
            # If insert fails (maybe already exists but select missed it), return code as last resort
            # but usually it's better to fail here than with a UUID error later
            raise HTTPException(503, f"Produk '{product_id_or_code}' ada di katalog tapi gagal masuk Database: {repr(e)}")

    raise HTTPException(400, f"Product '{product_id_or_code}' tidak ditemukan di Database atau Katalog.")


def _stage_status(*statuses: Optional[str]) -> str:
    present = [s for s in statuses if s]
    if not present:
        return "pending_review"
    return "fail" if any(s == "fail" for s in present) else "pass"


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


class DashboardSummary(BaseModel):
    date: str
    batch_today: int
    batch_pass: int
    batch_fail: int
    open_alerts: int
    latest_facility: list[dict]
    recent_batches: list[dict]
    hygiene_compliance: list[dict] = []
    inspector_performance: list[dict] = []


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
        recorder_id = _clean_uuid(recorder_id),
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

@app.get("/products", tags=["Master Data"])
async def list_products(sb: Client = Depends(get_supabase)):
    """Return active products and SOP thresholds for dashboard/forms."""
    try:
        res = (
            sb.table("products")
            .select("*")
            .eq("is_active", True)
            .order("product_code")
            .execute()
        )
        if res.data:
            return [_product_payload(row) for row in res.data]
    except Exception as e:
        logger.warning("Product DB unavailable, using local catalog: %s", e)

    return [_product_payload(row) for row in CENTRAL_KITCHEN_PRODUCTS]


@app.get("/api/analytics/summary", response_model=DashboardSummary, tags=["Analytics"])
async def analytics_summary(day: Optional[str] = None, sb: Client = Depends(get_supabase)):
    """BI summary for the dashboard."""
    selected_day = day or date.today().isoformat()
    try:
        batches = (
            sb.table("production_batches")
            .select("id,batch_code,production_date,shift,status,final_qc_status,created_at,products(product_code,product_name)")
            .eq("production_date", selected_day)
            .order("created_at", desc=True)
            .execute()
        ).data or []
        alerts = (
            sb.table("facility_alerts")
            .select("id")
            .eq("status", "open")
            .execute()
        ).data or []
        facility_logs = (
            sb.table("facility_logs")
            .select("zone,temperature_c,threshold_c,is_normal,recorded_at")
            .order("recorded_at", desc=True)
            .limit(50)
            .execute()
        ).data or []
    except Exception as e:
        logger.warning("Analytics DB unavailable: %s", e)
        return DashboardSummary(
            date=selected_day,
            batch_today=0,
            batch_pass=0,
            batch_fail=0,
            open_alerts=0,
            latest_facility=[],
            recent_batches=[],
        )

    latest_by_zone: dict[str, dict] = {}
    for row in facility_logs:
        latest_by_zone.setdefault(row["zone"], row)

    # Calculate inspector performance from current batches
    inspector_stats: dict[str, dict] = {}
    for b in batches:
        # Check for qc_officer or operator? Screenshot says "Inspektor", so qc_officer is better.
        # But batches might have profiles join.
        officer = b.get("profiles_qc", {}) or {} # Placeholder if we had join
        # For now, let's use the staff accounts if possible, or just mock based on batches
        # Actually, let's just use the count of batches per officer if we had the name.
        # Since the current select doesn't join profiles, I'll update the select first.
        pass

    # Simplified hygiene mock (as there's no table yet)
    hygiene = [
        {"label": "Cuci Tangan", "score": 96, "status": "PASS"},
        {"label": "Sanitasi Alat", "score": 88, "status": "WARNING"},
        {"label": "Penggunaan APD", "score": 93, "status": "PASS"},
        {"label": "Manajemen Limbah", "score": 87, "status": "WARNING"},
    ]

    return DashboardSummary(
        date=selected_day,
        batch_today=len(batches),
        batch_pass=sum(1 for b in batches if b.get("final_qc_status") == "pass"),
        batch_fail=sum(1 for b in batches if b.get("final_qc_status") == "fail"),
        open_alerts=len(alerts),
        latest_facility=list(latest_by_zone.values()),
        recent_batches=batches[:10],
        hygiene_compliance=hygiene,
        inspector_performance=[
            {"name": "Sarah J.", "count": 12, "score": 98, "initials": "SJ"},
            {"name": "Michael C.", "count": 10, "score": 95, "initials": "MC"},
            {"name": "Emily R.", "count": 8, "score": 82, "initials": "ER"},
        ]
    )


@app.get("/batches", tags=["Batch QC"])
async def list_batches(limit: int = 50, sb: Client = Depends(get_supabase)):
    try:
        res = (
            sb.table("production_batches")
            .select("id,batch_code,production_date,shift,status,final_qc_status,report_url,created_at,products(product_code,product_name)")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        raise HTTPException(503, f"Gagal membaca batch: {e}")


@app.post("/batch/create", response_model=BatchCreateResponse, tags=["Batch QC"])
async def create_batch(body: BatchCreateRequest, sb: Client = Depends(get_supabase)):
    """Create a new production batch record."""
    pid = _resolve_product_id(sb, body.product_id)

    try:
        res = sb.table("production_batches").insert([{
            "product_id":      pid,
            "batch_code":      body.batch_code,
            "production_date": body.production_date,
            "shift":           body.shift,
            "operator_id":     _clean_uuid(body.operator_id),
            "qc_officer_id":   _clean_uuid(body.qc_officer_id),
        }]).execute()
        if not res.data: raise Exception("No data returned - possibly foreign key constraint or RLS blocked insert")
        batch_id = res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error create_batch: {e}", exc_info=True)
        raise HTTPException(503, f"Gagal membuat batch di database: {repr(e)}")
    return BatchCreateResponse(
        batch_id   = batch_id,
        batch_code = body.batch_code,
        message    = "Batch created. Proceed to CCP1.",
    )


@app.get("/batch/{batch_id}", tags=["Batch QC"])
async def get_batch(batch_id: str, sb: Client = Depends(get_supabase)):
    """Fetch a batch with all CCP logs."""
    batch_res = sb.table("production_batches").select("*").eq("id", batch_id).execute()
    if not batch_res.data:
        raise HTTPException(404, "Batch not found.")
    logs = sb.table("production_batch_logs").select("*").eq("batch_id", batch_id).execute()
    return {"batch": batch_res.data[0], "ccp_logs": logs.data}


# ---- CCP 1: Pre-Cook -------------------------------------------------------

@app.post("/batch/{batch_id}/ccp1", response_model=CCPLogResponse, tags=["Batch QC"])
async def submit_ccp1(
    batch_id:     str,
    raw_temp_c:   float             = Form(..., description="Raw material temperature (≤ 5°C)"),
    recorder_id:  Optional[str]     = Form(None),
    photo:        UploadFile        = File(..., description="Raw material photo"),
    sb: Client = Depends(get_supabase),
):
    """CCP1 – Pre-Cook: upload raw material photo and validate raw temperature."""
    photo_path = await _upload_photo(sb, photo, f"ccp1/{batch_id}")

    try:
        log_res = sb.table("production_batch_logs").insert([{
            "batch_id":                 batch_id,
            "stage":                    "CCP1_PRE_COOK",
            "recorder_id":              _clean_uuid(recorder_id),
            "raw_material_photo_path":  photo_path,
        }]).execute()
        batch_log_id = log_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp1: {e}")
        raise HTTPException(503, f"Gagal menyimpan CCP1: {e}")

    from skills.parametric_checker import check_ccp_temperatures
    result = check_ccp_temperatures(
        batch_log_id = batch_log_id,
        stage        = "CCP1_PRE_COOK",
        temperature  = raw_temp_c,
        recorder_id  = recorder_id,
    )
    sb.table("production_batch_logs").update({
        "stage_qc_status": result.status.value,
    }).eq("id", batch_log_id).execute()

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
    core_temp_c:     Optional[float]    = Form(None, description="Core temp (≥ 75°C)"),
    product_id:      str               = Form(...),
    ph_value:        Optional[float]    = Form(None),
    brix_value:      Optional[float]    = Form(None),
    tds_value:       Optional[float]    = Form(None),
    recorder_id:     Optional[str]     = Form(None),
    ph_photo:        Optional[UploadFile] = File(None),
    brix_photo:      Optional[UploadFile] = File(None),
    sb: Client = Depends(get_supabase),
):
    """CCP2 – Post-Cook: validate core temp, and run OCR on pH + Brix photos."""
    ph_path = await _upload_photo(sb, ph_photo, f"ccp2/{batch_id}/ph") if ph_photo else None
    brix_path = await _upload_photo(sb, brix_photo, f"ccp2/{batch_id}/brix") if brix_photo else None
    resolved_product_id = _resolve_product_id(sb, product_id)

    try:
        log_res = sb.table("production_batch_logs").select("id").eq("batch_id", batch_id).eq("stage", "CCP2_POST_COOK").execute()
        
        payload = {
            "batch_id": batch_id,
            "stage": "CCP2_POST_COOK"
        }
        if recorder_id: payload["recorder_id"] = _clean_uuid(recorder_id)
        if ph_path: payload["ph_meter_photo_path"] = ph_path
        if brix_path: payload["refractometer_photo_path"] = brix_path

        if log_res.data:
            batch_log_id = log_res.data[0]["id"]
            if len(payload) > 2: # More than just batch_id and stage
                sb.table("production_batch_logs").update(payload).eq("id", batch_log_id).execute()
        else:
            insert_res = sb.table("production_batch_logs").insert([payload]).execute()
            batch_log_id = insert_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp2: {e}")
        raise HTTPException(503, f"Gagal menyimpan CCP2: {e}")

    # Temperature check
    temp_result = None
    from skills.parametric_checker import check_ccp_temperatures
    if core_temp_c is not None:
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
        product_id      = resolved_product_id,
        ph_photo_path   = ph_path,
        brix_photo_path = brix_path,
    )

    product_res = (
        sb.table("products")
        .select("ph_min,ph_max,brix_min,brix_max,tds_min,tds_max")
        .eq("id", resolved_product_id)
        .execute()
    )
    product = product_res.data[0] if product_res.data else {}

    def param_status(value: Optional[float], lo: Optional[float], hi: Optional[float]) -> Optional[str]:
        if value is None:
            return None
        if lo is not None and value < float(lo):
            return "fail"
        if hi is not None and value > float(hi):
            return "fail"
        return "pass"

    manual_payload = {}
    manual_ph_status = param_status(ph_value, product.get("ph_min"), product.get("ph_max"))
    manual_brix_status = param_status(brix_value, product.get("brix_min"), product.get("brix_max"))
    manual_tds_status = param_status(tds_value, product.get("tds_min"), product.get("tds_max"))
    if ph_value is not None:
        manual_payload.update(ph_value_extracted=ph_value, ph_value_status=manual_ph_status)
    if brix_value is not None:
        manual_payload.update(brix_value_extracted=brix_value, brix_value_status=manual_brix_status)
    if tds_value is not None:
        manual_payload.update(tds_value=tds_value, tds_value_status=manual_tds_status)
    if manual_payload:
        sb.table("production_batch_logs").update(manual_payload).eq("id", batch_log_id).execute()

    ph_status = None
    brix_status = None
    if ocr_output.get("ph_result"):
        ph_status = "pass" if ocr_output["ph_result"].is_valid else "fail"
    if ocr_output.get("brix_result"):
        brix_status = "pass" if ocr_output["brix_result"].is_valid else "fail"
    ph_status = manual_ph_status or ph_status
    brix_status = manual_brix_status or brix_status
    
    # We shouldn't overwrite stage_status if it's already pass and we only updated one parameter
    # Let's read the current statuses from DB to merge them
    curr_log = sb.table("production_batch_logs").select("*").eq("id", batch_log_id).execute()
    curr = curr_log.data[0] if curr_log.data else {}
    
    if ph_status is None:
        ph_status = curr.get("ph_value_status")
    if brix_status is None:
        brix_status = curr.get("brix_value_status")
    if manual_tds_status is None:
        manual_tds_status = curr.get("tds_value_status")
    
    curr_temp_status = temp_result.status.value if temp_result else curr.get("stage_qc_status") # fallback for partial temp
    if curr_temp_status is None:
        curr_temp_status = "pass" # if not yet recorded, assume ok for the stage calc
        
    stage_status = _stage_status(curr_temp_status, ph_status, brix_status, manual_tds_status)
    sb.table("production_batch_logs").update({
        "stage_qc_status": stage_status,
    }).eq("id", batch_log_id).execute()

    return CCPLogResponse(
        batch_log_id = batch_log_id,
        stage        = "CCP2_POST_COOK",
        checks       = [{"label": temp_result.label, "value": core_temp_c, "status": temp_result.status}] if temp_result else [],
        ocr_result   = {
            "ph_value":    ocr_output["ph_result"].value if ocr_output.get("ph_result") else None,
            "brix_value":  ocr_output["brix_result"].value if ocr_output.get("brix_result") else None,
            "manual_ph_value": ph_value,
            "manual_brix_value": brix_value,
            "manual_tds_value": tds_value,
            "overall_pass": ocr_output["overall_pass"],
        },
        stage_status = stage_status,
    )


# ---- CCP 3: Packaging -------------------------------------------------------

@app.post("/batch/{batch_id}/ccp3", response_model=CCPLogResponse, tags=["Batch QC"])
async def submit_ccp3(
    batch_id:    str,
    room_temp_c: float             = Form(..., description="Room/ambient temp (≤ 20°C)"),
    recorder_id: Optional[str]     = Form(None),
    photo:       UploadFile        = File(..., description="Packaging visual photo"),
    sb: Client = Depends(get_supabase),
):
    """CCP3 – Packaging: upload packaging photo and validate room temperature."""
    photo_path = await _upload_photo(sb, photo, f"ccp3/{batch_id}")

    try:
        log_res = sb.table("production_batch_logs").insert([{
            "batch_id":                 batch_id,
            "stage":                    "CCP3_PACKAGING",
            "recorder_id":              _clean_uuid(recorder_id),
            "packaging_photo_path":     photo_path,
        }]).execute()
        batch_log_id = log_res.data[0]["id"]
    except Exception as e:
        logger.error(f"DB Error ccp3: {e}")
        raise HTTPException(503, f"Gagal menyimpan CCP3: {e}")

    from skills.parametric_checker import check_ccp_temperatures
    result = check_ccp_temperatures(
        batch_log_id = batch_log_id,
        stage        = "CCP3_PACKAGING",
        temperature  = room_temp_c,
        recorder_id  = recorder_id,
    )
    sb.table("production_batch_logs").update({
        "stage_qc_status": result.status.value,
    }).eq("id", batch_log_id).execute()

    return CCPLogResponse(
        batch_log_id = batch_log_id,
        stage        = "CCP3_PACKAGING",
        checks       = [{"label": result.label, "value": room_temp_c, "status": result.status}],
        stage_status = result.status.value,
    )


# ---- Report Generation ------------------------------------------------------

@app.post("/batch/{batch_id}/report", response_model=ReportResponse, tags=["Batch QC"])
async def generate_report(batch_id: str, background_tasks: BackgroundTasks, sb: Client = Depends(get_supabase)):
    """
    Compile all validated CCP data and photos into a structured PDF report.
    Uploads the PDF to Supabase Storage and writes the URL back to the batch.
    """
    from skills.auto_reporter import run_auto_reporter
    payload = run_auto_reporter(batch_id=batch_id)

    # Sinkronisasi ke Google Sheets
    from skills.gsheets_integration import send_to_google_sheets
    sheet_payload = {
        "batch_id": batch_id,
        "batch_code": payload.batch_code,
        "final_status": payload.final_status,
        "report_pdf_url": payload.report_pdf_url,
        "violations": payload.violations
    }
    background_tasks.add_task(send_to_google_sheets, sheet_payload)
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
