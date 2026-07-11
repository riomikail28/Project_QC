"""Real-data service for the staff inspection page."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.database.supabase_client import direct_db_query, get_client
from backend.services.audit_service import write_audit
from backend.services.google_apps_script_service import build_qc_report_payload, send_qc_report
from backend.services.storage_service import delete_photo, upload_file_storage

logger = logging.getLogger("qc.services.inspection")


class InspectionService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _fail(self, message, status_code=None):
        result = {"success": False, "data": None, "message": message}
        if status_code:
            result["status_code"] = status_code
        return result

    def _jakarta_today(self):
        return datetime.now(timezone(timedelta(hours=7))).date().isoformat()

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
            if method in ("eq", "is_", "is"):
                if value == "null" or value is None:
                    parts.append(f"{field}=is.null")
                else:
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
            select="*, products(*), qc_reports(*)",
            order_by="created_at",
            limit=limit,
        )
        active = [
            self._batch_view(row)
            for row in rows
            if self._norm_status(row.get("status") or row.get("final_qc_status")) in {"pending", "hold", "warning", "", "cooking", "packing", "completed", "finished", "in_progress"}
        ]
        return self._ok(active)

    def active_batches_for_sku(self, sku, limit=20):
        sku = str(sku or "").strip()
        if not sku:
            return self._ok({"active_batches": []})
        product = self._find_product(sku)
        product_id = (product or {}).get("id")
        product_name = (product or {}).get("product_name")
        rows = self._fetch("production_batches", order_by="created_at", limit=500)
        active_statuses = {"", "pending", "in_progress", "hold", "warning", "pending_review", "on_hold"}
        candidates = []
        for row in rows:
            status = self._norm_status(row.get("status") or row.get("final_qc_status"))
            if status not in active_statuses:
                continue
            values = {
                str(row.get("batch_code") or "").lower(),
                str(row.get("product_name") or "").lower(),
                str(row.get("product_code") or "").lower(),
                str(row.get("sku_code") or "").lower(),
                str(row.get("barcode") or "").lower(),
                str(row.get("product_id") or "").lower(),
            }
            if (
                sku.lower() in values
                or (product_id and str(product_id).lower() in values)
                or (product_name and product_name.lower() in values)
            ):
                view = self._batch_view(row)
                last = self._last_report_for_batch(row.get("id"), row.get("batch_code"))
                view["last_stage"] = (last or {}).get("qc_stage") or (last or {}).get("ccp_stage")
                view["last_status"] = (last or {}).get("status") or row.get("final_qc_status") or row.get("status")
                candidates.append(view)
        return self._ok({"active_batches": candidates[:limit]})

    def product_shortcuts(self, limit=8):
        rows = self._fetch("products", order_by="product_code", desc=False, limit=limit, filters=[("eq", "is_active", True)])
        if not rows:
            rows = self._fetch("products", order_by="product_code", desc=False, limit=limit)
        return self._ok([{
            "id": row.get("id"),
            "product_code": row.get("product_code") or row.get("sku_code") or "-",
            "product_name": row.get("product_name") or "Unnamed product",
        } for row in rows])

    def products(self, limit=1000):
        rows = self._fetch("products", order_by="product_code", desc=False, limit=limit, filters=[("eq", "is_active", True)])
        return self._ok([self._product_picker_item(row) for row in rows])

    def recent_submissions(self, limit=10):
        reports = self._fetch("qc_reports", order_by="created_at", limit=limit)
        if reports:
            return self._ok([self._report_view(row) for row in reports])
        logs = self._fetch("production_batch_logs", order_by="recorded_at", limit=limit)
        return self._ok([self._log_view(row) for row in logs])

    def submit_qc(self, payload, files=None, actor_id=None, actor_role=None):
        files = files or {}
        staff_id = payload.get("staff_id") or actor_id
        is_admin = str(actor_role or "").lower() == "admin"
        barcode = str(payload.get("barcode") or payload.get("sku_code") or "").strip()
        sku_code = str(payload.get("sku_code") or barcode or "").strip()
        batch_id = payload.get("batch_id") or None
        batch_code = str(payload.get("batch_code") or "").strip()
        operational_date = str(payload.get("operational_date") or payload.get("production_date") or self._jakarta_today()).strip()
        parent_inspection = str(payload.get("parent_inspection") or payload.get("parent_inspection_id") or "").strip() or None
        if not staff_id:
            return self._fail("staff_id wajib tersedia dari sesi login")
        if not sku_code:
            return self._fail("SKU atau barcode wajib diisi")
        qc_stage = self._normalize_stage(payload.get("qc_stage") or payload.get("ccp_stage"))
        if not qc_stage:
            return self._fail("Jenis pengecekan wajib dipilih: cooking_check atau final_check")
        raw_status = payload.get("qc_status") or payload.get("status")
        if not raw_status:
            return self._fail("Status QC wajib diisi")
        qc_status = self._norm_status(raw_status)
        if qc_status == "failed":
            qc_status = "fail"
        if qc_status not in {"pass", "hold", "fail"}:
            return self._fail("Status QC tidak valid")
        temperature = payload.get("temperature")
        if qc_stage in ("cooking_check", "cooking_sensory") and temperature in (None, ""):
            return self._fail("Temperature is required for Cooking Check")

        product = self._resolve_product(payload.get("product_id"), sku_code)
        if payload.get("product_id") and not product:
            return self._fail("Produk tidak ditemukan atau sudah nonaktif")
        product_id = (product or {}).get("id")
        sku_code = (product or {}).get("product_code") or (product or {}).get("sku_code") or sku_code
        barcode = (product or {}).get("product_code") or barcode or sku_code
        product_name = (product or {}).get("product_name") or payload.get("product_name") or "Manual SKU"
        if not batch_id:
            active = self.active_batches_for_sku(sku_code, limit=1).get("data", {}).get("active_batches", [])
            if active and not payload.get("force_new_batch"):
                batch_id = active[0].get("id")
                batch_code = batch_code or active[0].get("batch_code")
        if not batch_code:
            batch_code = self._generated_batch_code()
        batch_id = batch_id or self._ensure_batch(batch_code, product_id, product_name, staff_id)
        batch_row = self._batch_by_id_or_code(batch_id, batch_code)
        batch_date = str((batch_row or {}).get("production_date") or "")[:10]
        if batch_row and batch_date and batch_date != operational_date:
            return self._fail("Batch ini berasal dari tanggal berbeda. Pilih batch hari ini atau buat batch baru.", status_code=409)

        # State transition and locking validations
        existing_report = None
        if qc_stage == "cooking_sensory":
            filters = [("eq", "batch_id", batch_id), ("eq", "qc_stage", "cooking_sensory")]
            if parent_inspection:
                filters.append(("eq", "parent_inspection", parent_inspection))
            else:
                filters.append(("is_", "parent_inspection", "null"))
            existing = self._fetch("qc_reports", limit=1, filters=filters)
            if existing:
                existing_report = existing[0]
        elif qc_stage == "cooking_instrument":
            filters = [("eq", "batch_id", batch_id), ("eq", "qc_stage", "cooking_instrument")]
            if parent_inspection:
                filters.append(("eq", "parent_inspection", parent_inspection))
            else:
                filters.append(("is_", "parent_inspection", "null"))
            existing = self._fetch("qc_reports", limit=1, filters=filters)
            if existing:
                existing_report = existing[0]
        elif qc_stage == "packing":
            sensory_filters = [("eq", "batch_id", batch_id), ("eq", "qc_stage", "cooking_sensory")]
            instr_filters = [("eq", "batch_id", batch_id), ("eq", "qc_stage", "cooking_instrument")]
            if parent_inspection:
                sensory_filters.append(("eq", "parent_inspection", parent_inspection))
                instr_filters.append(("eq", "parent_inspection", parent_inspection))
            else:
                sensory_filters.append(("is_", "parent_inspection", "null"))
                instr_filters.append(("is_", "parent_inspection", "null"))
            
            existing_sensory = self._fetch("qc_reports", limit=1, filters=sensory_filters)
            existing_instrument = self._fetch("qc_reports", limit=1, filters=instr_filters)
            if not existing_sensory or not existing_instrument:
                return self._fail("Tahap Cooking belum lengkap (Sensory & Instrument harus diisi terlebih dahulu)", status_code=400)
            
            pack_filters = [("eq", "batch_id", batch_id), ("eq", "qc_stage", "packing")]
            if parent_inspection:
                pack_filters.append(("eq", "parent_inspection", parent_inspection))
            else:
                pack_filters.append(("is_", "parent_inspection", "null"))
            existing = self._fetch("qc_reports", limit=1, filters=pack_filters)
            if existing:
                existing_report = existing[0]

        active_lock = self._active_inspection_for_batch(batch_id, batch_code)
        if active_lock and not is_admin:
            locker = active_lock.get("staff_name") or active_lock.get("inspector_name") or active_lock.get("staff_id") or "staff lain"
            return self._fail(f"Sedang diperiksa oleh {locker}", status_code=409)

        inspection_round = 1
        if parent_inspection:
            parent = self._inspection_by_id(parent_inspection)
            inspection_round = int((parent or {}).get("inspection_round") or 1) + 1

        uploaded_files = []
        try:
            completed_at = datetime.now(timezone.utc).isoformat()
            uploads = {
                "generic": self._preuploaded(payload.get("photo_url"), payload.get("storage_path")),
                "cooking": self._preuploaded(payload.get("cooking_photo_url"), payload.get("cooking_storage_path")),
                "barcode": self._preuploaded(payload.get("barcode_photo_url"), payload.get("barcode_storage_path")),
                "label": self._preuploaded(payload.get("label_photo_url"), payload.get("label_storage_path")),
            }
            file_map = self._file_map(files)
            if qc_stage in ("cooking_check", "cooking_sensory", "cooking_instrument"):
                for photo_file in file_map.get("cooking_photo") or file_map.get("photo") or []:
                    uploaded = self._upload_if_present(photo_file, staff_id, "cooking", batch_id or batch_code)
                    if uploaded:
                        uploaded_files.append(("cooking", uploaded))
                        uploads["cooking"]["urls"].append(uploaded.url)
                        uploads["cooking"]["paths"].append(uploaded.storage_path)
                for photo_file in file_map.get("barcode_photo") or []:
                    uploaded = self._upload_if_present(photo_file, staff_id, "barcode", batch_id or batch_code)
                    if uploaded:
                        uploaded_files.append(("barcode", uploaded))
                        uploads["barcode"]["urls"].append(uploaded.url)
                        uploads["barcode"]["paths"].append(uploaded.storage_path)
            elif qc_stage in ("final_check", "packing"):
                for field_name, bucket_key in (("barcode_photo", "barcode"), ("label_photo", "label"), ("photo", "generic")):
                    for photo_file in file_map.get(field_name) or []:
                        uploaded = self._upload_if_present(photo_file, staff_id, bucket_key, batch_id or batch_code)
                        if uploaded:
                            uploaded_files.append((bucket_key, uploaded))
                            uploads[bucket_key]["urls"].append(uploaded.url)
                            uploads[bucket_key]["paths"].append(uploaded.storage_path)

            cooking_url = self._join(uploads["cooking"]["urls"])
            cooking_path = self._join(uploads["cooking"]["paths"])
            barcode_url = self._join(uploads["barcode"]["urls"])
            barcode_path = self._join(uploads["barcode"]["paths"])
            label_url = self._join(uploads["label"]["urls"])
            label_path = self._join(uploads["label"]["paths"])
            generic_url = self._join(uploads["generic"]["urls"])
            generic_path = self._join(uploads["generic"]["paths"])
            photo_urls = [item for item in [cooking_url, barcode_url, label_url, generic_url] if item]
            storage_paths = [item for item in [cooking_path, barcode_path, label_path, generic_path] if item]
            photo_url = self._join(photo_urls)
            storage_path = self._join(storage_paths)

            report_payload = {
                "batch_id": batch_id,
                "batch_code": batch_code,
                "product_id": product_id or None,
                "product_name": product_name,
                "staff_id": staff_id,
                "staff_name": payload.get("staff_name") or payload.get("inspector_name"),
                "inspector_name": payload.get("staff_name") or payload.get("inspector_name"),
                "status": qc_status,
                "approval_status": "pending",
                "barcode": barcode or sku_code or None,
                "qc_stage": qc_stage,
                "ccp_stage": qc_stage,
                "temperature": temperature or None,
                "notes": payload.get("notes") or None,
                "inspection_round": inspection_round,
                "parent_inspection": parent_inspection,
                "is_active": False,
                "completed_at": completed_at,
                "inspection_result": {
                    "sku_code": sku_code,
                    "barcode": barcode or sku_code,
                    "qc_stage": qc_stage,
                    "ccp_stage": qc_stage,
                    "temperature": temperature,
                    "ph_value": payload.get("ph_value") or payload.get("ph"),
                    "brix_value": payload.get("brix_value") or payload.get("brix"),
                    "tds_value": payload.get("tds_value") or payload.get("tds"),
                    "mfg_date": payload.get("mfg_date") or payload.get("mfg"),
                    "exp_date": payload.get("exp_date") or payload.get("exp"),
                    "gramasi_1": payload.get("gramasi_1"),
                    "gramasi_2": payload.get("gramasi_2"),
                    "gramasi_3": payload.get("gramasi_3"),
                    "gramasi_4": payload.get("gramasi_4"),
                    "gramasi_5": payload.get("gramasi_5"),
                    "notes": payload.get("notes"),
                    "qc_status": qc_status,
                    "inspection_round": inspection_round,
                    "parent_inspection": parent_inspection,
                },
                "photo_url": photo_url,
                "storage_path": storage_path,
                "product_photo_url": photo_url,
                "product_storage_path": storage_path,
                "cooking_photo_url": cooking_url,
                "cooking_storage_path": cooking_path,
                "barcode_photo_url": barcode_url,
                "barcode_storage_path": barcode_path,
                "label_photo_url": label_url,
                "label_storage_path": label_path,
            }
            report_payload = {key: value for key, value in report_payload.items() if value is not None}
            if existing_report:
                report_id = existing_report.get("id")
                self.sb.table("qc_reports").update(report_payload).eq("id", report_id).execute()
                fetched = self._fetch("qc_reports", limit=1, filters=[("eq", "id", report_id)])
                report = fetched[0] if fetched else {**existing_report, **report_payload}
            else:
                report = self._insert("qc_reports", report_payload)
                report_id = report.get("id") if isinstance(report, dict) else None

            if barcode:
                self._insert("barcode_labels", {
                    "batch_id": batch_id,
                    "batch_code": batch_code or str(batch_id),
                    "product_id": product_id or None,
                    "product_name": product_name,
                    "barcode_value": barcode,
                    "barcode_photo_url": report_payload.get("product_photo_url"),
                    "staff_id": staff_id,
                    "staff_name": payload.get("staff_name") or payload.get("inspector_name"),
                }, required=False)

            report_id = report.get("id") if isinstance(report, dict) else None
            for evidence_type, uploaded in uploaded_files:
                self._insert("qc_evidence", {
                    "file_name": uploaded.file_name,
                    "file_type": uploaded.file_type,
                    "mime_type": uploaded.file_type,
                    "file_size": uploaded.file_size,
                    "bucket": uploaded.bucket,
                    "storage_path": uploaded.storage_path,
                    "public_url": uploaded.url,
                    "uploaded_by": staff_id,
                    "related_type": "qc_report",
                    "related_id": report_id or batch_id or batch_code,
                    "metadata": {"qc_stage": qc_stage, "evidence_type": evidence_type},
                }, required=False)

            if report_id:
                self._insert("approvals", {
                    "related_type": "qc_report",
                    "related_id": report_id,
                    "status": "pending",
                    "requested_by": staff_id,
                    "requester_id": staff_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, required=False)
            self._update_batch_status(batch_id, batch_code, report or report_payload)

            try:
                write_audit("submit_inspection", "qc_report", str(report_id), after=report or report_payload)
                if uploaded_files:
                    write_audit(
                        "upload_inspection_photo",
                        "qc_report",
                        str(report_id),
                        metadata={"storage_paths": [item.storage_path for _, item in uploaded_files], "qc_stage": qc_stage},
                    )
            except Exception:
                pass
            resolved_staff_name = payload.get("staff_name") or payload.get("inspector_name") or staff_id or "Unknown User"
            if resolved_staff_name and len(str(resolved_staff_name)) == 36 and str(resolved_staff_name).count("-") == 4:
                try:
                    user_rows = self._fetch("users", filters=[("eq", "staff_account_id", staff_id)], limit=1)
                    if user_rows and user_rows[0].get("full_name"):
                        resolved_staff_name = user_rows[0]["full_name"]
                    else:
                        staff_rows = self._fetch("staff_accounts", filters=[("eq", "id", staff_id)], limit=1)
                        if staff_rows and staff_rows[0].get("username"):
                            resolved_staff_name = staff_rows[0]["username"]
                except Exception as exc:
                    logger.warning("Failed to resolve staff name in inspection: %s", exc)

            created_at = (report or {}).get("created_at") or datetime.now(timezone.utc).isoformat()
            send_qc_report(build_qc_report_payload({
                **report_payload,
                **(report or {}),
                "staff_display_name": resolved_staff_name,
                "batch_sequence": (batch_row or {}).get("batch_sequence"),
                "cook_name": (batch_row or {}).get("cook_name"),
                "quantity": (batch_row or {}).get("quantity"),
                "production_shift": (batch_row or {}).get("production_shift") or (batch_row or {}).get("shift"),
                "ph_value": payload.get("ph_value") or payload.get("ph"),
                "brix_value": payload.get("brix_value") or payload.get("brix"),
                "tds_value": payload.get("tds_value") or payload.get("tds"),
                "gramasi_1": payload.get("gramasi_1"),
                "gramasi_2": payload.get("gramasi_2"),
                "gramasi_3": payload.get("gramasi_3"),
                "gramasi_4": payload.get("gramasi_4"),
                "gramasi_5": payload.get("gramasi_5"),
                "created_at": created_at,
                "source_type": "qc_report",
                "source_id": report_id,
            }), background=True)
            return self._ok({
                "report_id": report_id,
                "batch_id": batch_id,
                "batch_code": batch_code,
                "qc_stage": qc_stage,
                "inspection_round": inspection_round,
                "parent_inspection": parent_inspection,
                "approval_status": "pending",
                "photo_url": report_payload.get("photo_url"),
                **(report or report_payload),
            }, "QC check submitted")
        except Exception as exc:
            for _, uploaded in uploaded_files:
                delete_photo(uploaded.storage_path)
            logger.exception("Submit QC failed: %s", exc)
            return self._fail(str(exc))

    def _generated_batch_code(self):
        return f"QC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

    def _find_product(self, sku_code):
        if not sku_code:
            return None
        rows = self._fetch("products", limit=1, filters=[("eq", "product_code", sku_code)])
        if not rows:
            rows = self._fetch("products", limit=1, filters=[("eq", "sku_code", sku_code)])
        if not rows:
            rows = self._fetch("products", limit=1, filters=[("eq", "barcode", sku_code)])
        return rows[0] if rows else None

    def _resolve_product(self, product_id, sku_code):
        product_id = str(product_id or "").strip()
        if product_id:
            rows = self._fetch("products", limit=1, filters=[("eq", "id", product_id)])
            product = rows[0] if rows else None
            if product and product.get("is_active") is not False:
                return product
            return None
        return self._find_product(sku_code)

    def _product_picker_item(self, row):
        return {
            "id": row.get("id"),
            "product_code": row.get("product_code") or row.get("sku_code"),
            "product_name": row.get("product_name"),
            "shelf_life_days": row.get("shelf_life_days"),
            "is_active": row.get("is_active", True),
        }

    def _ensure_batch(self, batch_code, product_id, product_name, staff_id):
        payload = {
            "batch_code": batch_code,
            "product_id": product_id or None,
            "product_name": product_name,
            "production_date": self._jakarta_today(),
            "status": "pending",
            "created_by": staff_id,
        }
        batch = self._insert("production_batches", {k: v for k, v in payload.items() if v is not None}, required=False)
        return batch.get("id") if isinstance(batch, dict) else None

    def _batch_by_id_or_code(self, batch_id, batch_code):
        if batch_id:
            rows = self._fetch("production_batches", limit=1, filters=[("eq", "id", batch_id)])
            if rows:
                return rows[0]
        if batch_code:
            rows = self._fetch("production_batches", limit=1, filters=[("eq", "batch_code", batch_code)])
            if rows:
                return rows[0]
        return None

    def _normalize_stage(self, value):
        raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "cooking": "cooking_check",
            "cook": "cooking_check",
            "cooking_check": "cooking_check",
            "final": "final_check",
            "final_check": "final_check",
            "label": "final_check",
            "barcode": "final_check",
            "cooking_sensory": "cooking_sensory",
            "cooking_instrument": "cooking_instrument",
            "packing": "packing",
        }
        return aliases.get(raw, raw)

    def _file_map(self, files):
        if isinstance(files, dict):
            return {key: [item for item in (value or []) if item] for key, value in files.items()}
        return {"photo": [item for item in (files or []) if item]}

    def _upload_if_present(self, photo_file, staff_id, category, related_id):
        if not photo_file or not getattr(photo_file, "filename", ""):
            return None
        return upload_file_storage(photo_file, staff_id=staff_id, category=category, related_id=related_id)

    def _preuploaded(self, urls, paths):
        return {
            "urls": [item for item in str(urls or "").split(";") if item],
            "paths": [item for item in str(paths or "").split(";") if item],
        }

    def _join(self, values):
        items = [item for item in values if item]
        return ";".join(items) if items else None

    def _last_report_for_batch(self, batch_id, batch_code):
        filters = []
        if batch_id:
            filters.append(("eq", "batch_id", batch_id))
        rows = self._fetch("qc_reports", order_by="created_at", limit=20, filters=filters) if filters else []
        if not rows and batch_code:
            rows = self._fetch("qc_reports", order_by="created_at", limit=20, filters=[("eq", "batch_code", batch_code)])
        return rows[0] if rows else None

    def _active_inspection_for_batch(self, batch_id, batch_code):
        rows = []
        if batch_id:
            rows = self._fetch(
                "qc_reports",
                order_by="created_at",
                limit=1,
                filters=[("eq", "batch_id", batch_id), ("eq", "is_active", True)],
            )
        if not rows and batch_code:
            rows = self._fetch(
                "qc_reports",
                order_by="created_at",
                limit=1,
                filters=[("eq", "batch_code", batch_code), ("eq", "is_active", True)],
            )
        return rows[0] if rows else None

    def _inspection_by_id(self, inspection_id):
        if not inspection_id:
            return None
        rows = self._fetch("qc_reports", limit=1, filters=[("eq", "id", inspection_id)])
        return rows[0] if rows else None

    def _update_batch_status(self, batch_id, batch_code, current_report):
        if not batch_id or not self.sb:
            return
        try:
            reports = self._fetch("qc_reports", order_by="created_at", limit=100, filters=[("eq", "batch_id", batch_id)])
            reports.append(current_report)
            stages = {row.get("qc_stage") or row.get("ccp_stage"): self._norm_status(row.get("status")) for row in reports}
            statuses = set(stages.values())
            payload = {"updated_at": datetime.now(timezone.utc).isoformat()}
            
            batch_row = self._batch_by_id_or_code(batch_id, batch_code)
            batch_sequence = int((batch_row or {}).get("batch_sequence") or 1)

            # Check sensory, instrument and packing status
            has_sensory = "cooking_sensory" in stages
            has_instrument = "cooking_instrument" in stages
            has_packing = "packing" in stages

            if "fail" in statuses:
                payload.update({"status": "failed", "final_qc_status": "fail"})
            elif "hold" in statuses:
                payload.update({"status": "on_hold", "final_qc_status": "hold"})
            elif batch_sequence > 1 and has_sensory and has_instrument:
                if stages.get("cooking_instrument") == "pass":
                    payload.update({"status": "completed", "final_qc_status": "pass"})
                else:
                    payload.update({"status": "cooking", "final_qc_status": "pending"})
            elif (stages.get("cooking_check") == "pass" and stages.get("final_check") == "pass") or (has_sensory and has_instrument and has_packing and stages.get("packing") == "pass"):
                payload.update({"status": "completed", "final_qc_status": "pass"})
            elif has_sensory and has_instrument and not has_packing:
                payload.update({"status": "packing", "final_qc_status": "pending"})
            else:
                payload.update({"status": "cooking", "final_qc_status": "pending"})

            # Calculate expired_date automatically when packing is submitted
            if has_packing:
                try:
                    batch_row = self._batch_by_id_or_code(batch_id, batch_code)
                    product_id = current_report.get("product_id") or (batch_row or {}).get("product_id")
                    if product_id:
                        prod_res = self.sb.table("products").select("shelf_life_days").eq("id", product_id).execute().data or []
                        shelf_life = prod_res[0].get("shelf_life_days") if prod_res else 3
                        if shelf_life is None:
                            shelf_life = 3
                    else:
                        shelf_life = 3
                    from datetime import date, timedelta
                    insp_res = current_report.get("inspection_result") or {}
                    mfg_str = insp_res.get("mfg_date") or current_report.get("production_date") or (batch_row or {}).get("production_date") or datetime.now().isoformat()
                    try:
                        mfg_dt = datetime.fromisoformat(mfg_str).date()
                    except Exception:
                        try:
                            mfg_dt = datetime.strptime(str(mfg_str)[:10], "%Y-%m-%d").date()
                        except Exception:
                            mfg_dt = date.today()
                    
                    expired_dt = insp_res.get("exp_date") or (mfg_dt + timedelta(days=shelf_life)).isoformat()
                    payload.update({
                        "production_date": mfg_dt.isoformat(),
                        "expired_date": expired_dt
                    })
                except Exception as exp_err:
                    logger.warning("Failed to calculate expired_date automatically: %s", exp_err)

            self.sb.table("production_batches").update(payload).eq("id", batch_id).execute()
        except Exception:
            logger.warning("Batch status update skipped for %s/%s", batch_id, batch_code, exc_info=True)

    def _insert(self, table, payload, required=True):
        if not self.sb:
            if required:
                raise RuntimeError("Database belum terhubung")
            return None
        insert_payload = dict(payload)
        while True:
            try:
                return (self.sb.table(table).insert(insert_payload).execute().data or [insert_payload])[0]
            except Exception as exc:
                missing_column = self._schema_cache_missing_column(exc)
                if missing_column and missing_column in insert_payload:
                    insert_payload = {key: value for key, value in insert_payload.items() if key != missing_column}
                    logger.warning(
                        "Retrying %s insert without missing schema-cache column %s",
                        table,
                        missing_column,
                    )
                    continue
                if required:
                    raise
                logger.warning("Optional insert skipped for %s", table, exc_info=True)
                return None

    def _schema_cache_missing_column(self, exc):
        text = str(exc or "")
        if "PGRST204" not in text and "schema cache" not in text:
            return None
        match = re.search(r"Could not find the '([^']+)' column", text)
        return match.group(1) if match else None

    def _batch_view(self, row):
        product = row.get("products") or {}
        return {
            "id": row.get("id"),
            "batch_code": row.get("batch_code") or "-",
            "product_name": product.get("product_name") or row.get("product_name") or "Unknown product",
            "batch_sequence": row.get("batch_sequence"),
            "cook_name": row.get("cook_name"),
            "quantity": row.get("quantity"),
            "production_shift": row.get("production_shift") or row.get("shift"),
            "production_date": row.get("production_date"),
            "production_time": row.get("production_time") or row.get("created_at"),
            "status": self._norm_status(row.get("final_qc_status") or row.get("status")) or "pending",
            "final_qc_status": self._norm_status(row.get("final_qc_status")),
            "created_at": row.get("created_at"),
            "qc_reports": row.get("qc_reports") or [],
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
