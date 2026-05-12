"""
Request parsing and validation primitives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Type

from flask import request


class RequestValidationError(ValueError):
    def __init__(self, errors: Any):
        super().__init__("Invalid request")
        self.errors = errors


@dataclass
class LoginRequest:
    username: str
    password: str


@dataclass
class BatchCreateRequest:
    product_id: str
    batch_code: str
    production_date: str | None = None
    shift: str | None = None
    operator_id: str | None = None
    qc_officer_id: str | None = None


@dataclass
class TemperatureLogRequest:
    room_id: str
    temperature: float
    device_id: str | None = None
    staff_id: str | None = None
    humidity: float | None = None
    reason: str | None = None
    photo_url: str | None = None
    threshold: float | None = None


@dataclass
class QCValidateRequest:
    temperature: float
    unit_type: str = "chiller"


def request_payload() -> dict[str, Any]:
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        return request.form.to_dict()
    return request.get_json(silent=True) or {}


def parse_form_json(name: str, default: Any = None) -> Any:
    raw = request.form.get(name)
    if raw in (None, ""):
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RequestValidationError({name: f"Invalid JSON: {exc.msg}"}) from exc


def _required(data: dict[str, Any], name: str, max_len: int | None = None) -> str:
    value = str(data.get(name, "")).strip()
    if not value:
        raise RequestValidationError({name: "required"})
    if max_len and len(value) > max_len:
        raise RequestValidationError({name: f"must be at most {max_len} characters"})
    return value


def _optional_str(data: dict[str, Any], name: str, max_len: int | None = None) -> str | None:
    value = data.get(name)
    if value in (None, ""):
        return None
    value = str(value).strip()
    if max_len and len(value) > max_len:
        raise RequestValidationError({name: f"must be at most {max_len} characters"})
    return value


def _number(data: dict[str, Any], name: str, required: bool, min_value: float, max_value: float) -> float | None:
    raw = data.get(name)
    if raw in (None, ""):
        if required:
            raise RequestValidationError({name: "required"})
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RequestValidationError({name: "must be a number"}) from exc
    if value < min_value or value > max_value:
        raise RequestValidationError({name: f"must be between {min_value} and {max_value}"})
    return value


def validate_model(model: Type[Any], data: dict[str, Any]) -> Any:
    allowed_fields = set(getattr(model, "__dataclass_fields__", {}).keys())
    unknown = set(data.keys()) - allowed_fields
    if unknown:
        raise RequestValidationError({"unknown_fields": sorted(unknown)})

    if model is LoginRequest:
        return LoginRequest(
            username=_required(data, "username", 80),
            password=_required(data, "password", 256),
        )
    if model is BatchCreateRequest:
        return BatchCreateRequest(
            product_id=_required(data, "product_id", 120),
            batch_code=_required(data, "batch_code", 80),
            production_date=_optional_str(data, "production_date", 20),
            shift=_optional_str(data, "shift", 40),
            operator_id=_optional_str(data, "operator_id", 80),
            qc_officer_id=_optional_str(data, "qc_officer_id", 80),
        )
    if model is TemperatureLogRequest:
        return TemperatureLogRequest(
            room_id=_required(data, "room_id", 80),
            device_id=_optional_str(data, "device_id", 80),
            staff_id=_optional_str(data, "staff_id", 80),
            temperature=_number(data, "temperature", True, -80, 100),
            humidity=_number(data, "humidity", False, 0, 100),
            reason=_optional_str(data, "reason", 1000),
            photo_url=_optional_str(data, "photo_url", 2048),
            threshold=_number(data, "threshold", False, -80, 100),
        )
    if model is QCValidateRequest:
        unit_type = _optional_str(data, "unit_type", 40) or "chiller"
        if unit_type not in {"chiller", "freezer", "ambient", "room_temp", "undercounter"}:
            raise RequestValidationError({"unit_type": "invalid"})
        return QCValidateRequest(
            unit_type=unit_type,
            temperature=_number(data, "temperature", True, -80, 100),
        )
    raise RuntimeError(f"No validator registered for {model}")
