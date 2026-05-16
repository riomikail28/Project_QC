"""
Storage Service
===============
Handles file uploads to Supabase Storage.
"""

import os
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass
from backend.database.supabase_client import STORAGE_BUCKET, get_supabase_admin_client

logger = logging.getLogger("qc.service.storage")


def get_client():
    """Backend storage client hook kept patchable for tests."""
    return get_supabase_admin_client()

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_IMAGE_TYPES = {
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "webp": b"RIFF",
}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


@dataclass(frozen=True)
class UploadedPhoto:
    url: str
    storage_path: str
    file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    bucket: str = STORAGE_BUCKET


def _detect_image_ext(file_bytes: bytes, content_type: str | None = None) -> str:
    if not file_bytes:
        raise ValueError("Photo is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Photo exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)}MB")
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Unsupported photo type. Gunakan JPG, PNG, atau WEBP.")
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["jpg"]):
        return ".jpg"
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["png"]):
        return ".png"
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["webp"]) and file_bytes[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Unsupported photo type. Gunakan JPG, PNG, atau WEBP.")


def _content_type(ext: str) -> str:
    return {
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")

def _safe_path_part(value: str | None, default: str = "unknown") -> str:
    safe = str(value or default).strip().replace("\\", "_").replace("/", "_")
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in safe)
    return safe.strip("-_")[:80] or default


def _storage_prefix(staff_id: str = "system", category: str = "inspection", related_id: str | None = None) -> str:
    category_map = {
        "temperature": "temperature",
        "monitoring": "temperature",
        "inspection": "inspection",
        "finding": "finding",
        "qc_finding": "finding",
        "barcode": "barcode",
        "ccp": "ccp",
        "batch": "batches",
        "report": "admin/reports",
        "approval": "admin/reports",
    }
    normalized = category_map.get(str(category or "inspection").lower(), "inspection")
    if normalized == "batches":
        return f"batches/{_safe_path_part(related_id or staff_id, 'batch')}"
    if normalized.startswith("admin/"):
        return normalized
    return f"staff/{_safe_path_part(staff_id, 'system')}/{normalized}"


def upload_photo_result(
    file_bytes,
    filename: str,
    staff_id: str = "system",
    content_type: str | None = None,
    category: str | None = None,
    related_id: str | None = None,
) -> UploadedPhoto:
    """Upload a photo and return URL plus storage path metadata.
    
    Args:
        file_bytes: The raw file content.
        filename: Original filename.
        staff_id: ID of the staff uploading the file.
        
    Returns:
        UploadedPhoto with public URL and storage path.
    """
    try:
        ext = _detect_image_ext(file_bytes, content_type)
    except ValueError as ve:
        logger.error("Validation failed: %s", ve)
        raise

    sb = get_client()
    if not sb:
        raise RuntimeError("Supabase service role key is not configured")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_folder = datetime.now().strftime("%Y-%m-%d")
    safe_staff_id = _safe_path_part(staff_id, "system")
    unique_name = f"{safe_staff_id}_{timestamp}_{uuid.uuid4().hex}{ext}"
    if category is None:
        storage_path = f"{safe_staff_id}/{date_folder}/{unique_name}"
    else:
        storage_path = f"{_storage_prefix(staff_id, category, related_id)}/{date_folder}/{unique_name}"

    try:
        sb.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": _content_type(ext), "upsert": "false"}
        )
        
        public_url = sb.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        if not public_url:
            delete_photo(storage_path)
            raise RuntimeError("Storage upload succeeded but public URL is empty")
        return UploadedPhoto(
            url=public_url,
            storage_path=storage_path,
            file_name=filename,
            file_type=_content_type(ext),
            file_size=len(file_bytes),
        )
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        raise Exception(f"Gagal mengunggah foto ke storage: {str(e)}")


def upload_photo(file_bytes, filename: str, staff_id: str = "system", content_type: str | None = None) -> str:
    """Upload a photo to Supabase Storage and return only the public URL.

    Kept for existing callers/API contract. New code should use
    upload_photo_result when it needs storage_path for rollback or DB metadata.
    """
    result = upload_photo_result(file_bytes, filename, staff_id=staff_id, content_type=content_type)
    return result.url if result else None


def upload_file_storage(
    file_storage,
    staff_id: str = "system",
    category: str | None = None,
    related_id: str | None = None,
) -> UploadedPhoto:
    """Validate and upload a Werkzeug FileStorage image."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        raise ValueError("No photo provided")
    return upload_photo_result(
        file_storage.read(),
        file_storage.filename,
        staff_id=staff_id,
        content_type=getattr(file_storage, "mimetype", None),
        category=category,
        related_id=related_id,
    )


def delete_photo(storage_path: str) -> bool:
    """Best-effort delete for rollback when DB insert fails."""
    if not storage_path:
        return False
    sb = get_client()
    if not sb:
        return False
    try:
        sb.storage.from_(STORAGE_BUCKET).remove([storage_path])
        return True
    except Exception as e:
        logger.warning("Storage rollback delete failed for %s: %s", storage_path, e)
        return False

