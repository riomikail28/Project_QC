from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_extensionless_dashboard_static_files_exist():
    forbidden = [
        ROOT / "frontend" / "admin" / "dashboard",
        ROOT / "frontend" / "staff" / "dashboard",
    ]

    assert not any(path.exists() for path in forbidden)


def test_demo_seed_contains_hashed_demo_accounts_and_demo_data():
    seed = (ROOT / "supabase" / "seed" / "001_demo_seed.sql").read_text(encoding="utf-8")

    assert "demo.admin@qcenterprise.id" in seed
    assert "demo.staff@qcenterprise.id" in seed
    assert "encode(digest('demo123456', 'sha256'), 'hex')" in seed
    assert "staff_accounts" in seed
    assert "temperature_logs" in seed
    assert "qc_reports" in seed
    assert "itdv_progress" in seed


def test_readme_is_github_portfolio_ready():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    required = [
        "Aplikasi Quality Control & Traceability Central Kitchen",
        "https://project-qc-mu.vercel.app/",
        "demo.admin@qcenterprise.id",
        "demo.staff@qcenterprise.id",
        "Dashboard & Panel Kontrol Admin",
        "Alur Kerja Staff Mobile-First",
        "Python Flask",
        "Supabase PostgreSQL",
        "pytest",
        "Integrasi sensor suhu berbasis IoT",
        "Rio Mikail",
    ]

    for text in required:
        assert text in readme
