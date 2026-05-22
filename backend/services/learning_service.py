from __future__ import annotations

import logging
import base64
from datetime import datetime, timezone
from uuid import uuid4

from backend.repositories.learning_repository import LearningRepository

logger = logging.getLogger("qc.services.learning")


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
LOCAL_MENTOR_HISTORY = []


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
            self._log_persistence_fallback("learning progress", user_id)
            LOCAL_PROGRESS.setdefault(user_id, set()).add(module_slug)
        return self.progress(user_id)

    def progress(self, user_id):
        modules = self._modules()
        completed = set(self._progress_map(user_id))
        learning_percent = self._percent(len(completed), len(modules))
        simulation_percent = self._attempt_percent(
            user_id,
            "itdv_simulation_attempts",
            "simulation_id",
            [item.get("id") for item in self._simulations()],
            LOCAL_SIMULATION_ATTEMPTS,
        )
        quiz_percent = self._attempt_percent(
            user_id,
            "itdv_quiz_attempts",
            "quiz_id",
            [item.get("id") for item in self._quizzes()],
            LOCAL_QUIZ_ATTEMPTS,
        )
        certificate_percent = 100 if self._has_certificate(user_id) else 0
        return self._ok({
            "completed_modules": len(completed),
            "total_modules": len(modules),
            "percent": learning_percent,
            "learning_percent": learning_percent,
            "simulation_percent": simulation_percent,
            "quiz_percent": quiz_percent,
            "certificate_percent": certificate_percent,
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
        feedback = self._simulation_feedback(simulation, action)
        payload = {
            "user_id": user_id,
            "simulation_id": simulation_id,
            "selected_action": selected_action,
            "score": score,
            "feedback": feedback,
        }
        saved = self.repo.insert_attempt("itdv_simulation_attempts", payload) if self.repo.available() else None
        if not saved:
            self._log_persistence_fallback("simulation attempt", user_id)
            LOCAL_SIMULATION_ATTEMPTS.append(payload)
        return self._ok({
            "simulation_id": simulation_id,
            "selected_action": selected_action,
            "score": score,
            "passed": score >= 70,
            "feedback": feedback,
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
            self._log_persistence_fallback("quiz attempt", user_id)
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
        if not self._certificate_unlocked(progress):
            return self._fail(
                "Selesaikan 100% modul, quiz, dan simulation sebelum generate sertifikat",
                409,
                {"progress": progress},
            )
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
            self._log_persistence_fallback("certificate", user["id"])
            LOCAL_CERTIFICATES[(user["id"], "ITDV-QC-FOOD")] = payload
        certificate_data = {
            **payload,
            "program_name": "Simulasi Quality Control Industri Pangan",
            "issued_at": _now(),
        }
        certificate_data["pdf_filename"] = f"{cert_id}.pdf"
        certificate_data["pdf_base64"] = base64.b64encode(self._simple_certificate_pdf(certificate_data)).decode("ascii")
        return self._ok(certificate_data)

    def certificate_pdf(self, user):
        result = self.certificate(user)
        if not result.get("success"):
            return result
        data = result["data"]
        pdf = self._simple_certificate_pdf(data)
        return self._ok({
            "filename": f"{data['certificate_id']}.pdf",
            "content_type": "application/pdf",
            "bytes": pdf,
        })

    def career_recommendation(self, user_id):
        progress = self.progress(user_id)["data"]
        modules = set(progress.get("module_slugs") or [])
        simulation_score = self._best_attempt_score(user_id, "itdv_simulation_attempts", LOCAL_SIMULATION_ATTEMPTS)
        quiz_score = self._best_attempt_score(user_id, "itdv_quiz_attempts", LOCAL_QUIZ_ATTEMPTS)
        learning_score = int(progress.get("learning_percent") or 0)

        def has(*slugs):
            return all(slug in modules for slug in slugs)

        recommendations = [
            self._career("QC", self._average(learning_score, simulation_score, quiz_score), [
                "Cocok untuk inspeksi proses, sampling, monitoring suhu, dan keputusan pass/fail.",
                "Skor simulation dan quiz menunjukkan kesiapan membaca kasus operasional QC.",
            ]),
            self._career("QA", self._average(learning_score, quiz_score, 85 if has("haccp") else 45), [
                "Cocok untuk dokumentasi mutu, verifikasi SOP, CAPA, dan kontrol sistem kualitas.",
                "Progress modul dan pemahaman quiz menjadi indikator kesiapan QA.",
            ]),
            self._career("Food Safety", self._average(quiz_score, 90 if has("haccp", "food-safety") else 45, simulation_score), [
                "Cocok untuk HACCP, hygiene, pencegahan kontaminasi, dan food safety compliance.",
                "Materi HACCP/Food Safety dan skor kasus suhu menjadi dasar rekomendasi.",
            ]),
            self._career("Auditor", self._average(learning_score, quiz_score, 90 if has("haccp", "traceability") else 40), [
                "Cocok untuk audit internal, audit trail, traceability, dan pemeriksaan evidence.",
                "Kesiapan auditor meningkat saat modul traceability dan HACCP selesai.",
            ]),
            self._career("Supply Chain", self._average(simulation_score, 90 if has("traceability") else 45, learning_score), [
                "Cocok untuk alur batch, cold chain, traceability, dan koordinasi risiko produk.",
                "Pemahaman traceability dan keputusan pada kasus suhu mendukung jalur ini.",
            ]),
        ]
        recommendations.sort(key=lambda item: item["match_percent"], reverse=True)
        return self._ok({
            "primary": recommendations[0],
            "recommendations": recommendations,
            "scores": {
                "learning": learning_score,
                "simulation": simulation_score,
                "quiz": quiz_score,
            },
        })

    def mentor_answer(self, user_id, question):
        question = str(question or "").strip()
        if len(question) < 3:
            return self._fail("Pertanyaan mentor terlalu pendek", 400)
        answer_data = self._mentor_rule(question)
        payload = {
            "user_id": user_id,
            "question": question[:1000],
            "answer": answer_data["answer"],
            "topics": answer_data["topics"],
        }
        saved = self.repo.insert_attempt("itdv_mentor_history", payload) if self.repo.available() else None
        if not saved:
            self._log_persistence_fallback("mentor history", user_id)
            LOCAL_MENTOR_HISTORY.append({**payload, "created_at": _now()})
        return self._ok(payload)

    def mentor_history(self, user_id):
        rows = self.repo.fetch_table(
            "itdv_mentor_history",
            filters=[("eq", "user_id", user_id)],
            order_by="created_at",
            desc=True,
            limit=20,
        ) if self.repo.available() else []
        if not rows:
            rows = [
                row for row in reversed(LOCAL_MENTOR_HISTORY)
                if row.get("user_id") == user_id
            ][:20]
        return self._ok(rows)

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
            "itdv_progress",
            filters=[("eq", "user_id", user_id), ("eq", "status", "completed")],
        ) if self.repo.available() else []
        progress = {row.get("module_slug"): row for row in rows if row.get("module_slug")}
        for slug in LOCAL_PROGRESS.get(user_id, set()):
            progress.setdefault(slug, {"module_slug": slug, "status": "completed"})
        return progress

    def _attempt_percent(self, user_id, table, id_field, total_ids, local_rows):
        expected = {item for item in total_ids if item}
        if not expected:
            return 0
        rows = self.repo.fetch_table(
            table,
            filters=[("eq", "user_id", user_id), ("gte", "score", 70)],
        ) if self.repo.available() else []
        passed = {row.get(id_field) for row in rows if row.get(id_field) in expected}
        for row in local_rows:
            if row.get("user_id") == user_id and int(row.get("score") or 0) >= 70 and row.get(id_field) in expected:
                passed.add(row.get(id_field))
        return self._percent(len(passed), len(expected))

    def _has_certificate(self, user_id):
        rows = self.repo.fetch_table(
            "itdv_certificates",
            filters=[("eq", "user_id", user_id), ("eq", "program_code", "ITDV-QC-FOOD")],
            limit=1,
        ) if self.repo.available() else []
        return bool(rows or LOCAL_CERTIFICATES.get((user_id, "ITDV-QC-FOOD")))

    def _best_attempt_score(self, user_id, table, local_rows):
        rows = self.repo.fetch_table(
            table,
            filters=[("eq", "user_id", user_id)],
        ) if self.repo.available() else []
        scores = [int(row.get("score") or 0) for row in rows]
        scores.extend(int(row.get("score") or 0) for row in local_rows if row.get("user_id") == user_id)
        return max(scores or [0])

    def _module(self, slug):
        return next((item for item in self._modules() if item.get("slug") == slug), None)

    def _simulation(self, simulation_id):
        return next((item for item in self._simulations() if item.get("id") == simulation_id), None)

    def _quiz(self, quiz_id):
        return next((item for item in self._quizzes() if item.get("id") == quiz_id), None)

    def _percent(self, completed, total):
        return round((completed / total) * 100) if total else 0

    def _average(self, *values):
        return round(sum(int(value or 0) for value in values) / len(values)) if values else 0

    def _career(self, title, match_percent, reasons):
        return {
            "title": title,
            "match_percent": max(0, min(100, int(match_percent or 0))),
            "reasons": reasons,
        }

    def _mentor_rule(self, question):
        normalized = question.lower()
        if "11" in normalized and ("suhu" in normalized or "°c" in normalized or "c" in normalized):
            return {
                "topics": ["Food safety", "HACCP", "Corrective action"],
                "answer": (
                    "Suhu 11°C berbahaya karena berada di atas batas aman chiller 5°C. "
                    "Dari sisi food safety, suhu ini meningkatkan risiko pertumbuhan mikroba pada bahan atau produk pangan. "
                    "Dalam HACCP, deviasi suhu harus dianggap sebagai penyimpangan pada titik kontrol yang perlu dimonitor dan dicatat. "
                    "Corrective action yang tepat adalah hold product, investigasi durasi deviasi, cek pintu/sensor/chiller, pindahkan produk ke chiller aman, "
                    "lalu hanya lanjutkan proses setelah risiko produk dinilai terkendali."
                ),
            }
        return {
            "topics": ["Food safety", "HACCP", "Corrective action"],
            "answer": (
                "Dalam konteks QC pangan, evaluasi pertanyaan ini dengan tiga langkah: food safety untuk menilai risiko keamanan produk, "
                "HACCP untuk menentukan apakah ada deviasi pada titik kontrol, dan corrective action untuk memastikan produk ditahan, "
                "penyebab diselidiki, serta keputusan lanjut produksi dibuat berdasarkan bukti."
            ),
        }

    def _certificate_unlocked(self, progress):
        return all(int(progress.get(key) or 0) >= 100 for key in (
            "learning_percent",
            "simulation_percent",
            "quiz_percent",
        ))

    def _simulation_feedback(self, simulation, action):
        target = simulation.get("target_c")
        actual = simulation.get("actual_c")
        label = action.get("label", "Tindakan")
        if action.get("score", 0) >= 70:
            return (
                f"Jawaban benar: {label}. Dalam HACCP, suhu penyimpanan adalah titik kontrol yang harus dimonitor. "
                f"Suhu {actual}°C melebihi batas aman {target}°C, sehingga produk perlu ditahan, deviasi dicatat, "
                "dan corrective action dilakukan sebelum produksi dilanjutkan."
            )
        return (
            f"Jawaban salah: {label}. Suhu {actual}°C melebihi batas aman {target}°C. "
            "Risiko mikroba meningkat jika produksi tetap dilanjutkan. "
            "Perlu investigasi, hold product, dan corrective action sebelum produk digunakan."
        )

    def _ok(self, data, message="OK"):
        return {"success": True, "data": data, "message": message}

    def _fail(self, message, status=400, extra=None):
        return {"success": False, "message": message, "status": status, **(extra or {})}

    def _simple_certificate_pdf(self, data):
        lines = [
            "QC LearnHub AI",
            "Certificate of Completion",
            f"Participant: {data.get('participant_name') or 'Peserta'}",
            f"Program: {data.get('program_name') or 'Simulasi Quality Control Industri Pangan'}",
            f"Certificate ID: {data.get('certificate_id')}",
            f"Issued At: {str(data.get('issued_at') or '')[:10]}",
            "This certificate confirms completion of learning modules, simulation, and quiz.",
        ]
        text = ["BT", "/F1 26 Tf", "72 760 Td", f"({self._pdf_escape(lines[0])}) Tj"]
        text.extend(["/F1 18 Tf", "0 -44 Td", f"({self._pdf_escape(lines[1])}) Tj"])
        text.extend(["/F1 12 Tf"])
        for line in lines[2:]:
            text.extend(["0 -28 Td", f"({self._pdf_escape(line)}) Tj"])
        text.append("ET")
        stream = "\n".join(text).encode("latin-1", "replace")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{index} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")
        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return bytes(pdf)

    def _pdf_escape(self, value):
        return str(value or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _log_persistence_fallback(self, entity, user_id):
        if self.repo.available():
            logger.error("Failed to persist ITDV %s for user %s; using local fallback", entity, user_id)
        else:
            logger.warning("Supabase unavailable for ITDV %s user %s; using local fallback", entity, user_id)


def _now():
    return datetime.now(timezone.utc).isoformat()
