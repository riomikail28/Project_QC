"""
QC Central Kitchen — Validation & SOP Checker v3.0
Fix: Integrated product list from SOP Threshold document, added TDS support, blue-white theme alignment.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, validator, root_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger("qc.validation")
router = APIRouter(prefix="/api/qc", tags=["QC Input"])

# ─── SOP per produk (Source: Produk & SOP Threshold document) ────────────────
SOP_LIMITS: Dict[str, Dict] = {
    "SKU-BEEF-001": { "name": "Finish Goods - Chilled/Frozen Original beef 90gr - AK", "params": { "brix": {"min": 11, "max": 14, "unit": "%"} } },
    "SKU-BEEF-002": { "name": "Finish Goods - Chilled/Frozen Teriyaki beef 90gr- AK", "params": { "brix": {"min": 11, "max": 14, "unit": "%"} } },
    "SKU-CHKN-001": { "name": "Finish Goods - Chilled/Frozen Teriyaki chicken 90gr - AK", "params": { "brix": {"min": 11, "max": 14, "unit": "%"} } },
    "SKU-CUGIL-001": { "name": "Finish Goods - Chilled/Frozen Cugil 100gr - AK", "params": { "brix": {"min": 11, "max": 14, "unit": "%"} } },
    "SKU-CUGIL-002": { "name": "Finish Goods - Chilled/Frozen Cugil tanpa Pete 100gr - AK", "params": { "brix": {"min": 11, "max": 14, "unit": "%"} } },
    "SKU-BUMBU-001": { "name": "Finish Goods - Bumbu Pecel 150gr - AG", "params": { "ph": {"min": 4.0, "max": 6.0, "unit": "pH"} } },
    "SKU-BUMBU-002": { "name": "Finish Goods - Garlic In Oil 150gr - AG", "params": { "ph": {"min": 4.5, "max": 7.0, "unit": "pH"} } },
    "SKU-BUMBU-003": { "name": "Finish Goods - Bumbu Dasar Merah 150gr - AG", "params": { "ph": {"min": 5.0, "max": 6.5, "unit": "pH"} } },
    "SKU-BUMBU-004": { "name": "Finish Goods - Bumbu Dasar Putih 150gr - AG", "params": { "ph": {"min": 5.0, "max": 6.5, "unit": "pH"} } },
    "SKU-WIP-001": { "name": "Finish Goods - WIP Astro Kitchen - Espresso concentrate 1L", "params": { "tds": {"min": 4800, "max": 5700, "unit": "ppm"} } },
    "SKU-WIP-002": { "name": "Finish Goods - WIP Cold Brew concentrate PATRIA 1L - AK", "params": { "tds": {"min": 2300, "max": 3700, "unit": "ppm"} } },
    "SKU-WIP-003": { "name": "Finish Goods - WIP Cold Brew concentrate KINTAMANI 1L - AK", "params": { "tds": {"min": 2300, "max": 3700, "unit": "ppm"} } },
    "SKU-CHKN-002": { "name": "Finish Goods - Grilled Chicken 100gr - AK", "params": { "brix": {"min": 55.0, "max": 65.0, "unit": "%"}, "ph": {"min": 4.0, "max": 6.0, "unit": "pH"} } },
    "SKU-EGG-001": { "name": "Finish Goods - Telur Marinated 1pcs - AK", "params": { "brix": {"min": 25.0, "max": 35.0, "unit": "%"} } },
    "SKU-ONIG-001": { "name": "Finish Goods - Onigiri Salmon Mentai 110gr - AK", "params": { "ph": {"min": 3.5, "max": 6.5, "unit": "pH"} } },
    "SKU-ONIG-002": { "name": "Finish Goods - Onigiri Tuna Mayo 110gr - AK", "params": { "ph": {"min": 3.5, "max": 6.5, "unit": "pH"} } },
    "SKU-ONIG-003": { "name": "Finish Goods - Onigiri Ebi Mentai 110gr - AK", "params": { "ph": {"min": 3.0, "max": 6.0, "unit": "pH"} } },
    "SKU-ONIG-004": { "name": "Finish Goods - Onigiri Beef Yakiniku 110gr - AK", "params": { "brix": {"min": 20.0, "max": 25.0, "unit": "%"}, "ph": {"min": 4.0, "max": 6.0, "unit": "pH"} } },
    "SKU-ONIG-005": { "name": "Finish Goods - Onigiri Chicken Truffle 110gr - AK", "params": { "brix": {"min": 15.0, "max": 25.0, "unit": "%"}, "ph": {"min": 5.0, "max": 7.0, "unit": "pH"} } },
    "SKU-SAMBAL-001": { "name": "Finish Goods - Sambal Korek 15gr ver 2 - AK", "params": { "ph": {"min": 4.0, "max": 6.0, "unit": "pH"} } },
    "SKU-SAUCE-001": { "name": "Finish Goods - Sauce Katsu 100gr", "params": { "brix": {"min": 20.0, "max": 30.0, "unit": "%"}, "ph": {"min": 3.0, "max": 4.0, "unit": "pH"} } },
    "SKU-SAUCE-002": { "name": "Finish Goods - Sauce Mentai 100gr", "params": { "brix": {"min": 35.0, "max": 75.0, "unit": "%"}, "ph": {"min": 3.0, "max": 4.0, "unit": "pH"} } },
    "SKU-HONEY-001": { "name": "Finish Goods - Honey Jelly 150gr", "params": { "brix": {"min": 9.0, "max": 11.0, "unit": "%"} } }
}

# ─── Request Models ──────────────────────────────────────────────────────────
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
    status: str # PASS / WARNING / FAIL
    violations: List[Dict]
    created_at: str

# ─── Validator utama ─────────────────────────────────────────────────────────
def validate_qc_record(record: QCRecordIn) -> Dict[str, Any]:
    if record.product_id not in SOP_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Produk ID '{record.product_id}' tidak ditemukan dalam database SOP."
        )

    sop = SOP_LIMITS[record.product_id]
    violations = []
    warnings = []

    # Common requirement for Cooked items: Core Temp >= 75
    # (Assuming core temp is provided in 'suhu' field)
    if record.params.suhu is not None:
        if record.params.suhu < 75.0:
            violations.append({
                "param": "suhu",
                "value": record.params.suhu,
                "unit": "°C",
                "min": 75.0,
                "message": f"Suhu Inti = {record.params.suhu}°C di bawah standar minimum 75°C"
            })

    for param_name, sop_limit in sop["params"].items():
        if sop_limit is None: continue
        
        value = getattr(record.params, param_name, None)
        if value is None: continue

        lo, hi = sop_limit.get("min"), sop_limit.get("max")
        unit = sop_limit.get("unit", "")

        if (lo is not None and value < lo) or (hi is not None and value > hi):
            violations.append({
                "param": param_name,
                "value": value,
                "unit": unit,
                "min": lo,
                "max": hi,
                "message": f"{param_name.upper()} = {value}{unit} di luar batas SOP ({lo}–{hi}{unit})"
            })
        elif lo is not None and hi is not None:
            margin = (hi - lo) * 0.1
            if value <= lo + margin or value >= hi - margin:
                warnings.append({
                    "param": param_name,
                    "value": value,
                    "unit": unit,
                    "message": f"{param_name.upper()} = {value}{unit} mendekati batas SOP"
                })

    if violations and (not record.correction or len(record.correction.strip()) < 10):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CORRECTION_REQUIRED",
                "message": "Tindakan koreksi wajib diisi (min. 10 karakter) jika ada parameter out-of-range.",
                "violations": violations
            }
        )

    overall_status = "FAIL" if violations else ("WARNING" if warnings else "PASS")

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "status": overall_status
    }

# ─── Routes ──────────────────────────────────────────────────────────────────
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
        created_at=record.timestamp or datetime.utcnow().isoformat()
    )

@router.get("/sop/{product_id}")
async def get_product_sop(product_id: str):
    if product_id not in SOP_LIMITS:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return {"product_id": product_id, **SOP_LIMITS[product_id]}

@router.get("/products")
async def list_products():
    return [
        {"id": pid, "name": data["name"], "params": list(data["params"].keys())}
        for pid, data in SOP_LIMITS.items()
    ]
