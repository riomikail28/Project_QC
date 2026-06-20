from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from uuid import uuid4

from backend.repositories.learning_repository import LearningRepository

logger = logging.getLogger("qc.services.learning")


MODULES = [
    {
        "slug": "food-safety-hygiene",
        "title": "Dasar Food Safety dan Hygiene",
        "category": "Food Safety",
        "duration_minutes": 25,
        "summary": "Fondasi keamanan pangan, hygiene area, dan pencegahan kontaminasi pada central kitchen.",
        "objectives": ["Memahami risiko food safety", "Mengenali sumber kontaminasi", "Menjaga hygiene area kerja"],
        "learning_material": "Food safety berfokus pada pengendalian bahaya yang dapat membuat produk tidak aman dikonsumsi. Staff QC perlu membaca kondisi area, hygiene pekerja, alur bahan, suhu, dan kebersihan alat sebelum produk dilepas.",
        "case_study": "Area preparation menerima bahan dingin dengan kemasan basah. Staff QC menilai kebersihan kemasan, suhu penerimaan, dan risiko kontaminasi silang sebelum bahan masuk proses.",
        "competencies": [
            "Menilai risiko keamanan pangan dasar",
            "Mencatat temuan hygiene",
            "Menentukan tindakan pencegahan awal",
        ],
    },
    {
        "slug": "gmp-personal-hygiene",
        "title": "GMP dan Personal Hygiene",
        "category": "GMP",
        "duration_minutes": 25,
        "summary": "Praktik GMP, kebersihan personel, sanitasi alat, dan disiplin area produksi.",
        "objectives": ["Memahami GMP", "Mengecek personal hygiene", "Mencegah kontaminasi silang"],
        "learning_material": "GMP mengatur praktik produksi yang konsisten dan higienis. Pemeriksaan meliputi APD, cuci tangan, kondisi alat, pemisahan area bersih/kotor, dan perilaku pekerja di area produksi.",
        "case_study": "Operator masuk area packing tanpa hairnet lengkap. QC perlu melakukan hold sementara pada proses, koreksi APD, dan mencatat temuan hygiene.",
        "competencies": [
            "Melakukan checklist GMP",
            "Mengidentifikasi pelanggaran hygiene",
            "Memberi rekomendasi perbaikan area",
        ],
    },
    {
        "slug": "haccp-principles",
        "title": "Prinsip HACCP",
        "category": "HACCP",
        "duration_minutes": 35,
        "summary": "Prinsip HACCP mulai dari analisis bahaya, CCP, critical limit, monitoring, corrective action, verification, dan dokumentasi.",
        "objectives": ["Memahami alur HACCP", "Menghubungkan bahaya dengan CCP", "Membaca dokumen monitoring"],
        "learning_material": "HACCP adalah pendekatan sistematis untuk mengidentifikasi, mengevaluasi, dan mengendalikan bahaya signifikan dalam proses pangan. Di central kitchen, HACCP membantu QC membuat keputusan berbasis risiko.",
        "case_study": "Suhu chiller naik ke 11°C saat produk menunggu rilis. QC menentukan apakah titik tersebut termasuk kontrol kritis dan bagaimana produk ditahan.",
        "competencies": [
            "Menjelaskan prinsip HACCP",
            "Membaca alur proses",
            "Menghubungkan deviasi dengan risiko produk",
        ],
    },
    {
        "slug": "hazard-identification",
        "title": "Identifikasi Bahaya Pangan",
        "category": "HACCP",
        "duration_minutes": 35,
        "summary": "Identifikasi bahaya biologis, kimia, fisik, dan alergen pada proses central kitchen.",
        "objectives": ["Mengenali bahaya biologis", "Mengenali bahaya kimia/fisik", "Mengenali risiko alergen"],
        "learning_material": "Bahaya biologis mencakup mikroba, kimia mencakup residu bahan pembersih, fisik mencakup serpihan benda asing, dan alergen mencakup kontaminasi silang bahan pemicu alergi.",
        "case_study": "Produk seafood diproses dekat menu non-seafood. QC menilai risiko alergen, alat yang dipakai, dan label pemisahan bahan.",
        "competencies": [
            "Mengklasifikasi bahaya pangan",
            "Menentukan sumber risiko",
            "Menulis temuan bahaya dalam checklist",
        ],
    },
    {
        "slug": "ccp-determination",
        "title": "Penentuan CCP",
        "category": "HACCP",
        "duration_minutes": 30,
        "summary": "Cara menentukan titik kendali kritis berdasarkan risiko dan kemampuan proses mengendalikan bahaya.",
        "objectives": ["Memahami konsep CCP", "Membedakan CP dan CCP", "Menentukan titik kendali proses"],
        "learning_material": "CCP adalah titik proses yang wajib dikendalikan untuk mencegah, menghilangkan, atau menurunkan bahaya signifikan ke tingkat aman. Tidak semua kontrol mutu adalah CCP.",
        "case_study": "Proses chilling setelah cooking perlu dikaji apakah menjadi CCP karena memengaruhi pertumbuhan mikroba pada produk matang.",
        "competencies": ["Menganalisis titik kendali", "Membedakan CP dan CCP", "Memberi alasan penentuan CCP"],
    },
    {
        "slug": "critical-limit",
        "title": "Critical Limit",
        "category": "HACCP",
        "duration_minutes": 25,
        "summary": "Batas kritis untuk suhu, waktu, visual, dan parameter proses yang harus dipenuhi.",
        "objectives": ["Membaca batas kritis", "Menilai deviasi", "Mengambil keputusan hold"],
        "learning_material": "Critical limit adalah batas terukur yang memisahkan kondisi aman dan tidak aman. Contohnya target suhu chiller 5°C, suhu cooking minimum, atau waktu pendinginan tertentu.",
        "case_study": "Chiller target 5°C tercatat 11°C. QC menilai bahwa limit terlewati dan produk perlu ditahan sampai evaluasi selesai.",
        "competencies": ["Membaca parameter kritis", "Menentukan status deviasi", "Mencatat limit yang dilanggar"],
    },
    {
        "slug": "ccp-monitoring",
        "title": "Monitoring CCP",
        "category": "Monitoring",
        "duration_minutes": 30,
        "summary": "Teknik monitoring CCP, frekuensi cek, evidence, dan pencatatan hasil monitoring.",
        "objectives": ["Menjalankan monitoring", "Mencatat evidence", "Mengeskalasi hasil abnormal"],
        "learning_material": "Monitoring CCP memastikan batas kritis dipantau secara konsisten. Catatan harus berisi waktu, area, parameter, hasil, petugas, dan tindakan bila terjadi deviasi.",
        "case_study": "Staff mencatat suhu PPIC Chiller pada slot 07:00, 13:00, 16:00, dan 19:00 untuk memastikan cold chain terkendali.",
        "competencies": ["Melakukan pencatatan monitoring", "Membaca tren suhu", "Membuat evidence monitoring"],
    },
    {
        "slug": "corrective-action",
        "title": "Corrective Action",
        "category": "CAPA",
        "duration_minutes": 30,
        "summary": "Tindakan korektif saat critical limit terlewati, termasuk hold product, investigasi, dan eskalasi.",
        "objectives": ["Menahan produk terdampak", "Investigasi penyebab", "Menentukan tindakan perbaikan"],
        "learning_material": "Corrective action harus mengendalikan produk terdampak dan memperbaiki penyebab deviasi. Tindakan dicatat agar keputusan rilis/reject dapat diaudit.",
        "case_study": "Saat suhu chiller 11°C, QC menahan produk, memindahkan ke chiller aman, memeriksa pintu/sensor, dan meminta maintenance mengecek unit.",
        "competencies": [
            "Menentukan hold product",
            "Menyusun tindakan korektif",
            "Mencatat eskalasi dan hasil verifikasi",
        ],
    },
    {
        "slug": "verification-documentation",
        "title": "Verification dan Documentation",
        "category": "Documentation",
        "duration_minutes": 30,
        "summary": "Verifikasi hasil monitoring, review dokumen, audit trail, dan kelengkapan evidence.",
        "objectives": ["Memverifikasi catatan QC", "Mengecek kelengkapan evidence", "Membaca audit trail"],
        "learning_material": "Verification memastikan sistem kontrol berjalan efektif. Dokumentasi menjadi bukti bahwa monitoring, deviasi, dan corrective action dilakukan secara konsisten.",
        "case_study": "Supervisor mereview log suhu, foto evidence, jam input, dan catatan corrective action sebelum menutup deviasi.",
        "competencies": [
            "Melakukan review dokumen",
            "Menilai kelengkapan evidence",
            "Menyiapkan data untuk audit internal",
        ],
    },
    {
        "slug": "traceability-recall",
        "title": "Traceability dan Recall",
        "category": "Traceability",
        "duration_minutes": 35,
        "summary": "Pelacakan batch, bahan baku, proses, distribusi, dan simulasi recall produk.",
        "objectives": ["Melacak batch", "Menghubungkan bahan dan produk", "Menyiapkan data recall"],
        "learning_material": "Traceability memungkinkan tim menelusuri produk dari bahan baku sampai distribusi. Saat ada deviasi, data batch membantu menentukan produk terdampak.",
        "case_study": "Komplain muncul dari batch tertentu. QC menelusuri supplier, waktu produksi, suhu penyimpanan, dan area distribusi.",
        "competencies": ["Membaca alur batch", "Menentukan produk terdampak", "Menyusun data recall internal"],
    },
    {
        "slug": "chiller-freezer-monitoring",
        "title": "Monitoring Suhu Chiller/Freezer",
        "category": "Cold Chain",
        "duration_minutes": 25,
        "summary": "Monitoring suhu chiller/freezer, deviasi cold chain, dan pengendalian produk dingin.",
        "objectives": ["Membaca suhu chiller/freezer", "Menilai deviasi cold chain", "Mengambil tindakan cepat"],
        "learning_material": "Cold chain menjaga produk tetap pada suhu aman. Deviasi harus dilihat dari suhu aktual, durasi, produk terdampak, dan kondisi unit penyimpanan.",
        "case_study": "Freezer menunjukkan -9°C dari target -18°C. QC mengecek durasi, kondisi produk, pintu, dan eskalasi maintenance.",
        "competencies": [
            "Menginterpretasi suhu cold chain",
            "Menentukan prioritas eskalasi",
            "Mencatat log suhu harian",
        ],
    },
    {
        "slug": "central-kitchen-case",
        "title": "Studi Kasus Central Kitchen",
        "category": "Case Study",
        "duration_minutes": 40,
        "summary": "Simulasi keputusan QC dari penerimaan bahan, proses, penyimpanan, sampai rilis produk.",
        "objectives": ["Menganalisis kasus nyata", "Menggabungkan HACCP dan GMP", "Membuat keputusan QC"],
        "learning_material": "Studi kasus menggabungkan food safety, GMP, HACCP, monitoring suhu, corrective action, dokumentasi, dan traceability dalam satu alur kerja QC.",
        "case_study": "Produk ready meal melewati cooking, chilling, packing, dan penyimpanan. Peserta menentukan titik risiko dan tindakan QC di setiap tahap.",
        "competencies": [
            "Membuat analisis kasus QC",
            "Menyusun keputusan berbasis risiko",
            "Menentukan evidence yang wajib dicatat",
        ],
    },
]

SIMULATIONS = [
    {
        "id": "ppic-chiller-001",
        "title": "PPIC Chiller 11°C",
        "area": "PPIC Chiller",
        "target_c": 5,
        "actual_c": 11,
        "scenario": "Saat monitoring pagi, PPIC Chiller tercatat 11°C dari target 5°C. Produk ready meal masih menunggu rilis produksi.",
        "options": [
            {
                "key": "A",
                "label": "Investigasi dan tahan produk",
                "score": 85,
                "feedback": "Tepat: tahan produk terdampak, cek durasi deviasi, sensor, pintu, dan kondisi produk.",
            },
            {
                "key": "B",
                "label": "Corrective action",
                "score": 100,
                "feedback": "Paling tepat jika disertai hold product, pindah chiller cadangan, eskalasi maintenance, dan dokumentasi deviasi.",
            },
            {
                "key": "C",
                "label": "Lanjut produksi",
                "score": 0,
                "feedback": "Tidak aman. Deviasi suhu harus dikendalikan sebelum produksi dilanjutkan.",
            },
        ],
        "best_actions": ["A", "B"],
    }
]

QUIZZES = [
    {
        "id": "qc-basic-quiz",
        "title": "Quiz HACCP dan Food Safety Central Kitchen",
        "module_slug": "haccp-principles",
        "questions": [
            {
                "id": "q1",
                "text": "Saat suhu PPIC Chiller 11°C dari target 5°C, keputusan QC paling aman adalah...",
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
                "text": "Bahaya pangan biologis dalam central kitchen terutama berkaitan dengan...",
                "options": [
                    {"key": "A", "label": "Pertumbuhan mikroba pada bahan atau produk"},
                    {"key": "B", "label": "Serpihan plastik dari kemasan"},
                    {"key": "C", "label": "Residu bahan pembersih"},
                    {"key": "D", "label": "Label harga yang tidak sesuai"},
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
            {
                "id": "q4",
                "text": "Dokumentasi corrective action saat deviasi suhu minimal harus memuat...",
                "options": [
                    {"key": "A", "label": "Jam, area, suhu aktual, produk terdampak, tindakan, PIC, dan verifikasi"},
                    {"key": "B", "label": "Nama menu favorit staff"},
                    {"key": "C", "label": "Hanya foto tanpa catatan"},
                    {"key": "D", "label": "Nomor invoice pembelian"},
                ],
                "answer": "A",
            },
            {
                "id": "q5",
                "text": "Traceability batch berguna terutama untuk apa?",
                "options": [
                    {"key": "A", "label": "Menentukan jalur recall dan audit produk"},
                    {"key": "B", "label": "Menghapus kebutuhan QC"},
                    {"key": "C", "label": "Mengubah resep produksi"},
                    {"key": "D", "label": "Mengganti approval supervisor"},
                ],
                "answer": "A",
            },
        ],
    }
]

LOCAL_PROGRESS = {}
LOCAL_SIMULATION_ATTEMPTS = []
LOCAL_QUIZ_ATTEMPTS = []
LOCAL_MODULE_QUIZ_ATTEMPTS = []
LOCAL_CERTIFICATES = {}
LOCAL_MENTOR_HISTORY = []


class LearningService:
    def __init__(self, repository=None):
        self.repo = repository or LearningRepository()

    def modules(self, user_id):
        progress = self._progress_map(user_id)
        return self._ok(
            [
                {
                    **module,
                    "completed": progress.get(module["slug"], {}).get("status") == "completed",
                    "mini_quiz_passed": self._module_quiz_passed(user_id, module["slug"]),
                }
                for module in self._modules()
            ]
        )

    def module_detail(self, user_id, module_slug):
        module = self._module(module_slug)
        if not module:
            return self._fail("Modul tidak ditemukan", 404)
        progress = self._progress_map(user_id)
        best_score = self._best_module_quiz_score(user_id, module_slug)
        return self._ok(
            {
                **module,
                "completed": progress.get(module_slug, {}).get("status") == "completed",
                "mini_quiz_passed": best_score >= 70,
                "mini_quiz_score": best_score,
                "mini_quiz": [
                    {key: value for key, value in question.items() if key != "answer"}
                    for question in self._module_mini_quiz(module)
                ],
                "key_points": self._module_key_points(module),
            }
        )

    def submit_module_mini_quiz(self, user_id, module_slug, answers):
        module = self._module(module_slug)
        if not module:
            return self._fail("Modul tidak ditemukan", 404)
        answers = answers or {}
        questions = self._module_mini_quiz(module)
        items = []
        correct = 0
        for question in questions:
            selected = answers.get(question["id"])
            is_correct = selected == question["answer"]
            correct += 1 if is_correct else 0
            items.append(
                {
                    "question_id": question["id"],
                    "selected": selected,
                    "correct_answer": question["answer"],
                    "is_correct": is_correct,
                    "explanation": question.get("explanation"),
                }
            )
        score = round((correct / len(questions)) * 100) if questions else 0
        payload = {
            "user_id": user_id,
            "module_slug": module_slug,
            "score": score,
            "answers": answers,
            "passed": score >= 70,
        }
        saved = self.repo.insert_attempt("itdv_module_quiz_attempts", payload) if self.repo.available() else None
        if not saved:
            self._log_persistence_fallback("module mini quiz attempt", user_id)
            LOCAL_MODULE_QUIZ_ATTEMPTS.append(payload)
        return self._ok(
            {
                "module_slug": module_slug,
                "score": score,
                "correct": correct,
                "total": len(questions),
                "passed": score >= 70,
                "items": items,
                "message": "Mini quiz lulus"
                if score >= 70
                else "Selesaikan mini quiz minimal 70 untuk menyelesaikan modul.",
            }
        )

    def complete_module(self, user_id, module_slug):
        module = self._module(module_slug)
        if not module:
            return self._fail("Modul tidak ditemukan", 404)
        if not self._module_quiz_passed(user_id, module_slug):
            return self._fail(
                "Selesaikan mini quiz minimal 70 untuk menyelesaikan modul.",
                409,
                {"mini_quiz_score": self._best_module_quiz_score(user_id, module_slug)},
            )
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
            minimum_score=75,
        )
        certificate_percent = 100 if self._has_certificate(user_id) else 0
        return self._ok(
            {
                "completed_modules": len(completed),
                "total_modules": len(modules),
                "percent": learning_percent,
                "learning_percent": learning_percent,
                "simulation_percent": simulation_percent,
                "quiz_percent": quiz_percent,
                "certificate_percent": certificate_percent,
                "module_slugs": sorted(completed),
            }
        )

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
        return self._ok(
            {
                "simulation_id": simulation_id,
                "selected_action": selected_action,
                "score": score,
                "passed": score >= 70,
                "feedback": feedback,
                "best_actions": simulation["best_actions"],
            }
        )

    def quizzes(self):
        public_quizzes = []
        for quiz in self._quizzes():
            public_quizzes.append(
                {
                    **quiz,
                    "questions": [
                        {key: value for key, value in question.items() if key != "answer"}
                        for question in quiz["questions"]
                    ],
                }
            )
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
            items.append(
                {
                    "question_id": question["id"],
                    "selected": selected,
                    "correct_answer": question["answer"],
                    "is_correct": is_correct,
                }
            )
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
        return self._ok(
            {
                "quiz_id": quiz_id,
                "score": score,
                "correct": correct,
                "total": len(quiz["questions"]),
                "passed": score >= 75,
                "items": items,
            }
        )

    def certificate(self, user):
        progress = self.progress(user["id"])["data"]
        if not self._certificate_unlocked(progress):
            return self._fail(
                "Selesaikan 100% modul, simulation, dan quiz minimal 75 sebelum generate sertifikat",
                409,
                {"progress": progress},
            )
        existing = self._certificate_record(user)
        if existing:
            existing["pdf_filename"] = f"{existing['certificate_id']}.pdf"
            existing["pdf_base64"] = base64.b64encode(self._simple_certificate_pdf(existing)).decode("ascii")
            return self._ok(existing)
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
            "program_name": "QC LearnHub - Pelatihan Internal Quality Control Pangan",
            "issued_at": _now(),
        }
        certificate_data["pdf_filename"] = f"{cert_id}.pdf"
        certificate_data["pdf_base64"] = base64.b64encode(self._simple_certificate_pdf(certificate_data)).decode(
            "ascii"
        )
        return self._ok(certificate_data)

    def certificate_pdf(self, user):
        data = self._certificate_record(user)
        if not data:
            progress = self.progress(user["id"])["data"]
            return self._fail(
                "Generate sertifikat terlebih dahulu sebelum mengunduh PDF",
                404 if self._certificate_unlocked(progress) else 409,
                {"progress": progress},
            )
        pdf = self._simple_certificate_pdf(data)
        return self._ok(
            {
                "filename": f"{data['certificate_id']}.pdf",
                "content_type": "application/pdf",
                "bytes": pdf,
            }
        )

    def career_recommendation(self, user_id):
        progress = self.progress(user_id)["data"]
        modules = set(progress.get("module_slugs") or [])
        simulation_score = self._best_attempt_score(user_id, "itdv_simulation_attempts", LOCAL_SIMULATION_ATTEMPTS)
        quiz_score = self._best_attempt_score(user_id, "itdv_quiz_attempts", LOCAL_QUIZ_ATTEMPTS)
        learning_score = int(progress.get("learning_percent") or 0)

        def has(*slugs):
            return all(slug in modules for slug in slugs)

        recommendations = [
            self._career(
                "QC Staff",
                self._average(learning_score, simulation_score, quiz_score),
                [
                    "Cocok untuk inspeksi proses, sampling, monitoring suhu, dan keputusan pass/fail.",
                    "Skor simulation dan quiz menunjukkan kesiapan membaca kasus operasional QC.",
                ],
            ),
            self._career(
                "QA Staff",
                self._average(
                    learning_score, quiz_score, 85 if has("haccp-principles", "verification-documentation") else 45
                ),
                [
                    "Cocok untuk dokumentasi mutu, verifikasi SOP, CAPA, dan kontrol sistem kualitas.",
                    "Progress modul dan pemahaman quiz menjadi indikator kesiapan QA.",
                ],
            ),
            self._career(
                "Food Safety Officer",
                self._average(
                    quiz_score,
                    90 if has("haccp-principles", "food-safety-hygiene", "hazard-identification") else 45,
                    simulation_score,
                ),
                [
                    "Cocok untuk HACCP, hygiene, pencegahan kontaminasi, dan food safety compliance.",
                    "Materi HACCP/Food Safety dan skor kasus suhu menjadi dasar rekomendasi.",
                ],
            ),
            self._career(
                "Production Control",
                self._average(
                    simulation_score, learning_score, 85 if has("ccp-monitoring", "corrective-action") else 45
                ),
                [
                    "Cocok untuk koordinasi proses, monitoring jadwal produksi, dan eskalasi deviasi operasional.",
                    "Kemampuan membaca kasus dan mengambil tindakan cepat mendukung jalur produksi.",
                ],
            ),
            self._career(
                "Warehouse QC",
                self._average(
                    simulation_score,
                    90 if has("traceability-recall", "chiller-freezer-monitoring") else 45,
                    learning_score,
                ),
                [
                    "Cocok untuk kontrol penerimaan, penyimpanan, cold chain, dan traceability gudang.",
                    "Pemahaman suhu dan batch membantu menjaga mutu bahan serta produk jadi.",
                ],
            ),
            self._career(
                "Auditor Internal",
                self._average(
                    learning_score,
                    quiz_score,
                    90 if has("haccp-principles", "traceability-recall", "verification-documentation") else 40,
                ),
                [
                    "Cocok untuk audit internal, audit trail, traceability, dan pemeriksaan evidence.",
                    "Kesiapan auditor meningkat saat modul traceability dan HACCP selesai.",
                ],
            ),
        ]
        recommendations.sort(key=lambda item: item["match_percent"], reverse=True)
        return self._ok(
            {
                "primary": recommendations[0],
                "recommendations": recommendations,
                "scores": {
                    "learning": learning_score,
                    "simulation": simulation_score,
                    "quiz": quiz_score,
                },
            }
        )

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
        rows = (
            self.repo.fetch_table(
                "itdv_mentor_history",
                filters=[("eq", "user_id", user_id)],
                order_by="created_at",
                desc=True,
                limit=20,
            )
            if self.repo.available()
            else []
        )
        if not rows:
            rows = [row for row in reversed(LOCAL_MENTOR_HISTORY) if row.get("user_id") == user_id][:20]
        return self._ok(rows)

    def _modules(self):
        rows = self.repo.fetch_table("itdv_modules", order_by="sort_order") if self.repo.available() else []
        rows = [
            self._module_public(row)
            for row in rows
            if not row.get("archived") and row.get("published", True) is not False
        ]
        return rows or MODULES

    def _simulations(self):
        rows = self.repo.fetch_table("itdv_simulations", order_by="created_at") if self.repo.available() else []
        rows = [
            self._simulation_public(row)
            for row in rows
            if not row.get("archived") and row.get("published", True) is not False
        ]
        return rows or SIMULATIONS

    def _quizzes(self):
        question_rows = (
            self.repo.fetch_table("itdv_quiz_questions", order_by="created_at") if self.repo.available() else []
        )
        question_rows = [
            row for row in question_rows if not row.get("archived") and row.get("published", True) is not False
        ]
        if question_rows:
            return [
                {
                    "id": "itdv-main-quiz",
                    "title": "Quiz ITDV Learning Center",
                    "module_slug": None,
                    "questions": [self._question_public(row) for row in question_rows],
                }
            ]
        rows = self.repo.fetch_table("itdv_quizzes", order_by="created_at") if self.repo.available() else []
        return rows or QUIZZES

    def _progress_map(self, user_id):
        rows = (
            self.repo.fetch_table(
                "itdv_progress",
                filters=[("eq", "user_id", user_id), ("eq", "status", "completed")],
            )
            if self.repo.available()
            else []
        )
        progress = {row.get("module_slug"): row for row in rows if row.get("module_slug")}
        for slug in LOCAL_PROGRESS.get(user_id, set()):
            progress.setdefault(slug, {"module_slug": slug, "status": "completed"})
        return progress

    def _module_quiz_passed(self, user_id, module_slug):
        return self._best_module_quiz_score(user_id, module_slug) >= 70

    def _best_module_quiz_score(self, user_id, module_slug):
        rows = (
            self.repo.fetch_table(
                "itdv_module_quiz_attempts",
                filters=[("eq", "user_id", user_id), ("eq", "module_slug", module_slug)],
            )
            if self.repo.available()
            else []
        )
        scores = [int(row.get("score") or 0) for row in rows]
        scores.extend(
            int(row.get("score") or 0)
            for row in LOCAL_MODULE_QUIZ_ATTEMPTS
            if row.get("user_id") == user_id and row.get("module_slug") == module_slug
        )
        return max(scores or [0])

    def _module_mini_quiz(self, module):
        slug = module.get("slug")
        rows = (
            self.repo.fetch_table(
                "itdv_module_mini_quizzes",
                filters=[("eq", "module_slug", slug)],
                order_by="created_at",
            )
            if self.repo.available()
            else []
        )
        rows = [row for row in rows if not row.get("archived") and row.get("published", True) is not False]
        if rows:
            return [self._question_public(row) for row in rows]
        title = module.get("title")
        category = module.get("category")
        return [
            {
                "id": f"{slug}-q1",
                "text": f"Apa fokus utama modul {title}?",
                "options": [
                    {"key": "A", "label": module.get("summary")},
                    {"key": "B", "label": "Menghapus pencatatan QC agar proses lebih cepat"},
                    {"key": "C", "label": "Mengabaikan deviasi bila produk terlihat normal"},
                    {"key": "D", "label": "Mengganti approval supervisor"},
                ],
                "answer": "A",
                "explanation": "Fokus modul mengikuti ringkasan kompetensi dan praktik QC pangan yang dijelaskan pada materi.",
            },
            {
                "id": f"{slug}-q2",
                "text": "Jika ditemukan deviasi pada proses central kitchen, tindakan QC yang paling tepat adalah...",
                "options": [
                    {"key": "A", "label": "Melanjutkan proses tanpa catatan"},
                    {"key": "B", "label": "Menilai risiko, menahan produk terdampak bila perlu, dan mencatat evidence"},
                    {"key": "C", "label": "Mengubah target parameter agar sesuai hasil aktual"},
                    {"key": "D", "label": "Menunggu sampai akhir shift tanpa eskalasi"},
                ],
                "answer": "B",
                "explanation": "Deviasi harus dinilai berbasis risiko, dikendalikan, dan didokumentasikan.",
            },
            {
                "id": f"{slug}-q3",
                "text": f"Kompetensi kerja yang paling terkait dengan modul {category} ini adalah...",
                "options": [
                    {"key": "A", "label": "Membuat keputusan QC berbasis risiko dan bukti"},
                    {"key": "B", "label": "Menghilangkan kebutuhan monitoring suhu"},
                    {"key": "C", "label": "Mengganti SOP tanpa verifikasi"},
                    {"key": "D", "label": "Mengabaikan traceability batch"},
                ],
                "answer": "A",
                "explanation": "Kompetensi QC pangan menekankan keputusan berbasis risiko, evidence, dan pencatatan.",
            },
        ]

    def _module_key_points(self, module):
        points = list(module.get("objectives") or [])
        points.extend((module.get("competencies") or [])[:2])
        return points[:5] or [
            "Baca risiko proses",
            "Ambil keputusan QC berbasis bukti",
            "Catat evidence dan tindakan",
        ]

    def _module_public(self, row):
        duration = row.get("duration_minutes")
        if duration is None:
            duration = row.get("estimated_time")
        return {
            **row,
            "summary": row.get("summary") or row.get("description") or "",
            "duration_minutes": duration or 0,
            "objectives": row.get("objectives") or row.get("competencies") or [],
            "competencies": row.get("competencies") or row.get("objectives") or [],
            "learning_material": row.get("learning_material") or row.get("summary") or row.get("description") or "",
            "case_study": row.get("case_study") or "",
        }

    def _simulation_public(self, row):
        options = row.get("options") or []
        if not options and any(row.get(f"option_{key}") for key in ("a", "b", "c")):
            best = (row.get("best_actions") or [""])[0]
            options = [
                {"key": "A", "label": row.get("option_a"), "score": 100 if best == "A" else 0},
                {"key": "B", "label": row.get("option_b"), "score": 100 if best == "B" else 0},
                {"key": "C", "label": row.get("option_c"), "score": 100 if best == "C" else 0},
            ]
        return {**row, "options": options, "best_actions": row.get("best_actions") or []}

    def _question_public(self, row):
        return {
            "id": str(row.get("id")),
            "text": row.get("question") or row.get("text"),
            "options": [
                {"key": "A", "label": row.get("option_a")},
                {"key": "B", "label": row.get("option_b")},
                {"key": "C", "label": row.get("option_c")},
                {"key": "D", "label": row.get("option_d")},
            ],
            "answer": row.get("correct_answer") or row.get("answer"),
            "explanation": row.get("explanation"),
        }

    def _attempt_percent(self, user_id, table, id_field, total_ids, local_rows, minimum_score=70):
        expected = {item for item in total_ids if item}
        if not expected:
            return 0
        rows = (
            self.repo.fetch_table(
                table,
                filters=[("eq", "user_id", user_id), ("gte", "score", minimum_score)],
            )
            if self.repo.available()
            else []
        )
        passed = {
            row.get(id_field)
            for row in rows
            if row.get(id_field) in expected and int(row.get("score") or 0) >= minimum_score
        }
        for row in local_rows:
            if (
                row.get("user_id") == user_id
                and int(row.get("score") or 0) >= minimum_score
                and row.get(id_field) in expected
            ):
                passed.add(row.get(id_field))
        return self._percent(len(passed), len(expected))

    def _has_certificate(self, user_id):
        rows = (
            self.repo.fetch_table(
                "itdv_certificates",
                filters=[("eq", "user_id", user_id), ("eq", "program_code", "ITDV-QC-FOOD")],
                limit=1,
            )
            if self.repo.available()
            else []
        )
        return bool(rows or LOCAL_CERTIFICATES.get((user_id, "ITDV-QC-FOOD")))

    def _certificate_record(self, user):
        user_id = user["id"]
        rows = (
            self.repo.fetch_table(
                "itdv_certificates",
                filters=[("eq", "user_id", user_id), ("eq", "program_code", "ITDV-QC-FOOD")],
                order_by="issued_at",
                desc=True,
                limit=1,
            )
            if self.repo.available()
            else []
        )
        row = (rows or [LOCAL_CERTIFICATES.get((user_id, "ITDV-QC-FOOD"))])[0]
        if not row:
            return None
        return {
            "certificate_id": row.get("certificate_id"),
            "user_id": user_id,
            "program_code": row.get("program_code") or "ITDV-QC-FOOD",
            "participant_name": row.get("participant_name") or user.get("name") or user.get("username") or "Peserta",
            "program_name": "QC LearnHub - Pelatihan Internal Quality Control Pangan",
            "issued_at": row.get("issued_at") or _now(),
        }

    def _best_attempt_score(self, user_id, table, local_rows):
        rows = (
            self.repo.fetch_table(
                table,
                filters=[("eq", "user_id", user_id)],
            )
            if self.repo.available()
            else []
        )
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
        return all(
            int(progress.get(key) or 0) >= 100
            for key in (
                "learning_percent",
                "simulation_percent",
                "quiz_percent",
            )
        )

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
            "Sertifikat Penyelesaian QC LearnHub",
            f"Participant: {data.get('participant_name') or 'Peserta'}",
            f"Program: {data.get('program_name') or 'Simulasi Quality Control Industri Pangan'}",
            f"Certificate ID: {data.get('certificate_id')}",
            f"Issued At: {str(data.get('issued_at') or '')[:10]}",
            "Sertifikat penyelesaian pelatihan internal berdasarkan modul HACCP, GMP, food safety, traceability, dan kompetensi kerja QC pangan.",
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
