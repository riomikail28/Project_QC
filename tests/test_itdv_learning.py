from backend.services.learning_service import LearningService


def test_learning_modules_and_progress_without_database():
    service = LearningService(repository=NoDatabaseRepo())
    user_id = "student-1"

    modules = service.modules(user_id)
    assert modules["success"] is True
    assert len(modules["data"]) == 5

    progress = service.complete_module(user_id, "haccp")
    assert progress["data"]["completed_modules"] == 1
    assert progress["data"]["percent"] == 20


def test_simulation_scoring():
    result = LearningService(repository=NoDatabaseRepo()).submit_simulation(
        "student-1",
        "ppic-chiller-001",
        "B",
    )

    assert result["success"] is True
    assert result["data"]["score"] == 100
    assert result["data"]["passed"] is True


def test_quiz_auto_score():
    result = LearningService(repository=NoDatabaseRepo()).submit_quiz(
        "student-1",
        "qc-basic-quiz",
        {"q1": "B", "q2": "A", "q3": "B"},
    )

    assert result["success"] is True
    assert result["data"]["score"] == 100
    assert result["data"]["correct"] == 3


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
