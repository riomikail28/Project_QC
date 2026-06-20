import logging
from datetime import datetime, timezone

from backend.services.base_service import BaseService

logger = logging.getLogger("qc.services.approval")


class ApprovalService(BaseService):
    def get_pending_approvals(self, limit=50):
        try:
            rows = self._fetch("approvals", order_by="created_at", limit=limit, filters=[("eq", "status", "pending")])
            if rows:
                self._prefetch_for_rows(rows, ("staff_id", "created_by", "approved_by"))
                return self._empty([self._approval_summary(row) for row in rows[:limit]])

            rows = []
            reports = self._fetch("qc_reports", order_by="created_at", limit=limit)
            findings = self._fetch("qc_findings", order_by="created_at", limit=limit)
            temp_logs = self._fetch("facility_logs", order_by="recorded_at", limit=limit)
            if not temp_logs:
                temp_logs = self._fetch("temperature_logs", order_by="recorded_at", limit=limit)

            # Prefetch in bulk for all potential sources to avoid N+1 queries
            self._prefetch_for_rows(
                reports + findings + temp_logs,
                ("staff_id", "created_by", "operator_id", "qc_officer_id", "submitted_by"),
            )

            rows.extend(self._approval_from_qc_report(row) for row in reports if self._needs_approval(row))
            rows.extend(self._approval_from_finding(row) for row in findings if self._needs_approval(row, default=True))
            rows.extend(
                self._approval_from_temperature(row) for row in temp_logs if self._temperature_needs_review(row)
            )

            rows = sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)
            return self._empty([self._approval_summary(row) for row in rows[:limit]])
        except Exception as exc:
            logger.error("Approvals failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def get_approval_detail(self, approval_id):
        try:
            approval = (self._fetch("approvals", limit=1, filters=[("eq", "id", approval_id)]) or [None])[0]
            if approval:
                return self._empty(self._approval_detail_from_row(approval))

            report = (self._fetch("qc_reports", limit=1, filters=[("eq", "id", approval_id)]) or [None])[0]
            if report:
                return self._empty(
                    self._approval_detail_from_report(
                        report, {"id": approval_id, "status": report.get("approval_status") or "pending"}
                    )
                )

            related = (self._fetch("approvals", limit=1, filters=[("eq", "related_id", approval_id)]) or [None])[0]
            if related:
                return self._empty(self._approval_detail_from_row(related))
            return self._fail("Approval detail not found")
        except Exception as exc:
            logger.error("Approval detail failed: %s", exc)
            return {"success": False, "detail": str(exc)}

    def approve_item(self, approval_id, actor_id=None, comment=None, approved=True):
        status = "approved" if approved else "rejected"
        approved_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "status": status,
            "approval_status": status,
            "approved_by": actor_id,
            "approved_at": approved_at,
        }
        if not approved:
            payload["rejection_reason"] = comment or "Rejected by admin"
        approval_update = {"status": status, "comment": comment, "approved_by": actor_id, "approved_at": approved_at}
        if not approved:
            approval_update["rejection_reason"] = comment or "Rejected by admin"
        approval_rows = self._update_by_id("approvals", approval_id, approval_update)
        rows = approval_rows
        related_id = None
        if approval_rows:
            related_id = approval_rows[0].get("related_id") or approval_rows[0].get("report_id")
        if not approval_rows:
            existing = self._fetch("approvals", limit=1, filters=[("eq", "related_id", approval_id)])
            if existing:
                related_id = approval_id
                rows = self._update_by_id("approvals", existing[0].get("id"), approval_update)
        if related_id:
            report_rows = self._update_by_id("qc_reports", related_id, payload)
            rows = report_rows or rows
        if not related_id and not rows:
            report_rows = self._update_by_id("qc_reports", approval_id, payload)
            if report_rows:
                related_id = approval_id
                rows = report_rows
        if not rows:
            return self._fail("Approval item not found")
        try:
            from backend.services.audit_service import write_audit

            write_audit(
                "approve_qc" if approved else "reject_qc", "qc_report", related_id or approval_id, after=payload
            )
        except Exception:
            pass
        return self._empty(rows[0])

    def update_qc_finding_status(self, finding_id, status):
        normalized = str(status or "").strip().upper().replace("-", "_").replace(" ", "_")
        if normalized not in {"OPEN", "IN_PROGRESS", "CLOSED"}:
            return self._fail("Status temuan tidak valid")
        updated = self._update_by_id(
            "qc_findings",
            finding_id,
            {
                "status": normalized,
                "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )
        if not updated:
            return self._fail("QC finding not found")
        return self._empty(self._normalize_qc_finding(updated[0]))

    def _update_by_id(self, table, row_id, payload):
        if not self.sb:
            return []
        try:
            return (
                self.sb.table(table)
                .update({k: v for k, v in payload.items() if v is not None})
                .eq("id", row_id)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("Admin update skipped for %s: %s", table, exc)
            return []

    def _needs_approval(self, row, default=False):
        status = str(row.get("approval_status") or row.get("status") or "").lower()
        return status in {"", "pending", "hold", "warning", "finding", "fail", "failed"} or (default and not status)

    def _temperature_needs_review(self, row):
        if row.get("is_normal") is False or row.get("is_abnormal") is True:
            return True
        return bool(row.get("reason") or row.get("photo_url") or row.get("storage_path"))

    def _approval_from_qc_report(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item.setdefault("approval_id", item.get("id"))
        item.setdefault("source", "qc_report")
        item.setdefault("approval_status", item.get("approval_status") or "pending")
        item.setdefault("status", item.get("status") or "pending")
        item.setdefault("qc_stage", item.get("ccp_stage"))
        item.setdefault(
            "inspector_name", item.get("inspector_name") or item.get("staff_name") or item.get("staff_display_name")
        )
        if self._is_uuid_like(item.get("inspector_name")):
            item["inspector_name"] = item.get("staff_display_name")
        item.setdefault("product_photo_url", item.get("product_photo_url") or item.get("photo_url"))
        return item

    def _approval_summary(self, row):
        item = self._approval_with_related(row)
        evidence = self._approval_evidence_url(item)
        return {
            "id": item.get("approval_id") or item.get("id"),
            "approval_id": item.get("approval_id") or item.get("id"),
            "related_id": item.get("related_id") or item.get("report_id"),
            "batch_code": item.get("batch_code") or item.get("batch_id") or "-",
            "product_name": item.get("product_name") or item.get("product") or "-",
            "qc_status": self._display_qc_status(item.get("status") or item.get("qc_status")),
            "status": item.get("approval_status") or item.get("status") or "pending",
            "approval_status": item.get("approval_status") or "pending",
            "source": item.get("source") or item.get("related_type") or "approval",
            "inspector_display_name": item.get("inspector_name") or item.get("staff_display_name") or "Unknown User",
            "staff_id": item.get("staff_id") or item.get("created_by"),
            "staff_display_name": item.get("staff_display_name"),
            "submitted_at": item.get("submitted_at") or item.get("created_at"),
            "created_at": item.get("created_at") or item.get("submitted_at"),
            "evidence_url": evidence,
            "photo_url": evidence,
            "product_photo_url": item.get("product_photo_url") or evidence,
        }

    def _approval_detail_from_row(self, approval):
        related_type = approval.get("related_type")
        related_id = approval.get("related_id") or approval.get("report_id")
        if related_type == "qc_report" and related_id:
            report = (self._fetch("qc_reports", limit=1, filters=[("eq", "id", related_id)]) or [None])[0]
            if report:
                return self._approval_detail_from_report(report, approval)
        if related_id:
            report = (self._fetch("qc_reports", limit=1, filters=[("eq", "id", related_id)]) or [None])[0]
            if report:
                return self._approval_detail_from_report(report, approval)
        return self._approval_detail_from_report(approval, approval)

    def _approval_detail_from_report(self, report, approval):
        qc = self._approval_from_qc_report(report)
        batch = self._approval_batch_info(qc)
        evidence = self._approval_evidence_url(qc)
        history = self._approval_recheck_history(qc)
        return {
            "id": approval.get("id") or qc.get("id"),
            "approval_id": approval.get("id") or qc.get("approval_id") or qc.get("id"),
            "related_id": approval.get("related_id") or qc.get("id"),
            "batch_code": batch.get("batch_code") or qc.get("batch_code") or qc.get("batch_id"),
            "product_name": batch.get("product_name") or qc.get("product_name"),
            "batch_sequence": batch.get("batch_sequence") or qc.get("batch_sequence"),
            "cook_name": batch.get("cook_name") or qc.get("cook_name"),
            "quantity": batch.get("quantity") or qc.get("quantity"),
            "production_time": batch.get("production_time") or batch.get("created_at") or qc.get("production_time"),
            "qc_status": self._display_qc_status(qc.get("status") or qc.get("qc_status")),
            "inspection_type": qc.get("inspection_type")
            or qc.get("qc_stage")
            or qc.get("ccp_stage")
            or qc.get("check_type"),
            "temperature": qc.get("temperature") or qc.get("cooking_temperature") or qc.get("temperature_c"),
            "ph": qc.get("ph") or qc.get("ph_value"),
            "brix": qc.get("brix") or qc.get("brix_value"),
            "tds": qc.get("tds") or qc.get("tds_value"),
            "notes": qc.get("notes") or qc.get("parameter_notes") or qc.get("finding_notes"),
            "inspection_round": qc.get("inspection_round") or qc.get("batch_sequence"),
            "is_recheck": bool(qc.get("is_recheck") or qc.get("recheck_of") or qc.get("parent_report_id")),
            "inspector_display_name": qc.get("inspector_name") or qc.get("staff_display_name") or "Unknown User",
            "submitted_at": qc.get("submitted_at") or qc.get("created_at") or approval.get("created_at"),
            "evidence_url": evidence,
            "photo_url": evidence,
            "storage_path": qc.get("storage_path")
            or qc.get("product_storage_path")
            or qc.get("temperature_storage_path")
            or qc.get("barcode_storage_path"),
            "history": history,
        }

    def _approval_batch_info(self, qc):
        batch_id = qc.get("batch_id")
        batch_code = qc.get("batch_code")
        rows = []
        if batch_id:
            rows = self._fetch("production_batches", select="*, products(*)", limit=1, filters=[("eq", "id", batch_id)])
        if not rows and batch_code:
            rows = self._fetch(
                "production_batches", select="*, products(*)", limit=1, filters=[("eq", "batch_code", batch_code)]
            )
        batch = rows[0] if rows else {}
        product = batch.get("products") if isinstance(batch.get("products"), dict) else {}
        return {
            "batch_code": batch.get("batch_code"),
            "product_name": batch.get("product_name") or product.get("product_name"),
            "batch_sequence": batch.get("batch_sequence"),
            "cook_name": batch.get("cook_name"),
            "quantity": batch.get("quantity"),
            "production_time": batch.get("production_time") or batch.get("started_at") or batch.get("created_at"),
            "created_at": batch.get("created_at"),
        }

    def _approval_evidence_url(self, row):
        item = self.normalize_evidence_url(dict(row or {}))
        return (
            item.get("photo_url")
            or item.get("evidence_url")
            or item.get("product_photo_url")
            or item.get("temperature_photo_url")
            or item.get("barcode_photo_url")
        )

    def _approval_recheck_history(self, qc):
        batch_id = qc.get("batch_id")
        batch_code = qc.get("batch_code")
        if not (batch_id or batch_code):
            return []
        rows = self._fetch("qc_reports", order_by="created_at", limit=20)
        history = []
        for row in rows:
            if row.get("id") == qc.get("id") or not self._same_batch(row, batch_id, batch_code):
                continue
            normalized = self._normalize_qc_report(row)
            history.append(
                {
                    "id": normalized.get("id"),
                    "submitted_at": normalized.get("created_at") or normalized.get("submitted_at"),
                    "status": self._display_qc_status(normalized.get("status")),
                    "inspection_round": normalized.get("inspection_round") or normalized.get("batch_sequence"),
                    "inspector_display_name": normalized.get("staff_display_name") or normalized.get("inspector_name"),
                    "notes": normalized.get("notes"),
                }
            )
        return history

    def _same_batch(self, row, batch_id, batch_code):
        values = {
            str(row.get("batch_id") or ""),
            str(row.get("batch_code") or ""),
            str(row.get("related_batch_id") or ""),
            str(row.get("related_batch_code") or ""),
        }
        return bool((batch_id and str(batch_id) in values) or (batch_code and str(batch_code) in values))

    def _normalize_qc_report(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item.setdefault("report_type", "qc_report")
        item.setdefault("display_title", item.get("batch_code") or item.get("batch_id") or "QC Report")
        item["qc_stage"] = item.get("qc_stage") or item.get("ccp_stage")
        item["staff_name"] = item.get("staff_name") or item.get("inspector_name") or item.get("staff_display_name")
        if self._is_uuid_like(item.get("staff_name")):
            item["staff_name"] = item.get("staff_display_name")
        item["product_code"] = item.get("product_code") or item.get("sku_code") or item.get("barcode")
        item["photo_url"] = (
            item.get("photo_url")
            or item.get("cooking_photo_url")
            or item.get("barcode_photo_url")
            or item.get("label_photo_url")
            or item.get("product_photo_url")
            or item.get("temperature_photo_url")
        )
        self.normalize_evidence_url(item)
        return item

    def _normalize_qc_finding(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item["report_type"] = "qc_finding"
        item["status"] = item.get("status") or "finding"
        item["approval_status"] = item.get("approval_status") or "pending"
        item["display_title"] = item.get("reason") or "QC Finding"
        item["product_name"] = item.get("product_name") or "QC Finding"
        item["inspector_name"] = item.get("inspector_name") or item.get("staff_name") or item.get("staff_display_name")
        if self._is_uuid_like(item.get("inspector_name")):
            item["inspector_name"] = item.get("staff_display_name")
        self.normalize_evidence_url(item)
        return item

    def _approval_with_related(self, row):
        item = dict(row or {})
        related_type = item.get("related_type")
        related_id = item.get("related_id") or item.get("report_id")
        if related_type == "qc_report" and related_id:
            reports = self._fetch("qc_reports", limit=1, filters=[("eq", "id", related_id)])
            if reports:
                report = self._approval_from_qc_report(reports[0])
                report["approval_id"] = item.get("id")
                report["id"] = item.get("id")
                report["related_id"] = related_id
                report["approval_status"] = item.get("status") or report.get("approval_status") or "pending"
                report["status"] = report.get("status") or item.get("status") or "pending"
                report["created_at"] = item.get("created_at") or report.get("created_at")
                return report
        item = self._with_staff_display(item, ("staff_id", "requested_by", "created_by", "approved_by"))
        item.setdefault("approval_id", item.get("id"))
        item.setdefault("source", related_type or "approval")
        item.setdefault("approval_status", item.get("status") or "pending")
        item.setdefault("inspector_name", item.get("staff_display_name"))
        return item

    def _approval_from_finding(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by", "operator_id"))
        item["source"] = "qc_finding"
        item["batch_code"] = item.get("batch_code") or item.get("finding_type") or "QC Finding"
        item["status"] = item.get("status") or "finding"
        item["approval_status"] = item.get("approval_status") or "pending"
        item["inspector_name"] = item.get("inspector_name") or item.get("staff_name") or item.get("staff_display_name")
        if self._is_uuid_like(item.get("inspector_name")):
            item["inspector_name"] = item.get("staff_display_name")
        item["product_photo_url"] = item.get("photo_url")
        return item

    def _approval_from_temperature(self, row):
        item = self._with_staff_display(row, ("staff_id", "created_by"))
        room = (
            row.get("zone")
            or row.get("room_name")
            or (row.get("facility_rooms") or {}).get("name")
            or row.get("room_id")
            or "Temperature"
        )
        device = (
            row.get("device_type")
            or row.get("device_name")
            or (row.get("facility_devices") or {}).get("name")
            or row.get("device_id")
            or "Log"
        )
        return {
            "id": row.get("id"),
            "source": "temperature_log",
            "batch_code": f"{room} - {device}",
            "batch_id": row.get("room_id") or row.get("device_id"),
            "status": "warning" if self._temperature_needs_review(row) else "pending",
            "approval_status": "pending",
            "staff_id": item.get("staff_id") or row.get("created_by"),
            "staff_display_name": item.get("staff_display_name"),
            "staff_role": item.get("staff_role"),
            "staff_email": item.get("staff_email"),
            "inspector_name": row.get("staff_name") or item.get("staff_display_name"),
            "product_photo_url": row.get("photo_url"),
            "storage_path": row.get("storage_path"),
            "created_at": row.get("recorded_at") or row.get("created_at"),
        }

    def _normalize_batch_filter(self, value):
        text = str(value or "").strip().lower().replace("_", " ")
        aliases = {
            "": "",
            "semua": "",
            "all": "",
            "belum qc": "belum qc",
            "no qc": "belum qc",
            "pending approval": "pending approval",
            "pending": "pending approval",
            "approved": "approved",
            "rejected": "rejected",
            "reject": "rejected",
            "pass": "pass",
            "passed": "pass",
            "hold": "hold",
            "warning": "hold",
            "pending review": "hold",
            "fail": "fail",
            "failed": "fail",
        }
        return aliases.get(text, text)

    def _display_qc_status(self, value):
        key = self._normalize_batch_filter(value)
        return {
            "pass": "PASS",
            "hold": "HOLD",
            "fail": "FAIL",
            "pending approval": "Pending Approval",
            "belum qc": "Belum QC",
        }.get(key, str(value or "Belum QC"))

    def _display_approval_status(self, value):
        key = self._normalize_batch_filter(value)
        return {
            "pending approval": "Pending Approval",
            "approved": "Approved",
            "rejected": "Rejected",
        }.get(key, "Pending Approval" if not key else str(value))
