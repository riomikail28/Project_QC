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

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
ALLOWED_IMAGE_TYPES = {
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "webp": b"RIFF",
}


def _detect_image_ext(file_bytes: bytes) -> str:
    if not file_bytes:
        raise ValueError("Photo is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Photo exceeds maximum size")
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["jpg"]):
        return ".jpg"
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["png"]):
        return ".png"
    if file_bytes.startswith(ALLOWED_IMAGE_TYPES["webp"]) and file_bytes[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Unsupported photo type")


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
    ext = _detect_image_ext(file_bytes)
    unique_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(target_dir, unique_name)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    return f"/uploads/{folder}/{unique_name}"

def upload_photo(file_bytes, filename: str) -> str:
    """Upload a photo to Supabase Storage and return the public URL.
    
    Args:
        file_bytes: The raw file content.
        filename: Original filename.
        
    Returns:
        Public URL of the uploaded image.
    """
    sb = get_client()
    if not sb:
        return _local_photo_url(file_bytes, filename)

    ext = _detect_image_ext(file_bytes)
    unique_name = f"findings/{uuid.uuid4()}{ext}"

    try:
        # Upload to bucket
        # Note: bucket must exist and have proper RLS/Public policies
        res = sb.storage.from_(STORAGE_BUCKET).upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": _content_type(ext)}
        )
        
        # Get public URL
        # Format: https://[project].supabase.co/storage/v1/object/public/[bucket]/[path]
        url = sb.storage.from_(STORAGE_BUCKET).get_public_url(unique_name)
        return url
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        return _local_photo_url(file_bytes, filename)
