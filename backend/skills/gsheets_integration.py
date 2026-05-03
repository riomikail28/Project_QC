import httpx
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

# URL Web App dari Google Apps Script yang di-deploy (Diset di env var atau config)
# Contoh: https://script.google.com/macros/s/AKfycby.../exec
APPSCRIPT_WEB_APP_URL = os.environ.get("APPSCRIPT_WEB_APP_URL", "")

async def send_to_google_sheets(batch_data: Dict[str, Any]):
    """
    Mengirim data batch ke Google Spreadsheet melalui Google Apps Script Web App.
    """
    if not APPSCRIPT_WEB_APP_URL:
        logger.warning("APPSCRIPT_WEB_APP_URL tidak diatur. Melewati sinkronisasi Google Sheets.")
        return False

    try:
        # Menggunakan httpx async agar tidak memblokir FastAPI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                APPSCRIPT_WEB_APP_URL,
                json=batch_data,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Berhasil menyimpan data batch ke Google Sheets: {batch_data.get('batch_code')}")
            return True
    except Exception as e:
        logger.error(f"Gagal mengirim data ke Google Sheets: {e}")
        return False
