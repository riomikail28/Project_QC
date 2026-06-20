"""Repository layer for QC-related DB operations."""

from typing import Any, Dict, Optional


class QCRepository:
    def __init__(self, supabase_client):
        self.sb = supabase_client

    def insert_finding(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.sb:
            return None
        res = self.sb.table("qc_findings").insert(payload).execute()
        return res.data[0] if getattr(res, "data", None) else None
