from backend.services.learning_service import LearningService, MODULES


def test_learning_modules_and_progress_without_database():
    service = LearningService(repository=NoDatabaseRepo())
    user_id = "student-1"

    modules = service.modules(user_id)
    assert modules["success"] is True
    assert len(modules["data"]) == 5

    progress = service.complete_module(user_id, "haccp")
    assert progress["data"]["completed_modules"] == 1
    assert progress["data"]["percent"] == 20
    assert progress["data"]["learning_percent"] == 20
    assert progress["data"]["simulation_percent"] == 0
    assert progress["data"]["quiz_percent"] == 0
    assert progress["data"]["certificate_percent"] == 0


def test_learning_progress_is_persisted_to_repository():
    repo = RecordingRepo()
    service = LearningService(repository=repo)

    result = service.complete_module("student-2", "haccp")

    assert result["success"] is True
    assert repo.progress_payloads[-1]["user_id"] == "student-2"
    assert repo.progress_payloads[-1]["module_slug"] == "haccp"
    assert repo.progress_payloads[-1]["status"] == "completed"


def test_simulation_scoring():
    result = LearningService(repository=NoDatabaseRepo()).submit_simulation(
        "student-1",
        "ppic-chiller-001",
        "B",
    )

    assert result["success"] is True
    assert result["data"]["score"] == 100
    assert result["data"]["passed"] is True
    assert "Dalam HACCP" in result["data"]["feedback"]
    assert "Suhu 11°C melebihi batas aman 5°C" in result["data"]["feedback"]


def test_simulation_wrong_answer_explains_risk():
    result = LearningService(repository=NoDatabaseRepo()).submit_simulation(
        "student-1",
        "ppic-chiller-001",
        "C",
    )

    assert result["success"] is True
    assert result["data"]["score"] == 0
    assert result["data"]["passed"] is False
    assert "Risiko mikroba meningkat" in result["data"]["feedback"]
    assert "corrective action" in result["data"]["feedback"]


def test_simulation_answer_and_score_are_persisted():
    repo = RecordingRepo()
    result = LearningService(repository=repo).submit_simulation(
        "student-3",
        "ppic-chiller-001",
        "A",
    )

    assert result["success"] is True
    assert repo.attempts[-1]["table"] == "itdv_simulation_attempts"
    assert repo.attempts[-1]["payload"]["selected_action"] == "A"
    assert repo.attempts[-1]["payload"]["score"] == 70
    assert "Dalam HACCP" in repo.attempts[-1]["payload"]["feedback"]


def test_quiz_auto_score():
    result = LearningService(repository=NoDatabaseRepo()).submit_quiz(
        "student-1",
        "qc-basic-quiz",
        {"q1": "B", "q2": "A", "q3": "B"},
    )

    assert result["success"] is True
    assert result["data"]["score"] == 100
    assert result["data"]["correct"] == 3


def test_quiz_submit_persists_score_and_answers():
    repo = RecordingRepo()
    answers = {"q1": "B", "q2": "A", "q3": "D"}

    result = LearningService(repository=repo).submit_quiz("student-4", "qc-basic-quiz", answers)

    assert result["success"] is True
    assert result["data"]["score"] == 67
    assert result["data"]["passed"] is False
    assert repo.attempts[-1]["table"] == "itdv_quiz_attempts"
    assert repo.attempts[-1]["payload"]["answers"] == answers


def test_quiz_progress_requires_minimum_score_75():
    repo = RecordingRepo()
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 70}]

    result = LearningService(repository=repo).progress("student-8")

    assert result["data"]["quiz_percent"] == 0


def test_progress_breakdown_uses_existing_attempt_and_certificate_tables():
    repo = RecordingRepo()
    repo.completed_modules = {module["slug"] for module in MODULES}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]
    repo.certificates = [{"user_id": "student-8", "program_code": "ITDV-QC-FOOD"}]

    result = LearningService(repository=repo).progress("student-8")

    assert result["data"]["learning_percent"] == 100
    assert result["data"]["simulation_percent"] == 100
    assert result["data"]["quiz_percent"] == 100
    assert result["data"]["certificate_percent"] == 100


def test_career_recommendation_is_rule_based_and_ranked():
    repo = RecordingRepo()
    repo.completed_modules = {"haccp", "food-safety", "traceability", "monitoring-suhu", "qc-dasar"}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]

    result = LearningService(repository=repo).career_recommendation("student-8")

    assert result["success"] is True
    assert result["data"]["primary"]["title"] in {"QC", "QA", "Food Safety", "Auditor", "Supply Chain"}
    assert [item["title"] for item in result["data"]["recommendations"]] == [
        item["title"] for item in sorted(
            result["data"]["recommendations"],
            key=lambda row: row["match_percent"],
            reverse=True,
        )
    ]
    assert {item["title"] for item in result["data"]["recommendations"]} == {
        "QC",
        "QA",
        "Food Safety",
        "Auditor",
        "Supply Chain",
    }


def test_mentor_answers_temperature_question_and_saves_history():
    repo = RecordingRepo()
    service = LearningService(repository=repo)

    result = service.mentor_answer("student-9", "Kenapa suhu 11°C berbahaya?")

    assert result["success"] is True
    assert "food safety" in result["data"]["answer"].lower()
    assert "HACCP" in result["data"]["answer"]
    assert "Corrective action" in result["data"]["answer"] or "corrective action" in result["data"]["answer"]
    assert repo.attempts[-1]["table"] == "itdv_mentor_history"
    assert repo.attempts[-1]["payload"]["question"] == "Kenapa suhu 11°C berbahaya?"


def test_mentor_history_returns_saved_rows():
    repo = RecordingRepo()
    repo.mentor_history = [{
        "user_id": "student-9",
        "question": "Kenapa suhu 11°C berbahaya?",
        "answer": "Food safety HACCP Corrective action",
        "topics": ["Food safety", "HACCP", "Corrective action"],
    }]

    result = LearningService(repository=repo).mentor_history("student-9")

    assert result["success"] is True
    assert result["data"][0]["question"] == "Kenapa suhu 11°C berbahaya?"


def test_certificate_requires_modules_quiz_and_simulation_complete():
    service = LearningService(repository=NoDatabaseRepo())

    result = service.certificate({"id": "student-5", "username": "student"})

    assert result["success"] is False
    assert result["status"] == 409


def test_certificate_is_persisted_after_all_requirements_complete():
    repo = RecordingRepo()
    repo.completed_modules = {module["slug"] for module in MODULES}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]

    result = LearningService(repository=repo).certificate({"id": "student-6", "username": "student"})

    assert result["success"] is True
    assert repo.certificates[-1]["user_id"] == "student-6"
    assert repo.certificates[-1]["program_code"] == "ITDV-QC-FOOD"
    assert result["data"]["pdf_filename"].endswith(".pdf")
    assert result["data"]["pdf_base64"]


def test_certificate_generation_is_idempotent_when_certificate_exists():
    repo = RecordingRepo()
    repo.completed_modules = {module["slug"] for module in MODULES}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]

    first = LearningService(repository=repo).certificate({"id": "student-6", "username": "student"})
    second = LearningService(repository=repo).certificate({"id": "student-6", "username": "student"})

    assert first["data"]["certificate_id"] == second["data"]["certificate_id"]
    assert len(repo.certificates) == 1


def test_certificate_pdf_is_simple_pdf_after_requirements_complete():
    repo = RecordingRepo()
    repo.completed_modules = {module["slug"] for module in MODULES}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]
    LearningService(repository=repo).certificate({"id": "student-6", "username": "student"})

    result = LearningService(repository=repo).certificate_pdf({"id": "student-6", "username": "student"})

    assert result["success"] is True
    assert result["data"]["content_type"] == "application/pdf"
    assert result["data"]["bytes"].startswith(b"%PDF-1.4")


def test_certificate_pdf_does_not_generate_certificate_as_side_effect():
    repo = RecordingRepo()
    repo.completed_modules = {module["slug"] for module in MODULES}
    repo.simulation_attempts = [{"simulation_id": "ppic-chiller-001", "score": 100}]
    repo.quiz_attempts = [{"quiz_id": "qc-basic-quiz", "score": 100}]

    result = LearningService(repository=repo).certificate_pdf({"id": "student-6", "username": "student"})

    assert result["success"] is False
    assert result["status"] == 404
    assert repo.certificates == []


def test_learning_api_endpoints(client, staff_headers):
    modules = client.get("/api/learning/modules", headers=staff_headers)
    assert modules.status_code == 200
    assert modules.get_json()["success"] is True

    progress = client.get("/api/learning/progress", headers=staff_headers)
    assert progress.status_code == 200
    assert progress.get_json()["success"] is True

    career = client.get("/api/learning/career-recommendation", headers=staff_headers)
    assert career.status_code == 200
    assert career.get_json()["success"] is True

    mentor = client.post(
        "/api/learning/mentor",
        headers=staff_headers,
        json={"question": "Kenapa suhu 11°C berbahaya?"},
    )
    assert mentor.status_code == 200
    assert mentor.get_json()["success"] is True

    history = client.get("/api/learning/mentor/history", headers=staff_headers)
    assert history.status_code == 200
    assert history.get_json()["success"] is True

    simulation = client.post(
        "/api/learning/simulations/ppic-chiller-001/submit",
        headers=staff_headers,
        json={"selected_action": "B"},
    )
    assert simulation.status_code == 200
    assert simulation.get_json()["data"]["score"] == 100

    quiz = client.post(
        "/api/learning/quizzes/qc-basic-quiz/submit",
        headers=staff_headers,
        json={"answers": {"q1": "B", "q2": "A", "q3": "B"}},
    )
    assert quiz.status_code == 200
    assert quiz.get_json()["data"]["score"] == 100

    certificate = client.post("/api/learning/certificate", headers=staff_headers)
    assert certificate.status_code == 409


def test_repository_uses_final_progress_table_name():
    repo = RecordingSupabaseRepo()

    repo.upsert_progress({
        "user_id": "student-7",
        "module_slug": "haccp",
        "status": "completed",
        "completed_at": "2026-05-22T00:00:00Z",
    })

    assert repo.tables == ["itdv_progress"]


class NoDatabaseRepo:
    def available(self):
        return False

    def fetch_table(self, *args, **kwargs):
        return []

    def upsert_progress(self, payload):
        return None

    def insert_attempt(self, table, payload):
        return None

    def upsert_certificate(self, payload):
        return None


class RecordingRepo:
    def __init__(self):
        self.completed_modules = set()
        self.progress_payloads = []
        self.attempts = []
        self.certificates = []
        self.simulation_attempts = []
        self.quiz_attempts = []
        self.mentor_history = []

    def available(self):
        return True

    def fetch_table(self, table, *args, **kwargs):
        if table == "itdv_progress":
            return [
                {"module_slug": slug, "status": "completed"}
                for slug in self.completed_modules
            ]
        if table == "itdv_simulation_attempts":
            return [
                {"user_id": "student-8", **row}
                for row in self.simulation_attempts
            ]
        if table == "itdv_quiz_attempts":
            return [
                {"user_id": "student-8", **row}
                for row in self.quiz_attempts
            ]
        if table == "itdv_certificates":
            return self.certificates
        if table == "itdv_mentor_history":
            return self.mentor_history
        return []

    def upsert_progress(self, payload):
        self.progress_payloads.append(payload)
        self.completed_modules.add(payload["module_slug"])
        return [payload]

    def insert_attempt(self, table, payload):
        self.attempts.append({"table": table, "payload": payload})
        return [payload]

    def upsert_certificate(self, payload):
        existing = next(
            (
                item for item in self.certificates
                if item.get("user_id") == payload.get("user_id")
                and item.get("program_code") == payload.get("program_code")
            ),
            None,
        )
        if existing:
            existing.update(payload)
            return [existing]
        self.certificates.append(payload)
        return [payload]


class RecordingSupabaseRepo:
    def __init__(self):
        from backend.repositories.learning_repository import LearningRepository

        self.tables = []
        self.repo = LearningRepository(sb_client=self)

    def table(self, table_name):
        self.tables.append(table_name)
        return self

    def upsert(self, *args, **kwargs):
        return self

    def execute(self):
        return type("Result", (), {"data": [{"ok": True}]})()

    def upsert_progress(self, payload):
        return self.repo.upsert_progress(payload)
