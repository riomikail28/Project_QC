"""Service layer for QC business logic."""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("qc.service.qc")


class QCService:
    def __init__(self, repository, storage_service=None, audit_service=None, external_sync=None):
        self.repo = repository
        self.storage = storage_service
        self.audit = audit_service
        self.external_sync = external_sync

    def report_finding(self, staff_id: str, reason: str, photo_file: Optional[Any]) -> Dict[str, Any]:
        photo_url = None
        if photo_file and self.storage:
            try:
                photo_url = self.storage.upload_photo(photo_file.read(), photo_file.filename)
            except Exception as e:
                logger.error("Photo upload failed in service: %s", e)

        payload = {
            "staff_id": staff_id,
            "reason": reason,
            "photo_url": photo_url,
        }

        finding = None
        if self.repo:
            try:
                finding = self.repo.insert_finding(payload)
            except Exception as e:
                logger.error("DB insert failed: %s", e)

        # Audit the action if audit service available
        try:
            if self.audit:
                self.audit.write_audit("create", "qc_finding", str(finding.get("id") if isinstance(finding, dict) else None), after=finding)
        except Exception as e:
            logger.warning("Audit write skipped: %s", e)

        # Best-effort external sync
        try:
            if self.external_sync and finding:
                self.external_sync.send_finding(finding)
        except Exception as e:
            logger.warning("External sync skipped: %s", e)

        return finding or {"success": True, "photo_url": photo_url}
