"""
Parameter Checker
=================
QC parameter validation for CCP (Critical Control Point) inspections.
Validates temperature, pH, Brix, and TDS against product SOP thresholds.
"""

import logging

logger = logging.getLogger("qc.parameter_checker")


def check_temperature(value: float, unit_type: str = "chiller") -> dict:
    """Validate a temperature reading against SOP thresholds.

    Args:
        value: Temperature in Celsius
        unit_type: 'chiller', 'freezer', or 'ambient'

    Returns:
        dict with status, message, and threshold info
    """
    thresholds = {
        "chiller": {"pass_max": 5.0, "warn_max": 8.0, "label": "Chiller Temperature"},
        "freezer": {"pass_max": -18.0, "warn_max": -10.0, "label": "Freezer Temperature"},
        "ambient": {"pass_max": 25.0, "warn_max": 30.0, "label": "Ambient Temperature"},
    }

    config = thresholds.get(unit_type, thresholds["chiller"])

    if unit_type == "freezer":
        if value <= config["pass_max"]:
            status = "PASS"
        elif value <= config["warn_max"]:
            status = "WARNING"
        else:
            status = "FAIL"
    else:
        if value <= config["pass_max"]:
            status = "PASS"
        elif value <= config["warn_max"]:
            status = "WARNING"
        else:
            status = "FAIL"

    return {
        "value": value,
        "unit_type": unit_type,
        "status": status,
        "label": config["label"],
        "threshold": config["pass_max"],
    }


def check_parameter(value: float, param_min: float = None, param_max: float = None) -> str:
    """Validate a generic QC parameter against min/max range.

    Args:
        value: Measured value
        param_min: Minimum allowed value (inclusive)
        param_max: Maximum allowed value (inclusive)

    Returns:
        Status string: 'PASS' or 'FAIL'
    """
    if value is None:
        return "PENDING"
    if param_min is not None and value < param_min:
        return "FAIL"
    if param_max is not None and value > param_max:
        return "FAIL"
    return "PASS"


def check_product_parameters(
    product: dict,
    ph_value: float = None,
    brix_value: float = None,
    tds_value: float = None,
) -> dict:
    """Validate all QC parameters for a product against its SOP thresholds.

    Args:
        product: Product dict with ph_min, ph_max, brix_min, brix_max, tds_min, tds_max
        ph_value: Measured pH value
        brix_value: Measured Brix value
        tds_value: Measured TDS value

    Returns:
        dict with individual parameter statuses and overall result
    """
    results = {}

    if ph_value is not None:
        results["ph"] = {
            "value": ph_value,
            "status": check_parameter(ph_value, product.get("ph_min"), product.get("ph_max")),
            "range": f"{product.get('ph_min', '?')} – {product.get('ph_max', '?')}",
        }

    if brix_value is not None:
        results["brix"] = {
            "value": brix_value,
            "status": check_parameter(brix_value, product.get("brix_min"), product.get("brix_max")),
            "range": f"{product.get('brix_min', '?')} – {product.get('brix_max', '?')}",
        }

    if tds_value is not None:
        results["tds"] = {
            "value": tds_value,
            "status": check_parameter(tds_value, product.get("tds_min"), product.get("tds_max")),
            "range": f"{product.get('tds_min', '?')} – {product.get('tds_max', '?')}",
        }

    # Overall: FAIL if any parameter fails
    statuses = [r["status"] for r in results.values()]
    overall = "FAIL" if "FAIL" in statuses else "PASS"

    return {
        "parameters": results,
        "overall_status": overall,
        "total_checked": len(results),
    }
