import logging
from datetime import datetime, timezone

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.repositories.learning")


class LearningRepository:
    """Supabase persistence adapter for ITDV learning data."""

    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def available(self):
        return self.sb is not None

    def fetch_table(self, table, select="*", filters=None, order_by=None, desc=False, limit=None):
        if not self.sb:
            return []
        try:
            table_columns = {
                "learning_modules": "id,slug,title,description,content,published,best_actions,created_at,updated_at",
                "itdv_progress": "id,user_id,module_slug,status,quiz_score,quiz_passed,simulation_score,simulation_passed,completed_at,updated_at,created_at",
                "itdv_attempts": "id,user_id,module_slug,score,passed,created_at",
                "itdv_certificates": "id,user_id,program_code,certificate_number,issued_at,created_at",
            }
            if select == "*":
                select = table_columns.get(table, "*")
            query = self.sb.table(table).select(select)
            for method, field, value in filters or []:
                query = getattr(query, method)(field, value)
            if order_by:
                query = query.order(order_by, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Learning query skipped for %s: %s", table, exc)
            return []

    def upsert_progress(self, payload):
        if not self.sb:
            return None
        try:
            data = {**payload, "updated_at": _now()}
            return (
                self.sb.table("itdv_progress")
                .upsert(
                    data,
                    on_conflict="user_id,module_slug",
                )
                .execute()
                .data
            )
        except Exception as exc:
            logger.warning("Learning progress upsert skipped: %s", exc)
            return None

    def insert_attempt(self, table, payload):
        if not self.sb:
            return None
        try:
            return self.sb.table(table).insert({**payload, "created_at": _now()}).execute().data
        except Exception as exc:
            logger.warning("Learning attempt insert skipped for %s: %s", table, exc)
            return None

    def upsert_certificate(self, payload):
        if not self.sb:
            return None
        try:
            data = {**payload, "issued_at": _now()}
            return (
                self.sb.table("itdv_certificates")
                .upsert(
                    data,
                    on_conflict="user_id,program_code",
                )
                .execute()
                .data
            )
        except Exception as exc:
            logger.warning("Certificate upsert skipped: %s", exc)
            return None


def _now():
    return datetime.now(timezone.utc).isoformat()
