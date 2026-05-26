"""Admin CRUD service for ITDV Learning Center content."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from backend.database.supabase_client import get_client

logger = logging.getLogger("qc.services.admin_learning")

ANSWERS = {"A", "B", "C", "D"}
DUPLICATE_SLUG_MESSAGE = "Slug sudah digunakan. Gunakan slug lain."


class AdminLearningService:
    def __init__(self, sb_client=None):
        self.sb = sb_client or get_client()

    def list_modules(self):
        return self._ok(self._fetch("itdv_modules", order_by="sort_order"))

    def create_module(self, payload):
        data, error = self._module_payload(payload, partial=False)
        if error:
            return self._fail(error, 400)
        if self._exists("itdv_modules", "slug", data["slug"]):
            return self._fail(DUPLICATE_SLUG_MESSAGE, 409, "DUPLICATE_SLUG")
        return self._insert("itdv_modules", data)

    def update_module(self, module_id, payload):
        data, error = self._module_payload(payload, partial=True)
        if error:
            return self._fail(error, 400)
        current = self._one("itdv_modules", "slug", module_id)
        if not current:
            return self._fail("Module tidak ditemukan", 404, "MODULE_NOT_FOUND")
        if data.get("slug") and data["slug"] != module_id and self._exists("itdv_modules", "slug", data["slug"]):
            return self._fail(DUPLICATE_SLUG_MESSAGE, 409, "DUPLICATE_SLUG")
        return self._update("itdv_modules", "slug", module_id, data)

    def delete_module(self, module_id):
        # Soft delete keeps user progress and historical certificates intact.
        return self._update("itdv_modules", "slug", module_id, {"published": False, "archived": True})

    def list_mini_quiz(self, module_id):
        rows = self._fetch("itdv_module_mini_quizzes", filters=[("eq", "module_slug", module_id)], order_by="created_at")
        return self._ok(rows)

    def create_mini_quiz(self, module_id, payload):
        data, error = self._question_payload(payload, partial=False, module_slug=module_id)
        if error:
            return self._fail(error, 400)
        return self._insert("itdv_module_mini_quizzes", data)

    def update_mini_quiz(self, quiz_id, payload):
        data, error = self._question_payload(payload, partial=True)
        if error:
            return self._fail(error, 400)
        return self._update("itdv_module_mini_quizzes", "id", quiz_id, data)

    def delete_mini_quiz(self, quiz_id):
        return self._update("itdv_module_mini_quizzes", "id", quiz_id, {"published": False, "archived": True})

    def list_simulations(self):
        return self._ok(self._fetch("itdv_simulations", order_by="created_at", desc=True))

    def create_simulation(self, payload):
        data, error = self._simulation_payload(payload, partial=False)
        if error:
            return self._fail(error, 400)
        data.setdefault("id", f"sim-{uuid4().hex[:10]}")
        return self._insert("itdv_simulations", data)

    def update_simulation(self, simulation_id, payload):
        data, error = self._simulation_payload(payload, partial=True)
        if error:
            return self._fail(error, 400)
        return self._update("itdv_simulations", "id", simulation_id, data)

    def delete_simulation(self, simulation_id):
        return self._update("itdv_simulations", "id", simulation_id, {"published": False, "archived": True})

    def list_quizzes(self):
        return self._ok(self._fetch("itdv_quiz_questions", order_by="created_at", desc=True))

    def create_quiz(self, payload):
        data, error = self._question_payload(payload, partial=False, related_module=True)
        if error:
            return self._fail(error, 400)
        return self._insert("itdv_quiz_questions", data)

    def update_quiz(self, quiz_id, payload):
        data, error = self._question_payload(payload, partial=True, related_module=True)
        if error:
            return self._fail(error, 400)
        return self._update("itdv_quiz_questions", "id", quiz_id, data)

    def delete_quiz(self, quiz_id):
        return self._update("itdv_quiz_questions", "id", quiz_id, {"published": False, "archived": True})

    def progress(self):
        progress = self._fetch("itdv_progress", order_by="updated_at", desc=True, limit=500)
        sim_attempts = self._fetch("itdv_simulation_attempts", order_by="created_at", desc=True, limit=500)
        quiz_attempts = self._fetch("itdv_quiz_attempts", order_by="created_at", desc=True, limit=500)
        certificates = self._fetch("itdv_certificates", order_by="issued_at", desc=True, limit=500)
        users = {}
        for row in progress:
            users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")})["learning_progress"] = row.get("status")
        for row in sim_attempts:
            users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")})["simulation_score"] = max(
                int(users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")}).get("simulation_score") or 0),
                int(row.get("score") or 0),
            )
        for row in quiz_attempts:
            users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")})["quiz_score"] = max(
                int(users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")}).get("quiz_score") or 0),
                int(row.get("score") or 0),
            )
        for row in certificates:
            item = users.setdefault(row.get("user_id"), {"user_id": row.get("user_id")})
            item["certificate_status"] = "issued"
            item["issued_at"] = row.get("issued_at")
            item["certificate_id"] = row.get("certificate_id")
        return self._ok(list(users.values()))

    def _module_payload(self, payload, partial):
        data = {}
        title = self._str(payload.get("title"))
        slug = self._slug(payload.get("slug") or title)
        if not partial and not title:
            return None, "Title wajib diisi"
        if title:
            data["title"] = title
        if slug:
            data["slug"] = slug
        if "description" in payload:
            data["description"] = self._str(payload.get("description"))
            data["summary"] = data["description"] or title
        elif not partial:
            data["description"] = self._str(payload.get("summary"))
            data["summary"] = data["description"] or title
        if "category" in payload:
            data["category"] = self._str(payload.get("category")) or "ITDV"
        elif not partial:
            data["category"] = "ITDV"
        for source, target in (("learning_material", "learning_material"), ("case_study", "case_study"), ("difficulty", "difficulty")):
            if source in payload:
                data[target] = self._str(payload.get(source))
        if "competencies" in payload:
            data["competencies"] = self._list(payload.get("competencies"))
            data["objectives"] = data["competencies"]
        elif not partial:
            data["competencies"] = []
            data["objectives"] = []
        if "estimated_time" in payload or "duration_minutes" in payload:
            value, error = self._int(payload.get("estimated_time", payload.get("duration_minutes")), "estimated_time")
            if error:
                return None, error
            data["estimated_time"] = value
            data["duration_minutes"] = value
        elif not partial:
            data["estimated_time"] = 0
            data["duration_minutes"] = 0
        if "order_number" in payload or "sort_order" in payload:
            value, error = self._int(payload.get("order_number", payload.get("sort_order")), "order_number")
            if error:
                return None, error
            data["order_number"] = value
            data["sort_order"] = value
        elif not partial:
            data["order_number"] = 0
            data["sort_order"] = 0
        if "status" in payload or "published" in payload:
            data["published"] = self._published(payload)
        elif not partial:
            data["published"] = True
        data["updated_at"] = _now()
        return data, None

    def _question_payload(self, payload, partial, module_slug=None, related_module=False):
        data = {}
        if module_slug:
            data["module_slug"] = module_slug
        elif "module_slug" in payload or "module_id" in payload:
            data["module_slug"] = self._str(payload.get("module_slug") or payload.get("module_id"))
        if related_module and ("related_module_slug" in payload or "module_slug" in payload):
            data["related_module_slug"] = self._str(payload.get("related_module_slug") or payload.get("module_slug"))
        for field in ("question", "option_a", "option_b", "option_c", "option_d", "explanation"):
            if field in payload:
                data[field] = self._str(payload.get(field))
        if not partial:
            if not data.get("question"):
                return None, "Question wajib diisi"
            if not all(data.get(field) for field in ("option_a", "option_b", "option_c", "option_d")):
                return None, "Minimal 4 opsi wajib diisi"
        if "correct_answer" in payload:
            answer = self._str(payload.get("correct_answer")).upper()
            if answer not in ANSWERS:
                return None, "Correct answer harus A/B/C/D"
            data["correct_answer"] = answer
        elif not partial:
            return None, "Correct answer harus A/B/C/D"
        if "published" in payload or "status" in payload:
            data["published"] = self._published(payload)
        data["updated_at"] = _now()
        return data, None

    def _simulation_payload(self, payload, partial):
        data = {}
        title = self._str(payload.get("title"))
        scenario = self._str(payload.get("scenario"))
        if not partial and not title:
            return None, "Title wajib diisi"
        if not partial and not scenario:
            return None, "Scenario wajib diisi"
        for field in ("title", "scenario", "risk", "ideal_action", "haccp_reason", "corrective_action", "documentation_required"):
            if field in payload:
                data[field] = self._str(payload.get(field))
        if "area" in payload:
            data["area"] = self._str(payload.get("area")) or "ITDV Simulation"
        elif not partial:
            data["area"] = "ITDV Simulation"
        if "target_temp" in payload or "target_c" in payload:
            data["target_c"] = self._float(payload.get("target_temp", payload.get("target_c")))
        if "actual_temp" in payload or "actual_c" in payload:
            data["actual_c"] = self._float(payload.get("actual_temp", payload.get("actual_c")))
        options = []
        for key in ("A", "B", "C"):
            value = self._str(payload.get(f"option_{key.lower()}"))
            if value:
                options.append({"key": key, "label": value, "score": 100 if self._str(payload.get("correct_answer")).upper() == key else 0})
        if options:
            data["options"] = options
        elif not partial:
            return None, "Minimal opsi A, B, C wajib diisi"
        if "correct_answer" in payload:
            answer = self._str(payload.get("correct_answer")).upper()
            if answer not in {"A", "B", "C"}:
                return None, "Correct answer harus A/B/C"
            data["best_actions"] = [answer]
        elif not partial:
            return None, "Correct answer harus A/B/C"
        if "published" in payload or "status" in payload:
            data["published"] = self._published(payload)
        elif not partial:
            data["published"] = True
        data["updated_at"] = _now()
        return data, None

    def _fetch(self, table, filters=None, order_by=None, desc=False, limit=None):
        if not self.sb:
            return []
        query = self.sb.table(table).select("*")
        for method, field, value in filters or []:
            query = getattr(query, method)(field, value)
        if order_by:
            query = query.order(order_by, desc=desc)
        if limit:
            query = query.limit(limit)
        return query.execute().data or []

    def _one(self, table, field, value):
        rows = self._fetch(table, filters=[("eq", field, value)], limit=1)
        return rows[0] if rows else None

    def _exists(self, table, field, value):
        return bool(self._one(table, field, value))

    def _insert(self, table, payload):
        try:
            rows = self.sb.table(table).insert(payload).execute().data or []
            return self._ok(rows[0] if rows else payload, "Created", 201)
        except Exception as exc:
            if self._duplicate(exc):
                return self._fail(DUPLICATE_SLUG_MESSAGE, 409, "DUPLICATE_SLUG")
            logger.warning("Admin learning insert failed for %s: %s", table, exc)
            return self._fail("Gagal menyimpan data learning", 500)

    def _update(self, table, field, value, payload):
        if not payload:
            return self._fail("Tidak ada data untuk disimpan", 400)
        try:
            rows = self.sb.table(table).update(payload).eq(field, value).execute().data or []
            return self._ok(rows[0] if rows else {field: value, **payload}, "Updated")
        except Exception as exc:
            if self._duplicate(exc):
                return self._fail(DUPLICATE_SLUG_MESSAGE, 409, "DUPLICATE_SLUG")
            logger.warning("Admin learning update failed for %s: %s", table, exc)
            return self._fail("Gagal mengubah data learning", 500)

    def _str(self, value):
        return str(value or "").strip()

    def _slug(self, value):
        raw = self._str(value).lower()
        return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")

    def _int(self, value, field):
        try:
            return int(value or 0), None
        except (TypeError, ValueError):
            return None, f"{field} harus angka"

    def _float(self, value):
        if value in (None, ""):
            return None
        return float(value)

    def _list(self, value):
        if isinstance(value, list):
            return [self._str(item) for item in value if self._str(item)]
        return [item.strip() for item in self._str(value).splitlines() if item.strip()]

    def _published(self, payload):
        if "published" in payload:
            value = payload.get("published")
            return value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "published"}
        return self._str(payload.get("status")).lower() in {"published", "active", "true", "1"}

    def _duplicate(self, exc):
        text = str(exc).lower()
        return "23505" in text or "duplicate" in text or "unique" in text

    def _ok(self, data, message="OK", status=200):
        return {"success": True, "data": data, "message": message, "status": status}

    def _fail(self, message, status=400, error_code="VALIDATION_ERROR"):
        return {"success": False, "message": message, "error_code": error_code, "status": status}


def _now():
    return datetime.now(timezone.utc).isoformat()
