"""
QC Engine - Core Validation Logic
==================================
Temperature validation rules for chiller/freezer/ambient units.
Follows SOP standards for Central Kitchen operations.

VALIDATION RULES (DO NOT CHANGE):
  CHILLER:  0–5°C = PASS | 6–8°C = WARNING | >8°C = FAIL
  FREEZER:  ≤-18°C = PASS | -18 to -10°C = WARNING | >-10°C = FAIL
  AMBIENT:  ≤25°C = PASS | 25–30°C = WARNING | >30°C = FAIL
"""

import logging

logger = logging.getLogger("qc.engine")


def validate_temperature(unit_type: str, temperature: float) -> str:
    """Validate temperature against SOP thresholds.

    Args:
        unit_type: 'chiller', 'freezer', or 'ambient'
        temperature: Temperature reading in Celsius

    Returns:
        Status string: 'PASS', 'WARNING', or 'FAIL'
    """
    if unit_type == "chiller":
        if 0 <= temperature <= 5:
            return "PASS"
        elif 5 < temperature <= 8:
            return "WARNING"
        else:
            return "FAIL"

    elif unit_type == "freezer":
        if temperature <= -18:
            return "PASS"
        elif -18 < temperature <= -10:
            return "WARNING"
        else:
            return "FAIL"

    elif unit_type == "ambient":
        if temperature <= 25:
            return "PASS"
        elif 25 < temperature <= 30:
            return "WARNING"
        else:
            return "FAIL"

    logger.warning("Unknown unit_type: %s", unit_type)
    return "UNKNOWN"


def calculate_health_score(total_checks: int, passed_checks: int, warning_checks: int = 0) -> float:
    """Calculate overall QC health score as percentage.

    Warnings count as half-weight against the score.
    """
    if total_checks == 0:
        return 100.0

    effective_pass = passed_checks + (warning_checks * 0.5)
    return round((effective_pass / total_checks) * 100, 1)


def determine_overall_status(*statuses: str) -> str:
    """Determine overall status from a list of individual check statuses.

    Returns 'FAIL' if any check failed, 'WARNING' if any warned, else 'PASS'.
    """
    status_set = set(s.upper() for s in statuses if s)
    if "FAIL" in status_set:
        return "FAIL"
    if "WARNING" in status_set:
        return "WARNING"
    return "PASS"
