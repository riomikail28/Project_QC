"""Service layer for QC business logic."""

import logging
from typing import Any, Dict, Optional

from backend.services.google_apps_script_service import build_qc_finding_payload, send_qc_finding

logger = logging.getLogger("qc.service.qc")


class QCService:
    def __init__(self, repository, storage_service=None, audit_service=None, external_sync=None):
        self.repo = repository
        self.storage = storage_service
        self.audit = audit_service
        self.external_sync = external_sync

    def report_finding(
        self,
        staff_id: str,
        reason: str,
        photo_file: Optional[Any] = None,
        photo_url: str | None = None,
        storage_path: str | None = None,
        staff_name: str | None = None,
    ) -> Dict[str, Any]:
        photo_files = photo_file if isinstance(photo_file, list) else ([photo_file] if photo_file else [])
        uploaded_files = []
        photo_urls = [item for item in str(photo_url or "").split(";") if item]
        storage_paths = [item for item in str(storage_path or "").split(";") if item]
        if photo_files and self.storage:
            for item in photo_files:
                if hasattr(self.storage, "upload_file_storage"):
                    try:
                        uploaded = self.storage.upload_file_storage(item, staff_id=staff_id, category="finding")
                    except TypeError:
                        uploaded = self.storage.upload_file_storage(item, staff_id=staff_id)
                    uploaded_files.append(uploaded)
                    photo_urls.append(uploaded.url)
                    storage_paths.append(uploaded.storage_path)
                else:
                    photo_urls.append(self.storage.upload_photo(item.read(), item.filename))

        photo_url = ";".join(photo_urls) if photo_urls else None
        storage_path = ";".join(storage_paths) if storage_paths else None

        payload = {
            "staff_id": staff_id,
            "reason": reason,
            "photo_url": photo_url,
        }
        if storage_path:
            payload["storage_path"] = storage_path

        finding = None
        if self.repo:
            try:
                finding = self.repo.insert_finding(payload)
            except Exception as e:
                logger.error("DB insert failed: %s", e)
                if self.storage and hasattr(self.storage, "delete_photo"):
                    for uploaded in uploaded_files:
                        self.storage.delete_photo(uploaded.storage_path)
                raise
        if uploaded_files and not finding:
            if self.storage and hasattr(self.storage, "delete_photo"):
                for uploaded in uploaded_files:
                    self.storage.delete_photo(uploaded.storage_path)
            raise RuntimeError("Database save failed after photo upload")

        finding_id = finding.get("id") if isinstance(finding, dict) else None
        if finding_id:
            for uploaded in uploaded_files:
                self._insert_evidence(uploaded, staff_id, finding_id)
            if storage_paths or photo_urls:
                self._insert_preuploaded_evidence(photo_urls, storage_paths, staff_id, finding_id)

        # Audit the action if audit service available
        try:
            if self.audit:
                self.audit.write_audit(
                    "submit_finding",
                    "qc_finding",
                    str(finding.get("id") if isinstance(finding, dict) else None),
                    after=finding,
                )
                if uploaded_files:
                    self.audit.write_audit(
                        "upload_finding_photo",
                        "qc_finding",
                        str(finding.get("id") if isinstance(finding, dict) else None),
                        metadata={"storage_paths": [item.storage_path for item in uploaded_files]},
                    )
        except Exception as e:
            logger.warning("Audit write skipped: %s", e)

        # Best-effort external sync
        try:
            if self.external_sync and finding:
                self.external_sync.send_finding(finding)
        except Exception as e:
            logger.warning("External sync skipped: %s", e)

        try:
            if finding:
                sheet_row = {**finding, "staff_name": staff_name or finding.get("staff_name")}
                send_qc_finding(build_qc_finding_payload(sheet_row))
        except Exception as e:
            logger.warning("Google Sheets QC finding sync skipped: %s", e)

        data = finding or {"photo_url": photo_url, "storage_path": storage_path}
        return {
            "success": True,
            "message": "QC finding submitted",
            "data": data,
            **(data if isinstance(data, dict) else {}),
            "photo_url": data.get("photo_url") if isinstance(data, dict) else photo_url,
            "storage_path": data.get("storage_path") if isinstance(data, dict) else storage_path,
        }

    def _insert_evidence(self, uploaded, staff_id, finding_id):
        try:
            sb = getattr(self.repo, "sb", None)
            if not sb:
                return
            payload = {
                "file_name": uploaded.file_name,
                "file_type": uploaded.file_type,
                "mime_type": uploaded.file_type,
                "file_size": uploaded.file_size,
                "bucket": uploaded.bucket,
                "storage_path": uploaded.storage_path,
                "public_url": uploaded.url,
                "uploaded_by": staff_id,
                "related_type": "qc_finding",
                "related_id": finding_id,
            }
            sb.table("qc_evidence").insert({k: v for k, v in payload.items() if v is not None}).execute()
        except Exception as e:
            logger.warning("QC finding evidence metadata skipped: %s", e)

    def _insert_preuploaded_evidence(self, photo_urls, storage_paths, staff_id, finding_id):
        try:
            sb = getattr(self.repo, "sb", None)
            if not sb:
                return
            max_items = max(len(photo_urls or []), len(storage_paths or []))
            for index in range(max_items):
                public_url = photo_urls[index] if index < len(photo_urls or []) else None
                storage_path = storage_paths[index] if index < len(storage_paths or []) else None
                payload = {
                    "bucket": "qc-evidence",
                    "storage_path": storage_path,
                    "public_url": public_url,
                    "uploaded_by": staff_id,
                    "related_type": "qc_finding",
                    "related_id": finding_id,
                }
                sb.table("qc_evidence").insert({k: v for k, v in payload.items() if v is not None}).execute()
        except Exception as e:
            logger.warning("QC finding preuploaded evidence metadata skipped: %s", e)
