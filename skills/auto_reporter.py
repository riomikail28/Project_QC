"""
AutoReporter Skill
==================
Compiles all validated CCP data and photos from a production batch into a
structured final report (JSON + HTML → PDF).

Flow:
1. Fetch batch metadata + all CCP logs from Supabase
2. Generate a signed URL for each photo in Supabase Storage
3. Render an HTML report from a Jinja2 template
4. Convert HTML → PDF using WeasyPrint
5. Upload PDF back to Supabase Storage
6. Write the public URL back to production_batches.report_url
7. Return the final report payload

Dependencies:
    pip install supabase weasyprint jinja2 httpx
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from jinja2 import Environment, BaseLoader
from supabase import create_client, Client

try:
    from weasyprint import HTML as WeasyprintHTML
    _HAS_WEASYPRINT = True
except Exception:
    _HAS_WEASYPRINT = False
    logging.warning("WeasyPrint fails to load – PDF generation will be skipped.")
    logging.warning("WeasyPrint not installed – PDF generation will be skipped.")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "https://placeholder.supabase.co")
SUPABASE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "placeholder_key")
STORAGE_BUCKET: str = "qc-photos"
REPORT_BUCKET: str  = "qc-reports"
PHOTO_URL_EXPIRY: int = 3600  # seconds (1 hour signed URLs)


# ---------------------------------------------------------------------------
# Data Shapes
# ---------------------------------------------------------------------------

@dataclass
class PhotoLinks:
    raw_material:   Optional[str] = None
    ph_meter:       Optional[str] = None
    refractometer:  Optional[str] = None
    packaging:      Optional[str] = None


@dataclass
class ReportPayload:
    batch_code:       str
    product_name:     str
    production_date:  str
    shift:            str
    operator:         str
    qc_officer:       str
    final_status:     str
    generated_at:     str
    facility_summary: list[dict]
    ccp1:             Optional[dict]
    ccp2:             Optional[dict]
    ccp3:             Optional[dict]
    photos:           PhotoLinks
    violations:       list[str] = field(default_factory=list)
    report_pdf_url:   Optional[str] = None


# ---------------------------------------------------------------------------
# Supabase Helpers
# ---------------------------------------------------------------------------

def _get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _signed_url(sb: Client, path: str) -> str:
    """Generate a short-lived signed URL for a Supabase Storage object."""
    if not path:
        return ""
    res = sb.storage.from_(STORAGE_BUCKET).create_signed_url(path, PHOTO_URL_EXPIRY)
    return res.get("signedURL", "")


def _fetch_batch(sb: Client, batch_id: str) -> dict:
    res = (
        sb.table("production_batches")
        .select(
            "*, "
            "products(product_name, ph_min, ph_max, brix_min, brix_max, "
            "         core_temp_min_c, raw_temp_max_c, room_temp_max_c)"
        )
        .eq("id", batch_id)
        .single()
        .execute()
    )
    return res.data or {}


def _fetch_batch_logs(sb: Client, batch_id: str) -> list[dict]:
    res = (
        sb.table("production_batch_logs")
        .select("*")
        .eq("batch_id", batch_id)
        .order("recorded_at")
        .execute()
    )
    return res.data or []


def _fetch_recent_facility_logs(sb: Client, production_date: str) -> list[dict]:
    """Pull the most recent facility log entry per zone for the production date."""
    res = (
        sb.table("facility_logs")
        .select("zone, temperature_c, threshold_c, is_normal, recorded_at")
        .gte("recorded_at", f"{production_date}T00:00:00+00:00")
        .lte("recorded_at", f"{production_date}T23:59:59+00:00")
        .order("recorded_at", desc=True)
        .execute()
    )
    # De-duplicate: keep the latest per zone
    seen: set[str] = set()
    result = []
    for row in (res.data or []):
        if row["zone"] not in seen:
            seen.add(row["zone"])
            result.append(row)
    return result


# ---------------------------------------------------------------------------
# Report Compilation
# ---------------------------------------------------------------------------

def _build_report_payload(
    batch: dict,
    logs:  list[dict],
    facility: list[dict],
    sb:    Client,
) -> ReportPayload:
    """Transform raw DB rows into a structured ReportPayload."""
    product   = batch.get("products") or {}
    ccp_map   = {log["stage"]: log for log in logs}

    photos    = PhotoLinks()
    violations: list[str] = []

    # ----- CCP 1 -----
    ccp1_row = ccp_map.get("CCP1_PRE_COOK")
    ccp1 = None
    if ccp1_row:
        photos.raw_material = _signed_url(sb, ccp1_row.get("raw_material_photo_path") or "")
        if ccp1_row.get("raw_temp_status") == "fail":
            violations.append(
                f"CCP1 FAIL – Raw temp {ccp1_row.get('raw_temp_c')}°C "
                f"exceeds max {product.get('raw_temp_max_c')}°C"
            )
        ccp1 = {
            "raw_temp_c":            ccp1_row.get("raw_temp_c"),
            "raw_temp_status":       ccp1_row.get("raw_temp_status"),
            "threshold_max_c":       product.get("raw_temp_max_c"),
            "stage_qc_status":       ccp1_row.get("stage_qc_status"),
            "recorded_at":           ccp1_row.get("recorded_at"),
        }

    # ----- CCP 2 -----
    ccp2_row = ccp_map.get("CCP2_POST_COOK")
    ccp2 = None
    if ccp2_row:
        photos.ph_meter      = _signed_url(sb, ccp2_row.get("ph_meter_photo_path") or "")
        photos.refractometer = _signed_url(sb, ccp2_row.get("refractometer_photo_path") or "")
        for check_field, label in [
            ("core_temp_status", f"Core temp {ccp2_row.get('core_temp_c')}°C < min {product.get('core_temp_min_c')}°C"),
            ("ph_value_status",  f"pH {ccp2_row.get('ph_value_extracted')} out of SOP [{product.get('ph_min')}–{product.get('ph_max')}]"),
            ("brix_value_status",f"Brix {ccp2_row.get('brix_value_extracted')} out of SOP [{product.get('brix_min')}–{product.get('brix_max')}]"),
        ]:
            if ccp2_row.get(check_field) == "fail":
                violations.append(f"CCP2 FAIL – {label}")
        ccp2 = {
            "core_temp_c":           ccp2_row.get("core_temp_c"),
            "core_temp_status":      ccp2_row.get("core_temp_status"),
            "threshold_min_c":       product.get("core_temp_min_c"),
            "ph_value_extracted":    ccp2_row.get("ph_value_extracted"),
            "ph_value_status":       ccp2_row.get("ph_value_status"),
            "ph_threshold":          f"{product.get('ph_min')} – {product.get('ph_max')}",
            "brix_value_extracted":  ccp2_row.get("brix_value_extracted"),
            "brix_value_status":     ccp2_row.get("brix_value_status"),
            "brix_threshold":        f"{product.get('brix_min')} – {product.get('brix_max')}",
            "ocr_confidence_ph":     ccp2_row.get("ocr_confidence_ph"),
            "ocr_confidence_brix":   ccp2_row.get("ocr_confidence_brix"),
            "stage_qc_status":       ccp2_row.get("stage_qc_status"),
            "recorded_at":           ccp2_row.get("recorded_at"),
        }

    # ----- CCP 3 -----
    ccp3_row = ccp_map.get("CCP3_PACKAGING")
    ccp3 = None
    if ccp3_row:
        photos.packaging = _signed_url(sb, ccp3_row.get("packaging_photo_path") or "")
        if ccp3_row.get("room_temp_status") == "fail":
            violations.append(
                f"CCP3 FAIL – Room temp {ccp3_row.get('room_temp_c')}°C "
                f"exceeds max {product.get('room_temp_max_c')}°C"
            )
        ccp3 = {
            "room_temp_c":           ccp3_row.get("room_temp_c"),
            "room_temp_status":      ccp3_row.get("room_temp_status"),
            "threshold_max_c":       product.get("room_temp_max_c"),
            "stage_qc_status":       ccp3_row.get("stage_qc_status"),
            "recorded_at":           ccp3_row.get("recorded_at"),
        }

    final_status = batch.get("final_qc_status") or (
        "fail" if violations else "pass"
    )

    return ReportPayload(
        batch_code       = batch.get("batch_code", "N/A"),
        product_name     = product.get("product_name", "N/A"),
        production_date  = str(batch.get("production_date", "")),
        shift            = batch.get("shift") or "—",
        operator         = batch.get("operator_id") or "—",
        qc_officer       = batch.get("qc_officer_id") or "—",
        final_status     = final_status,
        generated_at     = datetime.now(timezone.utc).isoformat(),
        facility_summary = facility,
        ccp1             = ccp1,
        ccp2             = ccp2,
        ccp3             = ccp3,
        photos           = photos,
        violations       = violations,
    )


# ---------------------------------------------------------------------------
# HTML Report Template
# ---------------------------------------------------------------------------

REPORT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QC Batch Report – {{ payload.batch_code }}</title>
<style>
  body { font-family: Arial, sans-serif; font-size: 12px; color: #111; margin: 30px; }
  h1   { color: #1a4d8f; border-bottom: 2px solid #1a4d8f; padding-bottom: 6px; }
  h2   { color: #1a4d8f; margin-top: 24px; }
  table{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th   { background: #1a4d8f; color: #fff; padding: 6px 10px; text-align: left; }
  td   { border: 1px solid #ccc; padding: 6px 10px; }
  .pass{ color: #1a7a1a; font-weight: bold; }
  .fail{ color: #b30000; font-weight: bold; }
  .violation-box { background: #fff0f0; border: 1px solid #b30000;
                   padding: 10px; border-radius: 4px; margin-bottom: 16px; }
  .photo { max-width: 260px; border: 1px solid #ccc; margin: 4px; }
  footer { margin-top: 40px; font-size: 10px; color: #888; }
</style>
</head>
<body>
<h1>QC Batch Report</h1>
<p><strong>Company:</strong> PT Astro Teknologi Indonesia &nbsp;|&nbsp;
   <strong>Facility:</strong> Central Kitchen</p>

<table>
  <tr><th colspan="2">Batch Information</th></tr>
  <tr><td>Batch Code</td><td>{{ payload.batch_code }}</td></tr>
  <tr><td>Product</td><td>{{ payload.product_name }}</td></tr>
  <tr><td>Production Date</td><td>{{ payload.production_date }}</td></tr>
  <tr><td>Shift</td><td>{{ payload.shift }}</td></tr>
  <tr><td>Final QC Status</td>
      <td class="{{ payload.final_status }}">{{ payload.final_status | upper }}</td></tr>
  <tr><td>Report Generated</td><td>{{ payload.generated_at }}</td></tr>
</table>

{% if payload.violations %}
<div class="violation-box">
  <strong>⚠ Violations Detected</strong>
  <ul>{% for v in payload.violations %}<li>{{ v }}</li>{% endfor %}</ul>
</div>
{% endif %}

<h2>MODULE A – Facility Status (Production Day)</h2>
<table>
  <tr><th>Zone</th><th>Temp (°C)</th><th>Threshold</th><th>Status</th></tr>
  {% for f in payload.facility_summary %}
  <tr>
    <td>{{ f.zone | title }}</td>
    <td>{{ f.temperature_c }}</td>
    <td>≤ {{ f.threshold_c }}</td>
    <td class="{{ 'pass' if f.is_normal else 'fail' }}">
        {{ 'NORMAL' if f.is_normal else 'ABNORMAL' }}</td>
  </tr>
  {% endfor %}
</table>

<h2>MODULE B – Batch QC Traceability</h2>

{% if payload.ccp1 %}
<h3>CCP 1 – Pre-Cook</h3>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
  <tr>
    <td>Raw Material Temp</td>
    <td>{{ payload.ccp1.raw_temp_c }}°C</td>
    <td>≤ {{ payload.ccp1.threshold_max_c }}°C</td>
    <td class="{{ payload.ccp1.raw_temp_status }}">
        {{ payload.ccp1.raw_temp_status | upper }}</td>
  </tr>
</table>
{% if payload.photos.raw_material %}
<p><strong>Raw Material Photo:</strong><br>
   <img class="photo" src="{{ payload.photos.raw_material }}" alt="Raw Material"></p>
{% endif %}
{% endif %}

{% if payload.ccp2 %}
<h3>CCP 2 – Post-Cook</h3>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
  <tr>
    <td>Core Temperature</td>
    <td>{{ payload.ccp2.core_temp_c }}°C</td>
    <td>≥ {{ payload.ccp2.threshold_min_c }}°C</td>
    <td class="{{ payload.ccp2.core_temp_status }}">
        {{ payload.ccp2.core_temp_status | upper }}</td>
  </tr>
  <tr>
    <td>pH (Milwaukee pH51)</td>
    <td>{{ payload.ccp2.ph_value_extracted }}
        (conf: {{ "%.0f%%"|format(payload.ccp2.ocr_confidence_ph * 100) }})</td>
    <td>{{ payload.ccp2.ph_threshold }}</td>
    <td class="{{ payload.ccp2.ph_value_status }}">
        {{ payload.ccp2.ph_value_status | upper }}</td>
  </tr>
  <tr>
    <td>Brix (Refractometer)</td>
    <td>{{ payload.ccp2.brix_value_extracted }}
        (conf: {{ "%.0f%%"|format(payload.ccp2.ocr_confidence_brix * 100) }})</td>
    <td>{{ payload.ccp2.brix_threshold }}</td>
    <td class="{{ payload.ccp2.brix_value_status }}">
        {{ payload.ccp2.brix_value_status | upper }}</td>
  </tr>
</table>
<p>
  {% if payload.photos.ph_meter %}
  <strong>pH Meter LCD:</strong><br>
  <img class="photo" src="{{ payload.photos.ph_meter }}" alt="pH Meter"><br>
  {% endif %}
  {% if payload.photos.refractometer %}
  <strong>Refractometer LCD:</strong><br>
  <img class="photo" src="{{ payload.photos.refractometer }}" alt="Refractometer">
  {% endif %}
</p>
{% endif %}

{% if payload.ccp3 %}
<h3>CCP 3 – Packaging</h3>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
  <tr>
    <td>Room Temperature</td>
    <td>{{ payload.ccp3.room_temp_c }}°C</td>
    <td>≤ {{ payload.ccp3.threshold_max_c }}°C</td>
    <td class="{{ payload.ccp3.room_temp_status }}">
        {{ payload.ccp3.room_temp_status | upper }}</td>
  </tr>
</table>
{% if payload.photos.packaging %}
<p><strong>Packaging Photo:</strong><br>
   <img class="photo" src="{{ payload.photos.packaging }}" alt="Packaging"></p>
{% endif %}
{% endif %}

<footer>
  Generated automatically by Intelligent QC Traceability System | PT Astro Teknologi Indonesia
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

def _render_html(payload: ReportPayload) -> str:
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(REPORT_HTML_TEMPLATE)
    return tmpl.render(payload=payload)


def _html_to_pdf(html: str) -> bytes:
    if not _HAS_WEASYPRINT:
        raise RuntimeError("WeasyPrint is not installed. Run: pip install weasyprint")
    return WeasyprintHTML(string=html).write_pdf()


def _upload_report_pdf(sb: Client, batch_code: str, pdf_bytes: bytes) -> str:
    """Upload the PDF to Supabase Storage and return its public path."""
    date_str  = datetime.now(timezone.utc).strftime("%Y%m%d")
    file_path = f"reports/{date_str}/{batch_code}.pdf"
    sb.storage.from_(REPORT_BUCKET).upload(
        file_path,
        pdf_bytes,
        {"content-type": "application/pdf", "upsert": "true"},
    )
    # Get public URL (REPORT_BUCKET should be set to public or signed)
    public_url = sb.storage.from_(REPORT_BUCKET).get_public_url(file_path)
    return public_url


# ---------------------------------------------------------------------------
# Main Skill Entry Point
# ---------------------------------------------------------------------------

def run_auto_reporter(*, batch_id: str) -> ReportPayload:
    """
    Main skill entry point.

    Args:
        batch_id: UUID of the production_batches row.

    Returns:
        ReportPayload with report_pdf_url populated.
    """
    sb      = _get_supabase()
    batch   = _fetch_batch(sb, batch_id)
    logs    = _fetch_batch_logs(sb, batch_id)
    facility = _fetch_recent_facility_logs(sb, str(batch.get("production_date", "")))

    payload = _build_report_payload(batch, logs, facility, sb)

    # ---- Generate & Upload PDF ----
    html    = _render_html(payload)
    try:
        pdf_bytes        = _html_to_pdf(html)
        pdf_url          = _upload_report_pdf(sb, payload.batch_code, pdf_bytes)
        payload.report_pdf_url = pdf_url
        logger.info("Report PDF uploaded: %s", pdf_url)

        # Write URL back to production_batches
        sb.table("production_batches").update({
            "report_url":       pdf_url,
            "final_qc_status":  payload.final_status,
            "status":           "completed",
        }).eq("id", batch_id).execute()

    except RuntimeError as e:
        logger.warning("PDF generation skipped: %s", e)

    return payload
