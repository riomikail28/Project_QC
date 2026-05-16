from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sync_contract_documents_final_tables():
    contract = (ROOT / "docs" / "PROJECT_QC_SYNC_CONTRACT.md").read_text(encoding="utf-8")

    for table in [
        "facility_rooms",
        "facility_devices",
        "facility_logs",
        "production_batches",
        "qc_reports",
        "qc_evidence",
        "staff_accounts",
        "users",
    ]:
        assert table in contract

    assert "Do not use" in contract
    assert "rooms" in contract
    assert "storage_units" in contract


def test_sync_migration_seeds_general_qc_and_facility_defaults():
    migration = (ROOT / "supabase" / "migrations" / "008_sync_qc_production_contract.sql").read_text(encoding="utf-8")

    assert "GENERAL-QC" in migration
    assert "facility_rooms" in migration
    assert "facility_devices" in migration
    assert "PPIC" in migration
    assert "Suhu Ruangan" in migration
    assert "Chiller" in migration
    assert "Freezer" in migration
