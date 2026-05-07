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

def _local_photo_url(file_bytes: bytes, filename: str, folder: str = "qc_photos") -> str:
    """Save upload locally for development when Supabase Storage is unavailable."""
    if os.environ.get("VERCEL"):
        return None

    upload_root = current_app.config.get("UPLOAD_FOLDER") if current_app else None
    if not upload_root:
        upload_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    target_dir = os.path.join(upload_root, folder)
    os.makedirs(target_dir, exist_ok=True)
    _, ext = os.path.splitext(secure_filename(filename or "photo.jpg"))
    ext = ext or ".jpg"
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

    # Generate a unique path: findings/2026/05/uuid.jpg
    ext = os.path.splitext(filename)[1] or ".jpg"
    unique_name = f"findings/{uuid.uuid4()}{ext}"

    try:
        # Upload to bucket
        # Note: bucket must exist and have proper RLS/Public policies
        res = sb.storage.from_(STORAGE_BUCKET).upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": "image/jpeg"} # Assuming JPEG for camera
        )
        
        # Get public URL
        # Format: https://[project].supabase.co/storage/v1/object/public/[bucket]/[path]
        url = sb.storage.from_(STORAGE_BUCKET).get_public_url(unique_name)
        return url
    except Exception as e:
        logger.error("Storage upload failed: %s", e)
        return _local_photo_url(file_bytes, filename)
