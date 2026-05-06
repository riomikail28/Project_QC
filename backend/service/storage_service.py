"""
Storage Service
===============
Handles file uploads to Supabase Storage.
"""

import os
import uuid
import logging
from backend.database.supabase_client import get_client, STORAGE_BUCKET

logger = logging.getLogger("qc.service.storage")

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
        return None

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
        return None
