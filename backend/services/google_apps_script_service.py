"""Optional Google Apps Script webhook export for QC reports."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("qc.services.google_apps_script")

WEBHOOK_ENV = "GOOGLE_APPS_SCRIPT_WEBHOOK_URL"
TIMEOUT_SECONDS = 10.0


def send_monitoring_log(payload: dict[str, Any]) -> bool:
    """Send a temperature monitoring log when the webhook env is configured."""
    return _send("monitoring_log", payload)


def send_qc_report(payload: dict[str, Any]) -> bool:
    """Send a QC inspection report when the webhook env is configured."""
    return _send("qc_report", payload)


def _send(report_type: str, payload: dict[str, Any]) -> bool:
    webhook_url = os.getenv(WEBHOOK_ENV, "").strip()
    if not webhook_url:
        return False

    envelope = {
        "type": report_type,
        "payload": payload,
    }
    try:
        response = httpx.post(webhook_url, json=envelope, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Google Apps Script webhook export failed for %s: %s", report_type, exc)
        return False
