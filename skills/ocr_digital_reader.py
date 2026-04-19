"""
OCR_Digital_Reader Skill
========================
Extracts numerical readings from digital LCD display photos
(Milwaukee pH51 and Digital Refractometer).

Uses Google Cloud Vision API as primary OCR engine (highest accuracy for
7-segment LCD displays). Falls back to pytesseract if Vision is unavailable.

Validates extracted values against per-product SOP thresholds stored in Supabase.

Dependencies:
    pip install google-cloud-vision pytesseract Pillow supabase httpx
"""

from __future__ import annotations

import io
import os
import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# ---------------------------------------------------------------------------
# Third-party (lazy imports – gracefully handle missing packages)
# ---------------------------------------------------------------------------
try:
    from google.cloud import vision
    _HAS_VISION = True
except ImportError:
    _HAS_VISION = False

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUPABASE_URL: str  = os.environ.get("SUPABASE_URL", "https://placeholder.supabase.co")
SUPABASE_KEY: str  = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "placeholder_key")
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")


class ReadingType(str, Enum):
    PH   = "ph"
    BRIX = "brix"


@dataclass
class OCRResult:
    reading_type:  ReadingType
    raw_text:      str
    value:         Optional[float]
    confidence:    float           # 0.0 – 1.0
    is_valid:      bool
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    violation_msg: str             = ""
    engine_used:   str             = "unknown"


# ---------------------------------------------------------------------------
# Image Pre-Processing
# ---------------------------------------------------------------------------

def _preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Enhance LCD / 7-segment display photos for better OCR accuracy.
    - Convert to greyscale
    - Increase contrast & sharpness
    - Upscale if small
    """
    try:
        from PIL import Image, ImageFilter, ImageEnhance
    except ImportError:
        raise RuntimeError("Pillow (PIL) is not installed.")

    img = Image.open(io.BytesIO(image_bytes)).convert("L")  # greyscale

    # Upscale small images (OCR struggles < 300 dpi equivalent)
    min_dim = 800
    if min(img.size) < min_dim:
        scale = min_dim / min(img.size)
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )

    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


# ---------------------------------------------------------------------------
# OCR Engines
# ---------------------------------------------------------------------------

def _ocr_via_google_vision(image_bytes: bytes) -> tuple[str, float]:
    """Return (raw_text, confidence) using Google Cloud Vision."""
    if not _HAS_VISION:
        raise RuntimeError("google-cloud-vision not installed")

    client = vision.ImageAnnotatorClient()
    image  = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    texts = response.text_annotations
    if not texts:
        return "", 0.0

    full_text   = texts[0].description.strip()
    # Confidence is per-symbol; average the first annotation's symbols
    confidence  = 0.8  # Vision API doesn't expose per-annotation confidence directly
    return full_text, confidence


def _ocr_via_tesseract(image_bytes: bytes) -> tuple[str, float]:
    """Return (raw_text, confidence) using pytesseract (offline fallback)."""
    if not _HAS_TESSERACT:
        raise RuntimeError("pytesseract not installed")

    img = _preprocess_image(image_bytes)
    # PSM 6 = assume single uniform block of text (good for LCD displays)
    config = "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.+-"
    data   = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)

    texts       = [t for t in data["text"] if t.strip()]
    confidences = [c for t, c in zip(data["text"], data["conf"]) if t.strip() and c > 0]

    raw_text   = " ".join(texts)
    confidence = (sum(confidences) / len(confidences) / 100) if confidences else 0.0
    return raw_text, confidence


def _run_ocr(image_bytes: bytes) -> tuple[str, float, str]:
    """
    Run OCR with engine priority: Google Vision → Tesseract.
    Returns (raw_text, confidence, engine_name).
    """
    if _HAS_VISION and GCP_PROJECT_ID:
        try:
            text, conf = _ocr_via_google_vision(image_bytes)
            return text, conf, "google_vision"
        except Exception as e:
            logger.warning("Google Vision failed, falling back to Tesseract: %s", e)

    if _HAS_TESSERACT:
        text, conf = _ocr_via_tesseract(image_bytes)
        return text, conf, "tesseract"

    raise RuntimeError("No OCR engine available. Install google-cloud-vision or pytesseract.")


# ---------------------------------------------------------------------------
# Value Extraction
# ---------------------------------------------------------------------------

# Regex patterns for common LCD numeric formats
_NUMBER_PATTERN = re.compile(r"[-+]?\d+\.?\d*")


def _extract_number(raw_text: str, reading_type: ReadingType) -> Optional[float]:
    """
    Extract the most relevant numeric value from OCR text.
    pH:   expect range 0.00 – 14.00
    Brix: expect range 0.0  – 80.0
    """
    candidates = [float(m) for m in _NUMBER_PATTERN.findall(raw_text)]
    if not candidates:
        return None

    if reading_type == ReadingType.PH:
        valid = [v for v in candidates if 0.0 <= v <= 14.0]
    else:  # BRIX
        valid = [v for v in candidates if 0.0 <= v <= 85.0]

    return valid[0] if valid else candidates[0]  # return first plausible value


# ---------------------------------------------------------------------------
# Threshold Validation
# ---------------------------------------------------------------------------

def _validate_value(
    value: float,
    reading_type: ReadingType,
    threshold_min: Optional[float],
    threshold_max: Optional[float],
) -> tuple[bool, str]:
    """Returns (is_valid, violation_message)."""
    if value is None:
        return False, "Could not extract a numeric value from the image."

    if threshold_min is not None and value < threshold_min:
        return False, (
            f"{reading_type.value.upper()} {value} is BELOW minimum "
            f"({threshold_min}). SOP violation."
        )
    if threshold_max is not None and value > threshold_max:
        return False, (
            f"{reading_type.value.upper()} {value} EXCEEDS maximum "
            f"({threshold_max}). SOP violation."
        )
    return True, ""


# ---------------------------------------------------------------------------
# Supabase Helpers
# ---------------------------------------------------------------------------

def _get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _fetch_product_thresholds(product_id: str) -> dict:
    """Fetch SOP thresholds for a product from Supabase."""
    sb = _get_supabase()
    result = (
        sb.table("products")
        .select("ph_min, ph_max, brix_min, brix_max")
        .eq("id", product_id)
        .single()
        .execute()
    )
    return result.data or {}


def _download_from_storage(storage_path: str) -> bytes:
    """Download a file from Supabase Storage and return its bytes."""
    sb      = _get_supabase()
    bucket  = "qc-photos"
    response = sb.storage.from_(bucket).download(storage_path)
    return response  # returns bytes


# ---------------------------------------------------------------------------
# Main Skill Entry Point
# ---------------------------------------------------------------------------

def run_ocr_digital_reader(
    *,
    batch_log_id: str,
    product_id:   str,
    ph_photo_path:   Optional[str] = None,
    brix_photo_path: Optional[str] = None,
) -> dict:
    """
    Main skill entry point.

    Args:
        batch_log_id:     UUID of the production_batch_logs row to update.
        product_id:       UUID of the product (to fetch SOP thresholds).
        ph_photo_path:    Supabase Storage path for the pH meter LCD photo.
        brix_photo_path:  Supabase Storage path for the refractometer LCD photo.

    Returns:
        dict with keys: ph_result, brix_result, overall_pass (bool)
    """
    thresholds = _fetch_product_thresholds(product_id)
    results: dict[str, OCRResult] = {}

    for photo_path, reading_type in [
        (ph_photo_path,   ReadingType.PH),
        (brix_photo_path, ReadingType.BRIX),
    ]:
        if not photo_path:
            logger.info("No photo provided for %s – skipping.", reading_type)
            continue

        logger.info("Processing %s photo: %s", reading_type, photo_path)

        image_bytes           = _download_from_storage(photo_path)
        raw_text, conf, engine = _run_ocr(image_bytes)
        value                 = _extract_number(raw_text, reading_type)

        t_min = thresholds.get(f"{reading_type.value}_min")
        t_max = thresholds.get(f"{reading_type.value}_max")
        is_valid, msg = _validate_value(value, reading_type, t_min, t_max)

        result = OCRResult(
            reading_type  = reading_type,
            raw_text      = raw_text,
            value         = value,
            confidence    = round(conf, 4),
            is_valid      = is_valid,
            threshold_min = t_min,
            threshold_max = t_max,
            violation_msg = msg,
            engine_used   = engine,
        )
        results[reading_type.value] = result
        logger.info("OCR Result [%s]: value=%s, valid=%s", reading_type, value, is_valid)

    # ---------- Persist results back to Supabase ----------
    update_payload: dict = {}
    if "ph" in results:
        r = results["ph"]
        update_payload.update(
            ph_value_extracted  = r.value,
            ph_value_status     = "pass" if r.is_valid else "fail",
            ocr_confidence_ph   = r.confidence,
        )
    if "brix" in results:
        r = results["brix"]
        update_payload.update(
            brix_value_extracted = r.value,
            brix_value_status    = "pass" if r.is_valid else "fail",
            ocr_confidence_brix  = r.confidence,
        )

    # Store full OCR output as JSONB for audit trail
    update_payload["ocr_raw_output"] = {
        k: {
            "raw_text":   v.raw_text,
            "value":      v.value,
            "confidence": v.confidence,
            "engine":     v.engine_used,
            "valid":      v.is_valid,
            "violation":  v.violation_msg,
        }
        for k, v in results.items()
    }

    if update_payload:
        sb = _get_supabase()
        sb.table("production_batch_logs").update(update_payload).eq("id", batch_log_id).execute()

    overall_pass = all(r.is_valid for r in results.values())
    return {
        "batch_log_id": batch_log_id,
        "ph_result":    results.get("ph"),
        "brix_result":  results.get("brix"),
        "overall_pass": overall_pass,
    }
