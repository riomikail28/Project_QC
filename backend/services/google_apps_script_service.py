"""Optional Google Apps Script webhook export for QC reports."""

from __future__ import annotations

import logging
import os
from typing import Any
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger("qc.services.google_apps_script")

WEBHOOK_ENV = "GOOGLE_APPS_SCRIPT_WEBHOOK_URL"
TIMEOUT_SECONDS = 10.0
GET_REDIRECT_STATUS_CODES = {301, 302, 303}
PRESERVE_METHOD_REDIRECT_STATUS_CODES = {307, 308}
REDIRECT_STATUS_CODES = GET_REDIRECT_STATUS_CODES | PRESERVE_METHOD_REDIRECT_STATUS_CODES
MAX_REDIRECTS = 3
_last_export = {
    "last_export_status": None,
    "last_export_error": None,
    "last_export_at": None,
    "last_payload_type": None,
    "last_http_status": None,
    "last_response_text": None,
    "last_exception_message": None,
    "final_status_code": None,
    "final_response_text": None,
}


def send_monitoring_log(payload: dict[str, Any]) -> bool:
    """Send a temperature monitoring log when the webhook env is configured."""
    return _send("monitoring_log", payload)


def send_qc_report(payload: dict[str, Any]) -> bool:
    """Send a QC inspection report when the webhook env is configured."""
    return _send("qc_report", payload)


def send_qc_finding(payload: dict[str, Any]) -> bool:
    """Send a standalone QC finding to the QC Temuan sheet."""
    return _send("qc_finding", payload)


def build_qc_report_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Build the flat QC report payload expected by the Apps Script sheet."""
    row = row or {}
    result = row.get("inspection_result") if isinstance(row.get("inspection_result"), dict) else {}
    timestamp = row.get("timestamp") or row.get("created_at") or row.get("completed_at") or datetime.now(timezone.utc).isoformat()
    inspection_round = row.get("inspection_round") or result.get("inspection_round") or 1
    is_recheck = row.get("is_recheck")
    if is_recheck is None:
        is_recheck = bool(row.get("parent_inspection") or result.get("parent_inspection") or int(inspection_round or 1) > 1)
    return {
        "timestamp": timestamp,
        "date": row.get("date") or str(timestamp or "")[:10],
        "product_name": row.get("product_name") or "",
        "batch_code": row.get("batch_code") or row.get("barcode") or row.get("batch_id") or "",
        "batch_sequence": row.get("batch_sequence"),
        "cook_name": row.get("cook_name") or "",
        "quantity": row.get("quantity"),
        "inspection_type": row.get("inspection_type") or _inspection_type(row.get("qc_stage") or row.get("ccp_stage") or result.get("qc_stage")),
        "temperature": row.get("temperature") if row.get("temperature") is not None else result.get("temperature"),
        "ph": _first_present(row, result, "ph", "ph_value"),
        "brix": _first_present(row, result, "brix", "brix_value"),
        "tds": _first_present(row, result, "tds", "tds_value"),
        "status": _status(row.get("status") or row.get("qc_status") or result.get("qc_status") or row.get("approval_status")),
        "staff_name": row.get("staff_display_name") or row.get("staff_name") or row.get("inspector_name") or row.get("staff_id") or "",
        "photo_url": _photo_url(row),
        "notes": row.get("notes") or row.get("reason") or result.get("notes") or "",
        "inspection_round": inspection_round,
        "is_recheck": bool(is_recheck),
        "source_type": row.get("source_type") or row.get("report_type") or "qc_report",
        "source_id": row.get("source_id") or row.get("id") or row.get("report_id"),
    }


def build_qc_finding_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Build the flat QC finding payload expected by the QC Temuan sheet."""
    row = row or {}
    timestamp = row.get("timestamp") or row.get("created_at") or row.get("submitted_at") or datetime.now(timezone.utc).isoformat()
    photo_url = _photo_url(row)
    status = str(row.get("status") or row.get("approval_status") or "WARNING").strip().upper()
    if status in {"", "FINDING", "FIELD_FINDING"}:
        status = "WARNING"
    return {
        "timestamp": timestamp,
        "type": "qc_finding",
        "staff_name": _staff_name(row),
        "finding_description": row.get("finding_description") or row.get("temuan") or row.get("finding") or row.get("reason") or row.get("notes") or row.get("description") or row.get("message") or "",
        "photo_url": photo_url,
        "status": status,
        "source_type": "qc_finding",
        "source_id": row.get("source_id") or row.get("id") or row.get("finding_id"),
    }


def _staff_name(row: dict[str, Any]) -> str:
    return (
        row.get("staff_display_name")
        or row.get("staff_name")
        or row.get("full_name")
        or row.get("name")
        or row.get("username")
        or row.get("email")
        or "Unknown Staff"
    )


def _first_present(row: dict[str, Any], result: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
        value = result.get(key)
        if value not in (None, ""):
            return value
    return None


def _inspection_type(stage: Any) -> str:
    normalized = str(stage or "").lower()
    if normalized == "cooking_check":
        return "Cek Masakan"
    if normalized == "final_check":
        return "Cek Label Akhir"
    return str(stage or "")


def _status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {
        "pass": "PASS",
        "passed": "PASS",
        "hold": "HOLD",
        "warning": "HOLD",
        "fail": "FAIL",
        "failed": "FAIL",
    }
    return mapping.get(normalized, str(value or "").upper())


def _photo_url(row: dict[str, Any]) -> Any:
    return (
        row.get("photo_url")
        or row.get("product_photo_url")
        or row.get("cooking_photo_url")
        or row.get("temperature_photo_url")
        or row.get("barcode_photo_url")
        or row.get("label_photo_url")
        or row.get("evidence_url")
        or row.get("public_url")
    )


def google_sheets_status() -> dict[str, Any]:
    webhook_url = os.getenv(WEBHOOK_ENV, "").strip()
    url_ends_with_exec = _url_ends_with_exec(webhook_url)
    return {
        "webhook_configured": bool(webhook_url),
        "webhook_url_ends_with_exec": url_ends_with_exec,
        "webhook_valid": bool(webhook_url) and url_ends_with_exec,
        **_last_export,
    }


def send_test_payload() -> bool:
    return _send("test", {
        "message": "QC Enterprise webhook test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "admin",
    })


def _send(report_type: str, payload: dict[str, Any]) -> bool:
    webhook_url = os.getenv(WEBHOOK_ENV, "").strip()
    if not webhook_url:
        _record_status(
            report_type,
            "skipped",
            "Webhook URL belum valid. Gunakan Web App URL yang berakhiran /exec.",
            exception_message="Webhook env is empty",
        )
        return False

    if not _url_ends_with_exec(webhook_url):
        _record_status(
            report_type,
            "error",
            "Webhook URL belum valid. Gunakan Web App URL yang berakhiran /exec.",
            exception_message="Webhook URL does not end with /exec",
        )
        logger.warning(
            "Google Apps Script webhook export skipped for %s: invalid webhook path target=%s ends_with_exec=%s",
            report_type,
            _safe_webhook_target(webhook_url),
            False,
        )
        return False

    envelope = {
        "type": report_type,
        **(payload or {}),
    }
    try:
        response = _post_following_redirects(webhook_url, envelope)
        response.raise_for_status()
        if not _is_success_response(response):
            raise httpx.HTTPStatusError(
                f"Google Apps Script did not confirm success: {response.text[:200]}",
                request=response.request,
                response=response,
            )
        _record_status(
            report_type,
            "success",
            None,
            http_status=response.status_code,
            response_text=_trim_response_text(response.text),
            final_status_code=response.status_code,
            final_response_text=_trim_response_text(response.text),
        )
        return True
    except Exception as exc:
        error, detail = _format_error(exc)
        _record_status(report_type, "error", error, **detail)
        logger.warning(
            "Google Apps Script webhook export failed for %s target=%s status=%s response_text=%r exception=%s",
            report_type,
            _safe_webhook_target(webhook_url),
            detail.get("http_status"),
            detail.get("response_text"),
            detail.get("exception_message"),
        )
        return False


def _format_error(exc: Exception) -> tuple[str, dict[str, Any]]:
    response = getattr(exc, "response", None)
    parts = []
    detail = {
        "http_status": None,
        "response_text": None,
        "exception_message": None,
        "final_status_code": None,
        "final_response_text": None,
    }
    if response is not None:
        status_code = getattr(response, "status_code", None)
        detail["http_status"] = status_code
        detail["final_status_code"] = status_code
        parts.append(f"status_code={status_code}")
        text = _trim_response_text(getattr(response, "text", ""))
        detail["response_text"] = text
        detail["final_response_text"] = text
        if text:
            parts.append(f"response_text={text}")
    message = str(exc)
    detail["exception_message"] = message or exc.__class__.__name__
    if message:
        parts.append(f"exception={message}")
    return "; ".join(part for part in parts if part) or exc.__class__.__name__, detail


def _record_status(
    report_type: str,
    status: str,
    error: str | None,
    http_status: int | None = None,
    response_text: str | None = None,
    exception_message: str | None = None,
    final_status_code: int | None = None,
    final_response_text: str | None = None,
):
    _last_export.update({
        "last_export_status": status,
        "last_export_error": error,
        "last_export_at": datetime.now(timezone.utc).isoformat(),
        "last_payload_type": report_type,
        "last_http_status": http_status,
        "last_response_text": response_text,
        "last_exception_message": exception_message,
        "final_status_code": final_status_code if final_status_code is not None else http_status,
        "final_response_text": final_response_text if final_response_text is not None else response_text,
    })


def _post_following_redirects(webhook_url: str, envelope: dict[str, Any]) -> httpx.Response:
    current_url = webhook_url
    response = None
    method = "POST"
    for redirect_count in range(MAX_REDIRECTS + 1):
        if method == "POST":
            response = httpx.post(current_url, json=envelope, timeout=TIMEOUT_SECONDS, follow_redirects=False)
        else:
            response = httpx.get(current_url, timeout=TIMEOUT_SECONDS, follow_redirects=False)
        if response.status_code not in REDIRECT_STATUS_CODES:
            return response
        location = response.headers.get("Location") or response.headers.get("location")
        if not location:
            return response
        next_url = urljoin(current_url, location)
        next_method = "POST" if response.status_code in PRESERVE_METHOD_REDIRECT_STATUS_CODES else "GET"
        logger.info(
            "Google Apps Script webhook redirect followed status=%s method=%s next_method=%s from=%s to=%s",
            response.status_code,
            method,
            next_method,
            _safe_webhook_target(current_url),
            _safe_webhook_target(next_url),
        )
        current_url = next_url
        method = next_method
    return response


def _is_success_response(response: httpx.Response) -> bool:
    if response.status_code != 200:
        return False
    text = (response.text or "").strip()
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("success") is False:
            return False
        if isinstance(data, dict) and data.get("success") is True:
            return True
    except ValueError:
        pass
    normalized = text.lower().replace(" ", "")
    if '"success":true' in normalized or "success:true" in normalized:
        return True
    if '"success":false' in normalized or "success:false" in normalized:
        return False
    return True


def _url_ends_with_exec(webhook_url: str) -> bool:
    if not webhook_url:
        return False
    return urlparse(webhook_url).path.rstrip("/").endswith("/exec")


def _safe_webhook_target(webhook_url: str) -> str:
    parsed = urlparse(webhook_url)
    path = parsed.path.rstrip("/")
    suffix = "/exec" if path.endswith("/exec") else path[-24:]
    return f"{parsed.scheme}://{parsed.netloc}/...{suffix}" if parsed.netloc else "invalid-url"


def _trim_response_text(text: str | None) -> str | None:
    if not text:
        return None
    return str(text).strip()[:500]
