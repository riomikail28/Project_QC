"""Real-data service for the staff inspection page."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone

from backend.database.supabase_client import direct_db_query, get_client
from backend.services.audit_service import write_audit
from backend.services.storage_service import delete_photo, upload_file_storage

logger = logging.getLogger("qc.services.inspection")


class InspectionService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _fail(self, message):
        return {"success": False, "data": None, "message": message}

    def _fetch(self, table, select="*", order_by=None, desc=True, limit=None, filters=None):
        try:
            if not self.sb:
                return self._direct_fetch(table, select=select, order_by=order_by, desc=desc, limit=limit, filters=filters)
            query = self.sb.table(table).select(select)
            for method, field, value in filters or []:
                query = getattr(query, method)(field, value)
            if order_by:
                query = query.order(order_by, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Inspection query skipped for %s: %s", table, exc)
            return []

    def _direct_fetch(self, table, select="*", order_by=None, desc=True, limit=None, filters=None):
        parts = [f"select={str(select).replace(' ', '')}"]
        for method, field, value in filters or []:
            if method == "eq":
                normalized = str(value).lower() if isinstance(value, bool) else value
                parts.append(f"{field}=eq.{normalized}")
            elif method == "gte":
                parts.append(f"{field}=gte.{value}")
            elif method == "lte":
                parts.append(f"{field}=lte.{value}")
        if order_by:
            parts.append(f"order={order_by}.{'desc' if desc else 'asc'}")
        if limit:
            parts.append(f"limit={limit}")
        return direct_db_query(table, "GET", None, "&".join(parts))

    def summary(self):
        try:
            batches = self._fetch("production_batches", limit=1000)
            reports = self._fetch("qc_reports", limit=1000)
            approvals = self._fetch("approvals", filters=[("eq", "status", "pending")])
            labels = self._fetch("barcode_labels", limit=1000)
            status_counts = Counter(self._norm_status(row.get("status") or row.get("final_qc_status")) for row in reports)
            active_batches = [row for row in batches if self._norm_status(row.get("status") or row.get("final_qc_status")) in {"pending", "hold", "warning", ""}]
            pending = len(approvals) if approvals else status_counts["pending"] + status_counts["hold"] + status_counts["warning"]
            data = {
                "pass": status_counts["pass"],
                "hold_pending": pending,
                "active_batches": len(active_batches),
                "total_batches": len(batches),
                "recent_submissions": len(reports),
                "barcode_labels": len(labels),
                "has_data": bool(batches or reports or labels or approvals),
            }
            return self._ok(data)
        except Exception as exc:
            logger.exception("Inspection summary failed: %s", exc)
            return self._fail(str(exc))

    def active_batches(self, limit=20):
        rows = self._fetch(
            "production_batches",
            select="*, products(*)",
            order_by="created_at",
            limit=limit,
        )
        active = [
            self._batch_view(row)
            for row in rows
            if self._norm_status(row.get("status") or row.get("final_qc_status")) in {"pending", "hold", "warning", ""}
        ]
        return self._ok(active)

    def product_shortcuts(self, limit=8):
        rows = self._fetch("products", order_by="product_code", desc=False, limit=limit, filters=[("eq", "is_active", True)])
        if not rows:
            rows = self._fetch("products", order_by="product_code", desc=False, limit=limit)
        return self._ok([{
            "id": row.get("id"),
            "product_code": row.get("product_code") or row.get("sku_code") or "-",
            "product_name": row.get("product_name") or "Unnamed product",
        } for row in rows])

    def recent_submissions(self, limit=10):
        reports = self._fetch("qc_reports", order_by="created_at", limit=limit)
        if reports:
            return self._ok([self._report_view(row) for row in reports])
        logs = self._fetch("production_batch_logs", order_by="recorded_at", limit=limit)
        return self._ok([self._log_view(row) for row in logs])

    def submit_qc(self, payload, files=None, actor_id=None):
        files = files or []
        staff_id = payload.get("staff_id") or actor_id
        barcode = str(payload.get("barcode") or "").strip()
        batch_id = payload.get("batch_id") or None
        batch_code = str(payload.get("batch_code") or barcode or "").strip()
        qc_status = self._norm_status(payload.get("qc_status") or payload.get("status") or "pending")
        if qc_status == "failed":
            qc_status = "fail"
        if qc_status == "hold":
            qc_status = "warning"
        if qc_status not in {"pass", "warning", "fail", "pending", "hold"}:
            return self._fail("Status QC tidak valid")
        if not staff_id:
            return self._fail("staff_id wajib tersedia dari sesi login")
        if not batch_code and not batch_id:
            return self._fail("Barcode atau batch wajib diisi")

        uploaded_files = []
        photo_urls = [item for item in str(payload.get("photo_url") or "").split(";") if item]
        storage_paths = [item for item in str(payload.get("storage_path") or "").split(";") if item]
        try:
            for photo_file in files:
                if photo_file and getattr(photo_file, "filename", ""):
                    uploaded = upload_file_storage(photo_file, staff_id=staff_id, category="inspection", related_id=batch_id or batch_code)
                    uploaded_files.append(uploaded)
                    photo_urls.append(uploaded.url)
                    storage_paths.append(uploaded.storage_path)

            report_payload = {
                "batch_id": batch_id,
                "batch_code": batch_code or str(batch_id),
                "product_id": payload.get("product_id") or None,
                "product_name": payload.get("product_name") or None,
                "staff_id": staff_id,
                "inspector_name": payload.get("staff_name") or payload.get("inspector_name"),
                "status": "failed" if qc_status == "fail" else qc_status,
                "approval_status": "pending",
                "barcode": barcode or None,
                "ccp_stage": payload.get("ccp_stage") or "receiving",
                "temperature": payload.get("temperature") or None,
                "notes": payload.get("notes") or None,
                "inspection_result": {
                    "barcode": barcode,
                    "ccp_stage": payload.get("ccp_stage") or "receiving",
                    "temperature": payload.get("temperature"),
                    "notes": payload.get("notes"),
                    "qc_status": qc_status,
                },
                "photo_url": ";".join(photo_urls) if photo_urls else None,
                "storage_path": ";".join(storage_paths) if storage_paths else None,
                "product_photo_url": ";".join(photo_urls) if photo_urls else None,
                "product_storage_path": ";".join(storage_paths) if storage_paths else None,
            }
            report_payload = {key: value for key, value in report_payload.items() if value is not None}
            report = self._insert("qc_reports", report_payload)

            if barcode:
                self._insert("barcode_labels", {
                    "batch_id": batch_id,
                    "batch_code": batch_code or str(batch_id),
                    "product_id": payload.get("product_id") or None,
                    "product_name": payload.get("product_name") or None,
                    "barcode_value": barcode,
                    "barcode_photo_url": report_payload.get("product_photo_url"),
                    "staff_id": staff_id,
                    "staff_name": payload.get("staff_name") or payload.get("inspector_name"),
                }, required=False)

            report_id = report.get("id") if isinstance(report, dict) else None
            for uploaded in uploaded_files:
                self._insert("qc_evidence", {
                    "file_name": uploaded.file_name,
                    "file_type": uploaded.file_type,
                    "mime_type": uploaded.file_type,
                    "file_size": uploaded.file_size,
                    "bucket": uploaded.bucket,
                    "storage_path": uploaded.storage_path,
                    "public_url": uploaded.url,
                    "uploaded_by": staff_id,
                    "related_type": "inspection",
                    "related_id": report_id or batch_id or batch_code,
                }, required=False)

            try:
                write_audit("create", "qc_report", str(report_id), after=report or report_payload)
            except Exception:
                pass
            return self._ok(report or report_payload, "QC inspection submitted")
        except Exception as exc:
            for uploaded in uploaded_files:
                delete_photo(uploaded.storage_path)
            logger.exception("Submit QC failed: %s", exc)
            return self._fail(str(exc))

    def _insert(self, table, payload, required=True):
        if not self.sb:
            if required:
                raise RuntimeError("Database belum terhubung")
            return None
        try:
            return (self.sb.table(table).insert(payload).execute().data or [payload])[0]
        except Exception:
            if required:
                raise
            logger.warning("Optional insert skipped for %s", table, exc_info=True)
            return None

    def _batch_view(self, row):
        product = row.get("products") or {}
        return {
            "id": row.get("id"),
            "batch_code": row.get("batch_code") or "-",
            "product_name": product.get("product_name") or row.get("product_name") or "Unknown product",
            "status": self._norm_status(row.get("final_qc_status") or row.get("status")) or "pending",
            "created_at": row.get("created_at"),
        }

    def _report_view(self, row):
        return {
            "id": row.get("id"),
            "batch_code": row.get("batch_code") or row.get("batch_id") or "-",
            "product_name": row.get("product_name") or "QC report",
            "status": self._norm_status(row.get("status") or row.get("final_qc_status")) or "pending",
            "created_at": row.get("created_at"),
            "photo_url": row.get("product_photo_url") or row.get("temperature_photo_url") or row.get("barcode_photo_url") or row.get("photo_url"),
        }

    def _log_view(self, row):
        return {
            "id": row.get("id"),
            "batch_code": row.get("batch_id") or "-",
            "product_name": row.get("stage") or "CCP inspection",
            "status": self._norm_status(row.get("stage_qc_status")) or "pending",
            "created_at": row.get("recorded_at") or row.get("created_at"),
            "photo_url": row.get("photo_url"),
        }

    def _norm_status(self, value):
        value = str(value or "").lower()
        return {"passed": "pass", "success": "pass", "failed": "fail", "rejected": "fail"}.get(value, value)
