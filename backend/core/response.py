"""Standard API response helpers."""
from typing import Any, Dict, Optional


def success(data: Any = None, message: str = "OK", status_code: int = 200) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "data": data,
        "code": status_code,
    }


def error(message: str = "Error", code: int = 500, details: Optional[Any] = None) -> Dict[str, Any]:
    payload = {
        "status": "error",
        "message": message,
        "code": code,
    }
    if details is not None:
        payload["details"] = details
    return payload


def paginated(items: Any, total: int, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    return {
        "status": "success",
        "data": items,
        "meta": {"total": total, "page": page, "per_page": per_page},
    }
