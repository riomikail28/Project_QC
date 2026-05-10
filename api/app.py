"""
Vercel Python entrypoint for QC Central Kitchen API.

This wrapper ensures Vercel can correctly deploy the Flask app as a function handler.
"""
from backend import create_app

app = create_app()

# Vercel's @vercel/python uses the exported `app` callable.
