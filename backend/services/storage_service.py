"""
Storage Service
===============
Handles file uploads to Supabase Storage.
"""

import os
import uuid
import logging
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from backend.database.supabase_client import get_client, STORAGE_BUCKET

logger = logging.getLogger("qc.service.storage")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_IMAGE_TYPES = {
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "webp": b"RIFF",
}


def _detect_image_ext(file_bytes: bytes) -> str:
    if not file_bytes:
        raise ValueError("Photo is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Photo exceeds maximum size of {MAX_UPLOAD_BYTES // (1024*1024)}MB")
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

def _local_photo_url(file_bytes: bytes, filename: str, folder: str = "qc_photos") -> str:
    """Save upload locally for development when Supabase Storage is unavailable."""
    if os.environ.get("VERCEL"):
        return None

    upload_root = current_app.config.get("UPLOAD_FOLDER") if current_app else None
    if not upload_root:
        upload_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)
    try:
        ext = _detect_image_ext(file_bytes)
    except Exception:
        ext = os.path.splitext(filename)[1] or ".jpg"
        
    unique_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(target_dir, unique_name)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    return f"/uploads/{folder}/{unique_name}"

def upload_photo(file_bytes, filename: str, staff_id: str = "system") -> str:
    """Upload a photo to Supabase Storage and return the public URL.
    
    Args:
        file_bytes: The raw file content.
        filename: Original filename.
        staff_id: ID of the staff uploading the file.
        
    Returns:
        Public URL of the uploaded image.
    """
    sb = get_client()
    if not sb:
        logger.warning("Supabase client not available, using local storage fallback")
        return _local_photo_url(file_bytes, filename)

    try:
        ext = _detect_image_ext(file_bytes)
    except ValueError as ve:
        logger.error("Validation failed: %s", ve)
        raise

    # Path: staff_id/date/filename
    # Filename: staff_id_timestamp_uuid.ext
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_folder = datetime.now().strftime("%Y-%m-%d")
    unique_name = f"{staff_id}_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    storage_path = f"{staff_id}/{date_folder}/{unique_name}"

    try:
        # Upload to bucket
        # Note: bucket must exist and have proper RLS/Public policies
        res = sb.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": _content_type(ext)}
        )
        
        # Get public URL
        url_res = sb.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        return url_res
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        # Only fallback if not in production
        if not os.environ.get("VERCEL"):
            return _local_photo_url(file_bytes, filename)
        raise Exception(f"Gagal mengunggah foto ke storage: {str(e)}")

