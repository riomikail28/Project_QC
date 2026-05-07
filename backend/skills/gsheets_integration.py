"""
Compatibility wrapper for Google Sheets sync.
New code should import integrations.google_sheets_service directly.
"""

from __future__ import annotations

from typing import Any

from integrations.google_sheets_service import send_event


def send_to_google_sheets(batch_data: dict[str, Any]) -> bool:
    """Send batch data to Google Sheets through Apps Script."""
    result = send_event("batch_created", {"batch": batch_data})
    return bool(result.get("success"))
