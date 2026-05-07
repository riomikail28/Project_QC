"""
Google Sheets Integration
=========================
Sends QC events to a deployed Google Apps Script Web App.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

logger = logging.getLogger("qc.integrations.google_sheets")


def get_web_app_url() -> str:
    """Return the configured Apps Script Web App URL."""
    return (
        os.getenv("APPSCRIPT_WEB_APP_URL")
        or os.getenv("GOOGLE_APPS_SCRIPT_WEB_APP_URL")
        or ""
    ).strip()


def is_configured() -> bool:
    """Check whether Google Apps Script sync can run."""
    return bool(get_web_app_url())


def send_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send a generic event to Google Apps Script."""
    url = get_web_app_url()
    if not url:
        return {"success": False, "error": "APPSCRIPT_WEB_APP_URL belum dikonfigurasi"}

    body = {
        "event_type": event_type,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    data = json.dumps(body, default=str).encode("utf-8")

    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with request.urlopen(req, timeout=12) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            ok = 200 <= response.status < 300 and not parsed.get("error")
            return {"success": ok, "status_code": response.status, "response": parsed}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("Google Sheets HTTP error: %s %s", exc.code, detail)
        return {"success": False, "status_code": exc.code, "error": detail}
    except Exception as exc:
        logger.error("Google Sheets sync failed: %s", exc)
        return {"success": False, "error": str(exc)}


def send_batch_created(batch: dict[str, Any]) -> dict[str, Any]:
    """Send newly created batch data."""
    return send_event("batch_created", {"batch": batch})


def send_monitoring_log(log: dict[str, Any], alert: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send facility monitoring data."""
    return send_event("monitoring_log", {"log": log, "alert": alert})


def send_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Send QC field finding data."""
    return send_event("qc_finding", {"finding": finding})
