"""
QC Central Kitchen - Validation & SOP Checker.

The SOP source is product_catalog.py so backend validation, dashboard product
lists, and database seed data stay aligned.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from product_catalog import CENTRAL_KITCHEN_PRODUCTS, sop_params

logger = logging.getLogger("qc.validation")
router = APIRouter(prefix="/api/qc", tags=["QC Input"])

SOP_LIMITS: Dict[str, Dict] = {
    p["product_code"]: {"name": p["product_name"], "params": sop_params(p)}
    for p in CENTRAL_KITCHEN_PRODUCTS
}


class QCParams(BaseModel):
    suhu: Optional[float] = None
    ph: Optional[float] = None
    brix: Optional[float] = None
    tds: Optional[float] = None


class QCRecordIn(BaseModel):
    batch_code: str
    product_id: str
    mfg_date: str
    exp_date: str
    params: QCParams
    photo_url: Optional[str] = None
    photo_key: Optional[str] = None
    photo_note: Optional[str] = None
    has_out_of_range: bool = False
    correction: Optional[str] = None
    operator_id: str
    station_id: str
    ocr_value: Optional[float] = None
    timestamp: Optional[str] = None


class QCRecordOut(BaseModel):
    id: str
    batch_code: str
    product_name: str
    status: str
    violations: List[Dict]
    warnings: List[Dict] = []
    created_at: str


def validate_qc_record(record: QCRecordIn) -> Dict[str, Any]:
    if record.product_id not in SOP_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Produk ID '{record.product_id}' tidak ditemukan dalam database SOP.",
        )

    sop = SOP_LIMITS[record.product_id]
    violations = []
    warnings = []

    if record.params.suhu is not None and record.params.suhu < 75.0:
        violations.append({
            "param": "suhu",
            "value": record.params.suhu,
            "unit": "C",
            "min": 75.0,
            "message": f"Suhu inti = {record.params.suhu}C di bawah standar minimum 75C",
        })

    for param_name, sop_limit in sop["params"].items():
        value = getattr(record.params, param_name, None)
        if value is None:
            continue

        lo = sop_limit.get("min")
        hi = sop_limit.get("max")
        unit = sop_limit.get("unit", "")

        if (lo is not None and value < lo) or (hi is not None and value > hi):
            violations.append({
                "param": param_name,
                "value": value,
                "unit": unit,
                "min": lo,
                "max": hi,
                "message": f"{param_name.upper()} = {value}{unit} di luar batas SOP ({lo}-{hi}{unit})",
            })
        elif lo is not None and hi is not None:
            margin = (hi - lo) * 0.1
            if value <= lo + margin or value >= hi - margin:
                warnings.append({
                    "param": param_name,
                    "value": value,
                    "unit": unit,
                    "message": f"{param_name.upper()} = {value}{unit} mendekati batas SOP",
                })

    if violations and (not record.correction or len(record.correction.strip()) < 10):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CORRECTION_REQUIRED",
                "message": "Tindakan koreksi wajib diisi (min. 10 karakter) jika ada parameter out-of-range.",
                "violations": violations,
            },
        )

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "status": "FAIL" if violations else ("WARNING" if warnings else "PASS"),
    }


@router.post("/records", response_model=QCRecordOut, status_code=status.HTTP_201_CREATED)
async def submit_qc_record(record: QCRecordIn):
    validation = validate_qc_record(record)

    if validation["violations"]:
        logger.warning("QC VIOLATION batch=%s violations=%s", record.batch_code, validation["violations"])

    record_id = f"QC-{record.batch_code}-{int(datetime.utcnow().timestamp())}"

    return QCRecordOut(
        id=record_id,
        batch_code=record.batch_code,
        product_name=SOP_LIMITS[record.product_id]["name"],
        status=validation["status"],
        violations=validation["violations"],
        warnings=validation["warnings"],
        created_at=record.timestamp or datetime.utcnow().isoformat(),
    )


@router.get("/sop/{product_id}")
async def get_product_sop(product_id: str):
    if product_id not in SOP_LIMITS:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return {"product_id": product_id, **SOP_LIMITS[product_id]}


@router.get("/products")
async def list_products():
    return [
        {"id": pid, "name": data["name"], "params": data["params"]}
        for pid, data in SOP_LIMITS.items()
    ]
