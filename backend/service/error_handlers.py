"""
Global Flask error handling.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from backend.middleware.security_middleware import AuthError
from backend.service.request_validation import RequestValidationError

logger = logging.getLogger("qc.errors")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AuthError)
    def handle_auth_error(exc: AuthError):
        return jsonify({"error": str(exc)}), exc.status_code

    @app.errorhandler(RequestValidationError)
    def handle_validation_error(exc: RequestValidationError):
        return jsonify({"error": "Invalid request", "details": exc.errors}), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        return jsonify({"error": exc.description}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "Internal server error"}), 500
