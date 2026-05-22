from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.repositories.learning_repository import LearningRepository


MODULES = [
    {
        "slug": "haccp",
        "title": "HACCP",
        "category": "Food Safety",
        "duration_minutes": 45,
        "summary": "Identifikasi bahaya, CCP, critical limit, monitoring, corrective action, dan verifikasi.",
        "objectives": ["Mengenali bahaya pangan", "Menentukan CCP", "Membuat tindakan korektif"],
    },
    {
        "slug": "food-safety",
        "title": "Food Safety",
        "category": "Sanitasi",
        "duration_minutes": 35,
        "summary": "Prinsip keamanan pangan, personal hygiene, kontaminasi silang, dan alur sanitasi area produksi.",
        "objectives": ["Mencegah kontaminasi", "Memahami hygiene", "Menilai risiko area"],
    },
    {
        "slug": "qc-dasar",
        "title": "QC Dasar",
        "category": "Quality Control",
        "duration_minutes": 30,
        "summary": "Parameter mutu dasar, sampling, inspeksi visual, evidence, dan keputusan pass/warning/fail.",
        "objectives": ["Membaca parameter QC", "Melakukan sampling", "Mencatat evidence"],
    },
    {
        "slug": "traceability",
        "title": "Traceability",
        "category": "Batch",
        "duration_minutes": 40,
        "summary": "Pelacakan batch dari bahan baku, proses, penyimpanan, distribusi, sampai audit trail.",
        "objectives": ["Melacak batch", "Menganalisis audit trail", "Menyiapkan recall simulation"],
    },
    {
        "slug": "monitoring-suhu",
        "title": "Monitoring Suhu",
        "category": "Cold Chain",
        "duration_minutes": 25,
        "summary": "Pemantauan suhu chiller/freezer, batas kritis, alert, investigasi, dan eskalasi.",
        "objectives": ["Membaca deviasi suhu", "Memilih aksi korektif", "Menyimpan log monitoring"],
    },
]

SIMULATIONS = [
    {
        "id": "ppic-chiller-001",
        "title": "PPIC Chiller Temperature Deviation",
        "area": "PPIC Chiller",
        "target_c": 5,
        "actual_c": 11,
        "scenario": "Saat monitoring pagi, suhu aktual PPIC Chiller berada di atas target. Produk masih menunggu rilis produksi.",
        "options": [
            {"key": "A", "label": "Investigasi", "score": 70, "feedback": "Benar sebagai langkah awal: cek durasi deviasi, sensor, pintu, dan kondisi produk."},
            {"key": "B", "label": "Corrective Action", "score": 100, "feedback": "Paling tepat jika disertai hold product, pindah chiller cadangan, dan eskalasi maintenance."},
            {"key": "C", "label": "Lanjut produksi", "score": 0, "feedback": "Tidak aman. Deviasi suhu harus dikendalikan sebelum produksi dilanjutkan."},
        ],
        "best_actions": ["A", "B"],
    }
]

QUIZZES = [
    {
        "id": "qc-basic-quiz",
        "title": "Quiz QC Dasar",
        "module_slug": "qc-dasar",
        "questions": [
            {
                "id": "q1",
                "text": "Apa tindakan pertama saat suhu chiller melewati critical limit?",
                "options": [
                    {"key": "A", "label": "Catat saja di akhir shift"},
                    {"key": "B", "label": "Investigasi dan tahan produk terdampak"},
                    {"key": "C", "label": "Naikkan target suhu"},
                    {"key": "D", "label": "Lanjut produksi jika produk terlihat normal"},
                ],
                "answer": "B",
            },
            {
                "id": "q2",
                "text": "Traceability batch berguna terutama untuk apa?",
                "options": [
                    {"key": "A", "label": "Menentukan jalur recall dan audit produk"},
                    {"key": "B", "label": "Menghapus kebutuhan QC"},
                    {"key": "C", "label": "Mengubah resep produksi"},
                    {"key": "D", "label": "Mengganti approval supervisor"},
                ],
                "answer": "A",
            },
            {
                "id": "q3",
                "text": "Dalam HACCP, CCP berarti titik proses yang harus dikendalikan karena...",
                "options": [
                    {"key": "A", "label": "Selalu paling mahal"},
                    {"key": "B", "label": "Berhubungan dengan bahaya keamanan pangan signifikan"},
                    {"key": "C", "label": "Hanya untuk dokumen admin"},
                    {"key": "D", "label": "Tidak perlu monitoring"},
                ],
                "answer": "B",
            },
        ],
    }
]

LOCAL_PROGRESS = {}
LOCAL_SIMULATION_ATTEMPTS = []
LOCAL_QUIZ_ATTEMPTS = []
LOCAL_CERTIFICATES = {}


class LearningService:
    def __init__(self, repository=None):
        self.repo = repository or LearningRepository()

    def modules(self, user_id):
        progress = self._progress_map(user_id)
        return self._ok([
            {**module, "completed": progress.get(module["slug"], {}).get("status") == "completed"}
            for module in self._modules()
        ])

    def complete_module(self, user_id, module_slug):
        module = self._module(module_slug)
        if not module:
            return self._fail("Modul tidak ditemukan", 404)
        payload = {
            "user_id": user_id,
            "module_slug": module_slug,
            "status": "completed",
            "completed_at": _now(),
        }
        saved = self.repo.upsert_progress(payload) if self.repo.available() else None
        if not saved:
            LOCAL_PROGRESS.setdefault(user_id, set()).add(module_slug)
        return self.progress(user_id)

    def progress(self, user_id):
        modules = self._modules()
        completed = set(self._progress_map(user_id))
        percent = round((len(completed) / len(modules)) * 100) if modules else 0
        return self._ok({
            "completed_modules": len(completed),
            "total_modules": len(modules),
            "percent": percent,
            "module_slugs": sorted(completed),
        })

    def simulations(self):
        return self._ok(self._simulations())

    def submit_simulation(self, user_id, simulation_id, selected_action):
        simulation = self._simulation(simulation_id)
        if not simulation:
            return self._fail("Simulasi tidak ditemukan", 404)
        action = next((item for item in simulation["options"] if item["key"] == selected_action), None)
        if not action:
            return self._fail("Pilihan tindakan tidak valid", 400)
        score = action["score"]
        payload = {
            "user_id": user_id,
            "simulation_id": simulation_id,
            "selected_action": selected_action,
            "score": score,
            "feedback": action["feedback"],
        }
        saved = self.repo.insert_attempt("itdv_simulation_attempts", payload) if self.repo.available() else None
        if not saved:
            LOCAL_SIMULATION_ATTEMPTS.append(payload)
        return self._ok({
            "simulation_id": simulation_id,
            "selected_action": selected_action,
            "score": score,
            "passed": score >= 70,
            "feedback": action["feedback"],
            "best_actions": simulation["best_actions"],
        })

    def quizzes(self):
        public_quizzes = []
        for quiz in self._quizzes():
            public_quizzes.append({
                **quiz,
                "questions": [
                    {key: value for key, value in question.items() if key != "answer"}
                    for question in quiz["questions"]
                ],
            })
        return self._ok(public_quizzes)

    def submit_quiz(self, user_id, quiz_id, answers):
        quiz = self._quiz(quiz_id)
        if not quiz:
            return self._fail("Quiz tidak ditemukan", 404)
        answers = answers or {}
        items = []
        correct = 0
        for question in quiz["questions"]:
            selected = answers.get(question["id"])
            is_correct = selected == question["answer"]
            correct += 1 if is_correct else 0
            items.append({
                "question_id": question["id"],
                "selected": selected,
                "correct_answer": question["answer"],
                "is_correct": is_correct,
            })
        score = round((correct / len(quiz["questions"])) * 100) if quiz["questions"] else 0
        payload = {
            "user_id": user_id,
            "quiz_id": quiz_id,
            "score": score,
            "answers": answers,
        }
        saved = self.repo.insert_attempt("itdv_quiz_attempts", payload) if self.repo.available() else None
        if not saved:
            LOCAL_QUIZ_ATTEMPTS.append(payload)
        return self._ok({
            "quiz_id": quiz_id,
            "score": score,
            "correct": correct,
            "total": len(quiz["questions"]),
            "passed": score >= 70,
            "items": items,
        })

    def certificate(self, user):
        progress = self.progress(user["id"])["data"]
        if progress["percent"] < 100:
            return self._fail("Selesaikan semua modul sebelum generate sertifikat", 409, {"progress": progress})
        cert_id = f"ITDV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
        name = user.get("name") or user.get("username") or "Peserta"
        payload = {
            "certificate_id": cert_id,
            "user_id": user["id"],
            "program_code": "ITDV-QC-FOOD",
            "participant_name": name,
        }
        saved = self.repo.upsert_certificate(payload) if self.repo.available() else None
        if not saved:
            LOCAL_CERTIFICATES[(user["id"], "ITDV-QC-FOOD")] = payload
        return self._ok({
            **payload,
            "program_name": "Simulasi Quality Control Industri Pangan",
            "issued_at": _now(),
        })

    def _modules(self):
        rows = self.repo.fetch_table("itdv_modules", order_by="sort_order") if self.repo.available() else []
        return rows or MODULES

    def _simulations(self):
        rows = self.repo.fetch_table("itdv_simulations", order_by="created_at") if self.repo.available() else []
        return rows or SIMULATIONS

    def _quizzes(self):
        rows = self.repo.fetch_table("itdv_quizzes", order_by="created_at") if self.repo.available() else []
        return rows or QUIZZES

    def _progress_map(self, user_id):
        rows = self.repo.fetch_table(
            "itdv_learning_progress",
            filters=[("eq", "user_id", user_id), ("eq", "status", "completed")],
        ) if self.repo.available() else []
        progress = {row.get("module_slug"): row for row in rows if row.get("module_slug")}
        for slug in LOCAL_PROGRESS.get(user_id, set()):
            progress.setdefault(slug, {"module_slug": slug, "status": "completed"})
        return progress

    def _module(self, slug):
        return next((item for item in self._modules() if item.get("slug") == slug), None)

    def _simulation(self, simulation_id):
        return next((item for item in self._simulations() if item.get("id") == simulation_id), None)

    def _quiz(self, quiz_id):
        return next((item for item in self._quizzes() if item.get("id") == quiz_id), None)

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _fail(self, message, status=400, extra=None):
        return {"success": False, "message": message, "status": status, **(extra or {})}


def _now():
    return datetime.now(timezone.utc).isoformat()
