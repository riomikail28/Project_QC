"""
Alert Service
=============
Generates alerts and corrective recommendations based on QC status.
Writes alerts to the facility_alerts table when thresholds are violated.
"""

import logging
from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.alerts")

# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------
SEVERITY_MAP = {
    "PASS": "LOW",
    "WARNING": "MEDIUM",
    "FAIL": "HIGH",
}

# ---------------------------------------------------------------------------
# Corrective action recommendations
# ---------------------------------------------------------------------------
CORRECTIVE_ACTIONS = {
    "chiller": {
        "WARNING": "Periksa pengaturan thermostat dan pastikan pintu chiller tertutup rapat.",
        "FAIL": "SEGERA investigasi unit pendingin. Pindahkan produk ke unit cadangan jika tersedia.",
    },
    "freezer": {
        "WARNING": "Periksa segel pintu freezer dan verifikasi suhu kompresor.",
        "FAIL": "DARURAT: Freezer melebihi batas SOP. Segera pindahkan produk dan hubungi teknisi.",
    },
    "ambient": {
        "WARNING": "Periksa ventilasi ruangan dan pastikan AC berfungsi normal.",
        "FAIL": "Suhu ruangan terlalu tinggi. Hentikan proses produksi di area ini.",
    },
}


def generate_temperature_alert(
    room_name: str,
    unit_type: str,
    temperature: float,
    status: str,
) -> dict:
    """Generate an alert payload based on temperature reading and status.

    Args:
        room_name: Name of the monitored room/zone
        unit_type: 'chiller', 'freezer', or 'ambient'
        temperature: Temperature reading in Celsius
        status: QC status ('PASS', 'WARNING', 'FAIL')

    Returns:
        Alert dictionary with message, severity, and corrective action
    """
    severity = SEVERITY_MAP.get(status, "UNKNOWN")

    if status == "PASS":
        return {
            "alert": False,
            "message": f"Suhu {unit_type} di {room_name} dalam batas aman ({temperature}°C)",
            "severity": severity,
            "action": None,
        }

    action = CORRECTIVE_ACTIONS.get(unit_type, {}).get(status, "Lakukan pengecekan manual")

    return {
        "alert": True,
        "message": f"{unit_type.capitalize()} di {room_name} melebihi batas SOP ({temperature}°C)",
        "severity": severity,
        "action": action,
    }


def save_alert_to_db(
    zone: str,
    temperature: float,
    threshold: float,
    log_id: str = None,
    device_id: str = None,
) -> dict:
    """Persist an alert record to the facility_alerts table.

    Returns the created alert record or None on failure.
    """
    sb = get_client()
    if not sb:
        logger.warning("Supabase offline — alert not persisted")
        return None

    try:
        payload = {
            "zone": zone,
            "temperature_c": temperature,
            "threshold_c": threshold,
            "status": "open",
        }
        if log_id:
            payload["log_id"] = log_id
        if device_id:
            payload["device_id"] = device_id

        res = sb.table("facility_alerts").insert(payload).execute()
        if res.data:
            logger.info("Alert created: zone=%s temp=%.1f°C", zone, temperature)
            return res.data[0]
    except Exception as e:
        logger.error("Failed to save alert: %s", e)

    return None