"""Optional Google Apps Script webhook export for QC reports."""

from __future__ import annotations

import logging
import os
from typing import Any
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("qc.services.google_apps_script")

WEBHOOK_ENV = "GOOGLE_APPS_SCRIPT_WEBHOOK_URL"
TIMEOUT_SECONDS = 10.0
_last_export = {
    "last_export_status": None,
    "last_export_error": None,
    "last_export_at": None,
    "last_payload_type": None,
}


def send_monitoring_log(payload: dict[str, Any]) -> bool:
    """Send a temperature monitoring log when the webhook env is configured."""
    return _send("monitoring_log", payload)


def send_qc_report(payload: dict[str, Any]) -> bool:
    """Send a QC inspection report when the webhook env is configured."""
    return _send("qc_report", payload)


def google_sheets_status() -> dict[str, Any]:
    return {
        "webhook_configured": bool(os.getenv(WEBHOOK_ENV, "").strip()),
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
        _record_status(report_type, "skipped", "Webhook env is empty")
        return False

    envelope = {
        "type": report_type,
        **(payload or {}),
    }
    try:
        response = httpx.post(webhook_url, json=envelope, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        _record_status(report_type, "success", None)
        return True
    except Exception as exc:
        error = _format_error(exc)
        _record_status(report_type, "error", error)
        logger.warning("Google Apps Script webhook export failed for %s: %s", report_type, error)
        return False


def _format_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    parts = []
    if response is not None:
        parts.append(f"status_code={getattr(response, 'status_code', '')}")
        text = getattr(response, "text", "")
        if text:
            parts.append(f"response_text={text[:500]}")
    message = str(exc)
    if message:
        parts.append(f"exception={message}")
    return "; ".join(part for part in parts if part) or exc.__class__.__name__


def _record_status(report_type: str, status: str, error: str | None):
    _last_export.update({
        "last_export_status": status,
        "last_export_error": error,
        "last_export_at": datetime.now(timezone.utc).isoformat(),
        "last_payload_type": report_type,
    })
