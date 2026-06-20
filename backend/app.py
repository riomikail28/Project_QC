"""
QC Central Kitchen - Flask Application Entry Point
====================================================
PT Astro Teknologi Indonesia - Central Kitchen

Run:
    python backend/app.py

Or from project root:
    python -m backend.app
"""

from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",  # nosec B104
        port=5000,
        debug=True,
    )
