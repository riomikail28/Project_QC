"""
Parametric_Checker Skill
========================
Validates all temperature inputs across CCP 1, 2, and 3 (and Facility Monitoring).

Also handles:
- Writing validated results to Supabase
- Triggering alerts for out-of-spec conditions

Dependencies:
    pip install supabase httpx
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "") or "https://placeholder.supabase.co"
SUPABASE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or "placeholder_key"

# Optional: Webhook URL for maintenance alert (e.g. Google Chat, Slack, N8N)
ALERT_WEBHOOK_URL: str = os.getenv("ALERT_WEBHOOK_URL", "")


class QCStatus(str, Enum):
    PASS           = "pass"
    FAIL           = "fail"
    PENDING_REVIEW = "pending_review"


class FacilityZone(str, Enum):
    CHILLER = "chiller"
    FREEZER = "freezer"
    AMBIENT = "ambient"


# ---------------------------------------------------------------------------
# SOP Thresholds (defaults — override per-product from Supabase if needed)
# ---------------------------------------------------------------------------

FACILITY_THRESHOLDS: dict[FacilityZone, float] = {
    FacilityZone.CHILLER: 4.0,    # <= 4°C
    FacilityZone.FREEZER: -18.0,  # <= -18°C
    FacilityZone.AMBIENT: 20.0,   # <= 20°C
}

CCP_RULES = {
    "CCP1_PRE_COOK": {
        "field":     "raw_temp_c",
        "max":       5.0,   # <= 5°C
        "min":       None,
        "label":     "Raw Material Temp (Pre-Cook)",
    },
    "CCP2_POST_COOK": {
        "field":     "core_temp_c",
        "max":       None,
        "min":       75.0,  # >= 75°C
        "label":     "Core Temperature (Post-Cook)",
    },
    "CCP3_PACKAGING": {
        "field":     "room_temp_c",
        "max":       20.0,  # <= 20°C
        "min":       None,
        "label":     "Room Temperature (Packaging)",
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    stage:         str
    label:         str
    value:         float
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    status:        QCStatus
    violation_msg: str = ""


# ---------------------------------------------------------------------------
# Core Validation Logic
# ---------------------------------------------------------------------------

def _check_temperature(
    value: float,
    threshold_min: Optional[float],
    threshold_max: Optional[float],
    label: str,
    stage: str,
) -> CheckResult:
    """Generic temperature check against min/max bounds."""
    violation = ""

    if threshold_max is not None and value > threshold_max:
        violation = (
            f"[FAIL] {label}: {value}°C exceeds maximum {threshold_max}°C."
        )
    elif threshold_min is not None and value < threshold_min:
        violation = (
            f"[FAIL] {label}: {value}°C is below minimum {threshold_min}°C."
        )

    status = QCStatus.FAIL if violation else QCStatus.PASS
    return CheckResult(
        stage         = stage,
        label         = label,
        value         = value,
        threshold_min = threshold_min,
        threshold_max = threshold_max,
        status        = status,
        violation_msg = violation,
    )


# ---------------------------------------------------------------------------
# MODULE A — Facility Monitoring
# ---------------------------------------------------------------------------

def check_facility_temperature(
    *,
    device_id:    Optional[str] = None,
    zone:         FacilityZone,
    temperature:  float,
    threshold_override: Optional[float] = None,
    recorder_id:  Optional[str] = None,
    notes:        Optional[str] = None,
) -> CheckResult:
    """
    Validates a facility zone temperature reading and logs it to Supabase.
    Triggers an alert if out of SOP.

    Returns CheckResult.
    """
    threshold = threshold_override if threshold_override is not None else FACILITY_THRESHOLDS[zone]

    # All facility checks have max threshold only
    result = _check_temperature(
        value         = temperature,
        threshold_max = threshold,
        threshold_min = None,
        label         = f"Facility {zone.value.title()}",
        stage         = f"FACILITY_{zone.value.upper()}",
    )

    # ---- Persist to Supabase ----
    sb = _get_supabase()
    log_row = sb.table("facility_logs").insert([{
        "zone":          zone.value,
        "device_id":     device_id,
        "temperature_c": temperature,
        "threshold_c":   threshold,
        "is_normal":     result.status == QCStatus.PASS,
        "recorder_id":   recorder_id,
        "notes":         notes,
    }]).execute()

    if result.status == QCStatus.FAIL:
        log_id = log_row.data[0]["id"] if log_row.data else None
        _create_facility_alert(sb, log_id, device_id, zone, temperature, threshold)
        _send_alert_webhook(result)

    logger.info("Facility check [%s]: %s°C → %s", zone.value, temperature, result.status)
    return result


def _create_facility_alert(
    sb:          Client,
    log_id:      Optional[str],
    device_id:   Optional[str],
    zone:        FacilityZone,
    temperature: float,
    threshold:   float,
) -> None:
    """Insert an alert record into facility_alerts."""
    sb.table("facility_alerts").insert([{
        "log_id":       log_id,
        "device_id":    device_id,
        "zone":         zone.value,
        "temperature_c": temperature,
        "threshold_c":  threshold,
        "status":       "open",
    }]).execute()


# ---------------------------------------------------------------------------
# MODULE B — CCP Temperature Checks
# ---------------------------------------------------------------------------

def check_ccp_temperatures(
    *,
    batch_log_id: str,
    stage:        str,                 # 'CCP1_PRE_COOK' | 'CCP2_POST_COOK' | 'CCP3_PACKAGING'
    temperature:  float,
    recorder_id:  Optional[str] = None,
) -> CheckResult:
    """
    Validates the CCP temperature for the given stage and updates
    production_batch_logs with the result.

    Returns CheckResult.
    """
    if stage not in CCP_RULES:
        raise ValueError(f"Unknown CCP stage: {stage}. Valid: {list(CCP_RULES)}")

    rule   = CCP_RULES[stage]
    result = _check_temperature(
        value         = temperature,
        threshold_max = rule["max"],
        threshold_min = rule["min"],
        label         = rule["label"],
        stage         = stage,
    )

    # Determine which DB column to update
    status_field = rule["field"].replace("_c", "_status")  # e.g. raw_temp_status

    sb = _get_supabase()
    sb.table("production_batch_logs").update({
        rule["field"]:  temperature,
        status_field:   result.status.value,
    }).eq("id", batch_log_id).execute()

    if result.status == QCStatus.FAIL:
        logger.warning(result.violation_msg)
        _send_alert_webhook(result)

    logger.info("CCP check [%s]: %s°C → %s", stage, temperature, result.status)
    return result


# ---------------------------------------------------------------------------
# Batch Full-Check  (convenience wrapper)
# ---------------------------------------------------------------------------

def validate_full_batch(
    *,
    batch_log_id: str,
    stage:        str,
    temperatures: dict,  # e.g. {"raw_temp_c": 3.5} or {"core_temp_c": 82.0}
    recorder_id:  Optional[str] = None,
) -> list[CheckResult]:
    """
    Validates all temperature fields provided in a single batch log submission.

    Example:
        validate_full_batch(
            batch_log_id="uuid-xxx",
            stage="CCP2_POST_COOK",
            temperatures={"core_temp_c": 82.5},
        )
    """
    results = []
    for field_name, value in temperatures.items():
        # Find matching CCP rule by field name
        matching_stage = next(
            (s for s, r in CCP_RULES.items() if r["field"] == field_name),
            None,
        )
        if matching_stage is None:
            logger.warning("No CCP rule found for field: %s", field_name)
            continue

        r = check_ccp_temperatures(
            batch_log_id = batch_log_id,
            stage        = matching_stage,
            temperature  = value,
            recorder_id  = recorder_id,
        )
        results.append(r)

    # Update stage_qc_status on the batch log
    overall = QCStatus.PASS if all(r.status == QCStatus.PASS for r in results) else QCStatus.FAIL
    _get_supabase().table("production_batch_logs").update(
        {"stage_qc_status": overall.value}
    ).eq("id", batch_log_id).execute()

    return results


# ---------------------------------------------------------------------------
# Alert Webhook
# ---------------------------------------------------------------------------

def _send_alert_webhook(result: CheckResult) -> None:
    """Send an alert to a webhook (Slack/Google Chat/n8n) if configured."""
    if not ALERT_WEBHOOK_URL:
        return

    payload = {
        "text":  (
            f"🚨 *QC ALERT* | {result.stage}\n"
            f"{result.violation_msg}\n"
            f"Recorded at: {datetime.now(timezone.utc).isoformat()}"
        ),
        "stage": result.stage,
        "value": result.value,
    }
    try:
        httpx.post(ALERT_WEBHOOK_URL, json=payload, timeout=5.0)
    except Exception as e:
        logger.error("Failed to send alert webhook: %s", e)


# ---------------------------------------------------------------------------
# Supabase Client
# ---------------------------------------------------------------------------

def _get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
