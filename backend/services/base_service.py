import logging
import os
from datetime import datetime, timedelta, timezone

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.services.base")


class BaseService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()
        self._staff_profile_cache = {}

    def _empty(self, data):
        return {"success": True, "data": data, "message": "OK"}

    def _fail(self, message):
        return {"success": False, "data": None, "message": message, "detail": message}

    def _first_non_empty(self, *values):
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return value
        return None

    def _is_uuid_like(self, value):
        text = str(value or "").strip().lower()
        if len(text) != 36:
            return False
        parts = text.split("-")
        return (
            len(parts) == 5
            and [len(part) for part in parts] == [8, 4, 4, 4, 12]
            and all(all(char in "0123456789abcdef" for char in part) for part in parts)
        )

    def _staff_identity(
        self, row, id_fields=("staff_id", "actor_id", "created_by", "operator_id", "uploaded_by", "requested_by")
    ):
        row = row or {}
        nested_sources = (
            row.get("staff_accounts"),
            row.get("users"),
            row.get("profile"),
            row.get("staff_profile"),
            row.get("staff"),
        )
        nested_values = []
        for source in nested_sources:
            if isinstance(source, dict):
                nested_values.extend(
                    [
                        source.get("full_name"),
                        source.get("name"),
                        source.get("username"),
                        source.get("email"),
                    ]
                )
        direct_values = [
            row.get("staff_display_name"),
            row.get("actor_display_name"),
            row.get("full_name"),
            row.get("name"),
            row.get("username"),
            row.get("email"),
            row.get("staff_name"),
            row.get("inspector_name"),
            row.get("actor_name"),
        ]
        staff_id = self._first_non_empty(*(row.get(field) for field in id_fields))
        profile = self._staff_profile(staff_id)
        display_name = self._first_non_empty(
            profile.get("full_name"),
            profile.get("name"),
            profile.get("username"),
            profile.get("email"),
            *(nested_values + direct_values),
        )
        if self._is_uuid_like(display_name):
            display_name = None
        return display_name or "Unknown User", staff_id

    def _with_staff_display(
        self, row, id_fields=("staff_id", "actor_id", "created_by", "operator_id", "uploaded_by", "requested_by")
    ):
        item = dict(row or {})
        display_name, staff_id = self._staff_identity(item, id_fields)
        profile = self._staff_profile(staff_id)
        if staff_id and not item.get("staff_id") and "staff_id" in id_fields:
            item["staff_id"] = staff_id
        item["staff_display_name"] = display_name
        if self._is_uuid_like(item.get("staff_name")):
            item["staff_name"] = display_name
        if self._is_uuid_like(item.get("inspector_name")):
            item["inspector_name"] = display_name
        if self._is_uuid_like(item.get("actor_name")):
            item["actor_name"] = display_name
        nested = item.get("staff_accounts") if isinstance(item.get("staff_accounts"), dict) else {}
        item["staff_role"] = item.get("staff_role") or item.get("role") or profile.get("role") or nested.get("role")
        item["staff_role"] = item.get("staff_role") or "staff"
        item["staff_email"] = (
            item.get("staff_email") or item.get("email") or profile.get("email") or nested.get("email")
        )
        return item

    def _staff_profile(self, staff_id):
        if not staff_id:
            return {}
        if staff_id in self._staff_profile_cache:
            return self._staff_profile_cache[staff_id]
        account = (self._fetch("staff_accounts", limit=1, filters=[("eq", "id", staff_id)]) or [None])[0] or {}
        users = self._fetch("users", limit=1, filters=[("eq", "staff_account_id", staff_id)])
        if not users:
            users = self._fetch("users", limit=1, filters=[("eq", "id", staff_id)])
        user = (users or [None])[0] or {}
        profile = {
            "full_name": user.get("full_name") or account.get("full_name"),
            "name": user.get("name") or account.get("name"),
            "username": account.get("username") or user.get("username"),
            "email": user.get("email") or account.get("email"),
            "role": user.get("role") or account.get("role"),
        }
        self._staff_profile_cache[staff_id] = {key: value for key, value in profile.items() if value}
        return self._staff_profile_cache[staff_id]

    def _prefetch_staff_profiles(self, staff_ids):
        needed_ids = {str(sid) for sid in staff_ids if sid and str(sid) not in self._staff_profile_cache}
        if not needed_ids:
            return

        accounts = []
        if self.sb:
            query_builder = self.sb.table("staff_accounts")
            if hasattr(query_builder, "in_"):
                try:
                    res = query_builder.select("id,role,username,full_name,email").in_("id", list(needed_ids)).execute()
                    accounts = res.data or []
                except Exception as exc:
                    logger.warning("Prefetch staff accounts failed: %s", exc)
            else:
                try:
                    res = query_builder.select("id,role,username,full_name,email").execute()
                    accounts = [r for r in (res.data or []) if str(r.get("id")) in needed_ids]
                except Exception as exc:
                    logger.warning("Mock prefetch staff accounts failed: %s", exc)
        else:
            from backend.database.supabase_client import direct_db_query

            try:
                ids_str = ",".join(needed_ids)
                accounts = direct_db_query("staff_accounts", "GET", None, f"id=in.({ids_str})") or []
            except Exception as exc:
                logger.warning("Direct prefetch staff accounts failed: %s", exc)

        users = []
        if needed_ids:
            if self.sb:
                query_builder_users = self.sb.table("users")
                if hasattr(query_builder_users, "in_"):
                    try:
                        res = (
                            query_builder_users.select(
                                "id,staff_account_id,email,role,full_name,display_name,username,name"
                            )
                            .in_("staff_account_id", list(needed_ids))
                            .execute()
                        )
                        users = res.data or []
                        res_by_id = (
                            query_builder_users.select(
                                "id,staff_account_id,email,role,full_name,display_name,username,name"
                            )
                            .in_("id", list(needed_ids))
                            .execute()
                        )
                        users.extend(res_by_id.data or [])
                    except Exception as exc:
                        logger.warning("Prefetch users failed: %s", exc)
                else:
                    try:
                        res = query_builder_users.select(
                            "id,staff_account_id,email,role,full_name,display_name,username,name"
                        ).execute()
                        users = [
                            r
                            for r in (res.data or [])
                            if str(r.get("staff_account_id")) in needed_ids or str(r.get("id")) in needed_ids
                        ]
                    except Exception as exc:
                        logger.warning("Mock prefetch users failed: %s", exc)
            else:
                from backend.database.supabase_client import direct_db_query

                try:
                    ids_str = ",".join(needed_ids)
                    users = direct_db_query("users", "GET", None, f"staff_account_id=in.({ids_str})") or []
                    users_by_id = direct_db_query("users", "GET", None, f"id=in.({ids_str})") or []
                    users.extend(users_by_id)
                except Exception as exc:
                    logger.warning("Direct prefetch users failed: %s", exc)

        accounts_by_id = {str(a["id"]): a for a in accounts if "id" in a}
        users_by_staff_id = {str(u["staff_account_id"]): u for u in users if "staff_account_id" in u}
        users_by_id = {str(u["id"]): u for u in users if "id" in u}

        for staff_id in needed_ids:
            account = accounts_by_id.get(staff_id, {})
            user = users_by_staff_id.get(staff_id) or users_by_id.get(staff_id) or {}
            profile = {
                "full_name": user.get("full_name") or account.get("full_name"),
                "name": user.get("name") or account.get("name"),
                "username": account.get("username") or user.get("username"),
                "email": user.get("email") or account.get("email"),
                "role": user.get("role") or account.get("role"),
            }
            self._staff_profile_cache[staff_id] = {k: v for k, v in profile.items() if v}

    def _prefetch_for_rows(self, rows, fields):
        staff_ids = set()
        for row in rows or []:
            for field in fields:
                val = row.get(field)
                if val:
                    staff_ids.add(val)
        if staff_ids:
            self._prefetch_staff_profiles(list(staff_ids))

    def _count(self, table: str, filters: list[tuple[str, str, object]] | None = None) -> int:
        if not self.sb:
            return 0
        query = self.sb.table(table).select("id", count="exact").limit(0)
        for op, field, value in filters or []:
            query = getattr(query, op)(field, value)
        res = query.execute()
        return res.count if getattr(res, "count", None) is not None else 0

    def _date_filters(self, field, date_value):
        if not date_value:
            return []
        start = f"{date_value}T00:00:00Z"
        end = (datetime.fromisoformat(date_value) + timedelta(days=1)).date().isoformat() + "T00:00:00Z"
        return [("gte", field, start), ("lte", field, end)]

    def _jakarta_today(self):
        return datetime.now(timezone(timedelta(hours=7))).date().isoformat()

    def _jakarta_date_filters(self, field, date_value):
        if not date_value:
            return []
        jakarta = timezone(timedelta(hours=7))
        start_local = datetime.fromisoformat(date_value).replace(tzinfo=jakarta)
        end_local = start_local + timedelta(days=1)
        return [
            ("gte", field, start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")),
            ("lte", field, end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")),
        ]

    def _fetch(self, table, select="*", order_by=None, desc=True, limit=None, filters=None):
        if not self.sb:
            return []
        try:
            table_columns = {
                "products": "id,product_code,sku_code,product_name,description,ph_min,ph_max,brix_min,brix_max,tds_min,tds_max,is_active,created_at,updated_at",
                "production_batches": "id,product_id,product_name,batch_code,batch_sequence,production_date,expired_date,status,created_by,cook_name,quantity,production_shift,ph_value,brix_value,tds_value,ph_status,brix_status,tds_status,parameter_notes,parameter_checked_by,parameter_checked_at,shift,operator_id,qc_officer_id,photo_url,storage_path,created_at,updated_at,final_qc_status,report_url",
                "production_batch_logs": "id,batch_id,stage,operator_id,photo_url,stage_qc_status,metrics,recorded_at,storage_path,raw_temp_c,core_temp_c,ph_value_extracted,brix_value_extracted,tds_value,room_temp_c",
                "facility_rooms": "id,name,slug,description,is_active,created_at,updated_at",
                "facility_devices": "id,room_id,name,slug,device_type,type,target_temperature,threshold_temp,min_temperature,max_temperature,is_default,is_active,created_at,updated_at",
                "facility_logs": "id,room_id,device_id,temperature_c,recorded_at,is_normal,notes,storage_path,photo_url,monitoring_date,slot_time,status,submitted_by,submitted_at,is_late,schedule_status,created_at",
                "temperature_logs": "id,room_id,device_id,temperature,status,notes,submitted_by,submitted_at,is_late,schedule_status,temperature_c,is_normal,recorded_at,storage_path,photo_url,created_at",
                "facility_alerts": "id,zone,temperature_c,threshold_c,deviation_c,status,log_id,device_id,created_at,resolved_at,notes,resolved_by",
                "qc_reports": "id,batch_id,batch_code,status,final_qc_status,qc_stage,ccp_stage,started_at,created_at,completed_at,updated_at,photo_url,product_photo_url,cooking_photo_url,barcode_photo_url,temperature_photo_url,notes,inspection_round,parent_inspection,is_active,product_name,staff_id,staff_name,inspector_name,temperature",
                "qc_findings": "id,batch_id,reason,status,staff_name,created_at,staff_id,storage_path,photo_url,updated_at,category,notes,approval_status,product_name,inspector_name",
                "approvals": "id,qc_report_id,status,reason,approved_by,approved_at,created_at,updated_at",
                "barcode_labels": "id,batch_id,barcode_value,created_at,created_by,is_active",
                "staff_accounts": "id,user_id,role,username,is_active,created_at,updated_at",
                "profiles": "id,full_name,display_name,email,role,created_at,updated_at",
                "users": "id,email,full_name,display_name,role,created_at,updated_at",
                "learning_modules": "id,slug,title,description,content,published,best_actions,created_at,updated_at",
                "itdv_progress": "id,user_id,module_slug,status,quiz_score,quiz_passed,simulation_score,simulation_passed,completed_at,updated_at,created_at",
                "itdv_attempts": "id,user_id,module_slug,score,passed,created_at",
                "itdv_certificates": "id,user_id,program_code,certificate_number,issued_at,created_at",
            }

            if select == "*":
                select = table_columns.get(table, "*")
            else:
                if "products(*)" in select:
                    select = select.replace("products(*)", "products(id,product_code,sku_code,product_name)")
                if "facility_rooms(*)" in select:
                    select = select.replace("facility_rooms(*)", "facility_rooms(id,name,slug,description,is_active)")
                if "facility_devices(*)" in select:
                    select = select.replace(
                        "facility_devices(*)", "facility_devices(id,room_id,name,slug,device_type,type)"
                    )
                if select.startswith("*,"):
                    cols = table_columns.get(table, "*")
                    select = select.replace("*,", cols + ",")
                elif select.endswith(",*"):
                    cols = table_columns.get(table, "*")
                    select = select.replace(",*", "," + cols)
                elif ",*," in select:
                    cols = table_columns.get(table, "*")
                    select = select.replace(",*,", "," + cols + ",")

            query = self.sb.table(table).select(select)
            for op, field, value in filters or []:
                query = getattr(query, op)(field, value)
            if order_by:
                query = query.order(order_by, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Query failed for %s: %s", table, exc)
            return []

    def normalize_evidence_url(self, record):
        url = (
            record.get("public_url")
            or record.get("signed_url")
            or record.get("photo_url")
            or record.get("product_photo_url")
            or record.get("temperature_photo_url")
            or record.get("barcode_photo_url")
        )
        storage_path = (
            record.get("storage_path")
            or record.get("product_storage_path")
            or record.get("temperature_storage_path")
            or record.get("barcode_storage_path")
        )
        if not url and storage_path:
            url = self._signed_storage_url(
                storage_path, record.get("bucket") or "qc-evidence"
            ) or self._public_storage_url(storage_path, record.get("bucket") or "qc-evidence")
        record["photo_url"] = url
        record["storage_path"] = storage_path
        record["has_photo"] = bool(url)
        return record

    def _signed_storage_url(self, storage_path, bucket="qc-evidence"):
        first_path = str(storage_path or "").split(";")[0].strip()
        if not first_path or first_path.startswith(("http://", "https://")):
            return first_path or None
        try:
            storage = getattr(self.sb, "storage", None)
            if not storage or not hasattr(storage, "from_"):
                return None
            result = storage.from_(bucket).create_signed_url(first_path.lstrip("/"), 3600)
            if isinstance(result, dict):
                return result.get("signedURL") or result.get("signed_url") or result.get("url")
            return (
                getattr(result, "signed_url", None)
                or getattr(result, "signedURL", None)
                or getattr(result, "url", None)
            )
        except Exception as exc:
            logger.warning("Signed evidence URL generation skipped: %s", exc)
            return None

    def _public_storage_url(self, storage_path, bucket="qc-evidence"):
        first_path = str(storage_path or "").split(";")[0].strip()
        if not first_path:
            return None
        if first_path.startswith("http://") or first_path.startswith("https://"):
            return first_path
        base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}/storage/v1/object/public/{bucket}/{first_path.lstrip('/')}"

    def _fetch_daily_candidates(self, table, date, limit, timestamp_fields, date_fields=(), order_by=None):
        merged = []
        seen = set()
        for field in timestamp_fields:
            for row in self._fetch(
                table, order_by=order_by or field, limit=limit, filters=self._jakarta_date_filters(field, date)
            ):
                key = row.get("id") or (table, field, len(merged), str(row))
                if key not in seen:
                    seen.add(key)
                    merged.append(row)
        for field in date_fields:
            for row in self._fetch(table, order_by=order_by, limit=limit, filters=[("eq", field, date)]):
                key = row.get("id") or (table, field, len(merged), str(row))
                if key not in seen:
                    seen.add(key)
                    merged.append(row)
        if not merged:
            rows = self._fetch(table, order_by=order_by, limit=limit)
            merged = [row for row in rows if self._row_matches_date(row, date)]
        return merged[:limit]

    def _row_matches_date(self, row, date):
        for field in ("monitoring_date", "inspection_date", "finding_date", "production_date"):
            if str(row.get(field) or "")[:10] == date:
                return True
        for field in ("recorded_at", "submitted_at", "completed_at", "created_at", "updated_at"):
            if self._row_jakarta_date(row.get(field)) == date:
                return True
        return False

    def _row_jakarta_date(self, value):
        if not value:
            return ""
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed.astimezone(timezone(timedelta(hours=7))).date().isoformat()
        except Exception:
            return text[:10]
