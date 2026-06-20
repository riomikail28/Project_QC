"""
Supabase Client Singleton
=========================
Manages the connection to the Supabase database.
Ensures only one client instance exists throughout the application.
"""

import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

try:
    from supabase import Client, create_client
except ImportError:
    create_client = None
    Client = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qc.db.supabase")
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "qc-evidence")

# Shared singleton instance
_client: Client = None
_admin_client: Client = None
_failed: bool = False
_last_error: str = ""


INVALID_KEY_MESSAGE = "Invalid Supabase API key. Check Vercel SUPABASE_SERVICE_ROLE_KEY."
CONNECTION_FAILED_MESSAGE = "Supabase connection failed. Please check production environment variables."
SUPABASE_URL_MESSAGE = "SUPABASE_URL must be a valid https://<project-ref>.supabase.co URL."
SERVICE_ROLE_JWT_MESSAGE = (
    "SUPABASE_SERVICE_ROLE_KEY must be the service_role JWT from Supabase Dashboard Settings > API, not a CLI secret."
)
ANON_KEY_MESSAGE = "SUPABASE_ANON_KEY must be configured with the public anon JWT."
STORAGE_BUCKET_MESSAGE = "SUPABASE_STORAGE_BUCKET must be a valid bucket name."


@dataclass(frozen=True)
class SupabaseEnvStatus:
    success: bool
    message: str
    supabase_url_configured: bool
    service_role_key_configured: bool
    anon_key_configured: bool
    storage_bucket: str
    supabase_url_valid: bool = False
    service_role_key_valid: bool = False
    anon_key_valid: bool = False
    storage_bucket_valid: bool = False
    error_code: str = "OK"


def _supabase_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()


def _anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or "").strip()


def _service_key() -> str:
    return (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()


def _is_placeholder(value: str) -> bool:
    raw = str(value or "").strip().lower()
    return (
        not raw
        or raw.startswith("your-")
        or raw
        in {
            "test-key",
            "service-role-key",
            "replace-me",
            "your-supabase-anon-key",
            "your-supabase-service-role-key",
            "anon-key",
        }
        or "your-project-ref" in raw
    )


def _is_cli_secret(value: str) -> bool:
    """Check if the key is a Supabase CLI secret (sb_secret_...) instead of a JWT."""
    return str(value or "").startswith("sb_secret_")


def _decode_jwt_payload(value: str) -> dict:
    parts = str(value or "").split(".")
    if len(parts) != 3:
        raise ValueError("not a JWT")
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(f"{payload}{padding}".encode("utf-8"))
    return json.loads(decoded.decode("utf-8"))


def _jwt_role(value: str) -> str | None:
    try:
        payload = _decode_jwt_payload(value)
    except Exception:
        return None
    return payload.get("role")


def _is_jwt(value: str) -> bool:
    try:
        _decode_jwt_payload(value)
        return True
    except Exception:
        return False


def _is_valid_supabase_url(url: str) -> bool:
    return bool(re.fullmatch(r"https://[a-z0-9-]+\.supabase\.co", str(url or "").strip().rstrip("/"), re.IGNORECASE))


def _is_valid_bucket_name(bucket: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,61}[A-Za-z0-9]", str(bucket or "")))


def _is_invalid_key_error(error_text: str) -> bool:
    text = str(error_text or "").lower()
    return "invalid api key" in text or "jwt" in text and "invalid" in text


def validate_supabase_env(require_service_role: bool = True) -> SupabaseEnvStatus:
    """Validate required Supabase env without exposing secret values."""
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = _service_key()
    anon_key = _anon_key()
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "qc-evidence").strip() or "qc-evidence"
    url_configured = bool(url) and not _is_placeholder(url)
    service_configured = bool(service_key) and not _is_placeholder(service_key)
    anon_configured = bool(anon_key) and not _is_placeholder(anon_key)
    url_valid = url_configured and _is_valid_supabase_url(url)
    service_valid = (
        service_configured
        and not _is_cli_secret(service_key)
        and _is_jwt(service_key)
        and _jwt_role(service_key) == "service_role"
    )
    anon_valid = (
        anon_configured and not _is_cli_secret(anon_key) and _is_jwt(anon_key) and _jwt_role(anon_key) != "service_role"
    )
    bucket_valid = _is_valid_bucket_name(bucket)

    def status(success, message, error_code):
        return SupabaseEnvStatus(
            success,
            message,
            url_configured,
            service_configured,
            anon_configured,
            bucket,
            url_valid,
            service_valid,
            anon_valid,
            bucket_valid,
            error_code,
        )

    if not url_configured:
        return status(False, "SUPABASE_URL is not configured", "SUPABASE_URL_MISSING")
    if not url_valid:
        return status(False, SUPABASE_URL_MESSAGE, "SUPABASE_URL_INVALID")
    if require_service_role and not service_valid:
        msg = SERVICE_ROLE_JWT_MESSAGE
        if _is_cli_secret(service_key):
            msg = "SUPABASE_SERVICE_ROLE_KEY has invalid format (CLI Secret detected). Use the Service Role JWT."
        elif _is_placeholder(service_key):
            msg = "SUPABASE_SERVICE_ROLE_KEY is still a placeholder"
        elif not service_configured:
            msg = "SUPABASE_SERVICE_ROLE_KEY is not configured"
        return status(False, msg, "SUPABASE_SERVICE_ROLE_KEY_INVALID")
    if not require_service_role and not (service_valid or anon_valid):
        return status(False, ANON_KEY_MESSAGE, "SUPABASE_ANON_KEY_INVALID")
    if not bucket_valid:
        return status(False, STORAGE_BUCKET_MESSAGE, "SUPABASE_STORAGE_BUCKET_INVALID")
    return status(True, "OK", "OK")


def supabase_error_response(message: str | None = None) -> tuple[dict, int]:
    env = validate_supabase_env(require_service_role=True)
    resolved_message = message or get_last_db_error() or env.message or CONNECTION_FAILED_MESSAGE
    return {
        "success": False,
        "message": resolved_message,
        "error": "Supabase unavailable",
        "error_code": env.error_code if not env.success else "SUPABASE_CONNECTION_FAILED",
        "diagnostics": {
            "supabase_url_configured": env.supabase_url_configured,
            "supabase_url_valid": env.supabase_url_valid,
            "service_role_key_configured": env.service_role_key_configured,
            "service_role_key_valid": env.service_role_key_valid,
            "anon_key_configured": env.anon_key_configured,
            "anon_key_valid": env.anon_key_valid,
            "storage_bucket": env.storage_bucket,
            "storage_bucket_valid": env.storage_bucket_valid,
        },
    }, 503


def _client_with_key(key: str, key_name: str):
    global _last_error
    url = os.getenv("SUPABASE_URL", "").strip().strip("/")

    if not create_client or not Client:
        _last_error = "Package supabase belum terinstall"
        logger.warning(_last_error)
        return None
    if not url:
        _last_error = "SUPABASE_URL is not configured"
        logger.warning(_last_error)
        return None
    if not key:
        _last_error = f"{key_name} is not configured"
        logger.warning(_last_error)
        return None

    if _is_placeholder(key):
        _last_error = INVALID_KEY_MESSAGE if "SERVICE_ROLE" in key_name else "Invalid Supabase API key"
        logger.warning(_last_error)
        return None

    if _is_cli_secret(key):
        _last_error = f"Invalid {key_name} format. Detected Supabase CLI Secret (sb_secret_...) instead of a JWT. Please use the 'service_role' (secret) or 'anon' (public) key from Supabase Dashboard -> Settings -> API."
        logger.error(_last_error)
        return None
    if "SERVICE_ROLE" in key_name and _jwt_role(key) != "service_role":
        _last_error = SERVICE_ROLE_JWT_MESSAGE
        logger.error(_last_error)
        return None
    if "ANON" in key_name and (not _is_jwt(key) or _jwt_role(key) == "service_role"):
        _last_error = ANON_KEY_MESSAGE
        logger.error(_last_error)
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        error_msg = str(e)
        logger.warning("Supabase standard client creation failed; trying fallback: %s", error_msg)
        try:
            return Client(url, key)
        except Exception as e2:
            fallback_error = str(e2)
            if _is_invalid_key_error(f"{error_msg} {fallback_error}"):
                if _is_cli_secret(key):
                    _last_error = f"Invalid {key_name} format (CLI Secret detected). Use the Service Role JWT."
                else:
                    _last_error = INVALID_KEY_MESSAGE if "SERVICE_ROLE" in key_name else "Invalid Supabase API key"
            else:
                _last_error = f"{error_msg} | Fallback failed: {fallback_error}"
            logger.error("Supabase creation failed: %s", _last_error)
            return None


def get_client():
    """Get or initialize the Supabase client singleton."""
    global _client, _failed, _last_error

    if _client is not None:
        return _client
    env = validate_supabase_env(require_service_role=False)
    if not env.success:
        _last_error = env.message
        return None
    if env.service_role_key_valid:
        _client = _client_with_key(_service_key(), "SUPABASE_SERVICE_ROLE_KEY")
    else:
        _client = _client_with_key(_anon_key(), "SUPABASE_ANON_KEY")
    return _client


def get_supabase_client():
    """Backward-compatible alias for backend DB client."""
    return get_client()


def get_supabase_public_client():
    """Public Supabase client using anon key only."""
    global _client, _last_error
    if _client is not None:
        return _client
    env = validate_supabase_env(require_service_role=False)
    if not env.success or not env.anon_key_valid:
        _last_error = env.message if not env.success else ANON_KEY_MESSAGE
        return None
    _client = _client_with_key(_anon_key(), "SUPABASE_ANON_KEY")
    return _client


def get_supabase_admin_client():
    """Privileged Supabase client for backend-only writes and Storage upload."""
    global _admin_client, _last_error
    if _admin_client is not None:
        return _admin_client
    env = validate_supabase_env(require_service_role=True)
    if not env.success:
        _last_error = env.message
        logger.warning(_last_error)
        return None
    key = _service_key()
    if not key:
        _last_error = "Supabase service role key is not configured"
        logger.warning(_last_error)
        return None
    _admin_client = _client_with_key(key, "SUPABASE_SERVICE_ROLE_KEY")
    return _admin_client


def validate_supabase_connection() -> dict:
    """Validate env, schema reachability, and evidence storage bucket."""
    env = validate_supabase_env(require_service_role=True)
    base = {
        "supabase_url_configured": env.supabase_url_configured,
        "supabase_url_valid": env.supabase_url_valid,
        "service_role_key_configured": env.service_role_key_configured,
        "service_role_key_valid": env.service_role_key_valid,
        "anon_key_configured": env.anon_key_configured,
        "anon_key_valid": env.anon_key_valid,
        "storage_bucket": env.storage_bucket,
        "storage_bucket_valid": env.storage_bucket_valid,
        "checks": {
            "env": {"success": env.success, "message": env.message, "error_code": env.error_code},
            "database": {"success": False, "message": "Not checked"},
            "schema": {"success": False, "message": "Not checked"},
            "storage": {"success": False, "message": "Not checked"},
        },
    }
    if not env.success:
        return {"success": False, "message": env.message, "error_code": env.error_code, **base}
    client = get_supabase_admin_client()
    if not client:
        message = get_last_db_error() or CONNECTION_FAILED_MESSAGE
        if "Invalid Supabase API key" in message:
            message = "Invalid Supabase API key"
        base["checks"]["database"] = {"success": False, "message": message}
        return {"success": False, "message": message, "error_code": "SUPABASE_CLIENT_INIT_FAILED", **base}
    try:
        client.table("facility_rooms").select("id").limit(1).execute()
        base["checks"]["database"] = {"success": True, "message": "Supabase REST connection OK"}
        base["checks"]["schema"] = {"success": True, "message": "Required table facility_rooms is reachable"}
    except Exception as exc:
        error_text = str(exc)
        if _is_invalid_key_error(error_text):
            message = INVALID_KEY_MESSAGE
            if _is_cli_secret(_service_key()):
                message = "Invalid Supabase API key format (CLI Secret detected). Use the Service Role JWT from Supabase Dashboard."
        else:
            message = f"Supabase connection failed: {error_text}"
        base["checks"]["database"] = {"success": False, "message": message}
        base["checks"]["schema"] = {
            "success": False,
            "message": "Could not verify facility_rooms schema because database check failed",
        }
        return {"success": False, "message": message, "error_code": "SUPABASE_DATABASE_OR_SCHEMA_FAILED", **base}

    storage_check = _validate_storage_bucket(client, env.storage_bucket)
    base["checks"]["storage"] = storage_check
    if not storage_check["success"]:
        return {
            "success": False,
            "message": storage_check["message"],
            "error_code": storage_check.get("error_code", "SUPABASE_STORAGE_BUCKET_FAILED"),
            "connection": "partial",
            **base,
        }
    return {"success": True, "message": "Supabase connection OK", "connection": "ok", "error_code": "OK", **base}


def _validate_storage_bucket(client, bucket: str) -> dict:
    if not _is_valid_bucket_name(bucket):
        return {"success": False, "message": STORAGE_BUCKET_MESSAGE, "error_code": "SUPABASE_STORAGE_BUCKET_INVALID"}
    storage = getattr(client, "storage", None)
    if storage is None:
        return {
            "success": False,
            "message": "Supabase storage client is unavailable",
            "error_code": "SUPABASE_STORAGE_CLIENT_UNAVAILABLE",
        }
    try:
        if hasattr(storage, "get_bucket"):
            storage.get_bucket(bucket)
            return {"success": True, "message": f"Storage bucket '{bucket}' is reachable"}
        if hasattr(storage, "list_buckets"):
            buckets = storage.list_buckets()
            names = []
            for item in buckets or []:
                if isinstance(item, dict):
                    names.append(item.get("name") or item.get("id"))
                else:
                    names.append(getattr(item, "name", None) or getattr(item, "id", None))
            if bucket in names:
                return {"success": True, "message": f"Storage bucket '{bucket}' exists"}
            return {
                "success": False,
                "message": f"Storage bucket '{bucket}' was not found",
                "error_code": "SUPABASE_STORAGE_BUCKET_NOT_FOUND",
            }
        if hasattr(storage, "from_"):
            storage.from_(bucket)
            return {"success": True, "message": f"Storage bucket '{bucket}' client can be created"}
    except Exception as exc:
        text = str(exc)
        not_found = "not found" in text.lower() or "does not exist" in text.lower()
        return {
            "success": False,
            "message": f"Storage bucket '{bucket}' check failed: {text}",
            "error_code": "SUPABASE_STORAGE_BUCKET_NOT_FOUND" if not_found else "SUPABASE_STORAGE_BUCKET_FAILED",
        }
    return {
        "success": False,
        "message": "Supabase storage bucket could not be verified",
        "error_code": "SUPABASE_STORAGE_BUCKET_UNVERIFIED",
    }


def get_last_db_error():
    """Return the last encountered database error message."""
    global _last_error
    return _last_error


def reset_client():
    """Reset the singleton instance (useful for testing or reconnecting)."""
    global _client, _admin_client, _failed
    _client = None
    _admin_client = None
    _failed = False


# PostgREST control parameters that are NOT column filters.
_POSTGREST_CONTROL_PARAMS = frozenset(
    {
        "select",
        "order",
        "limit",
        "offset",
        "on_conflict",
    }
)

# Allowed characters for PostgREST column/key names (letters, digits, underscore, dot for joins).
_SAFE_KEY_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.()]*$")

# Allowed characters for table names.
_SAFE_TABLE_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Allowed PostgREST operators, for example eq, gte, lte, in, is, ilike.
_SAFE_OPERATOR_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def _sanitize_postgrest_filters(raw_filters: str) -> str:
    """Parse and re-encode a PostgREST query string to prevent injection.

    Each ``&``-separated segment is validated:
    - The key (column name or control param) must match ``[a-zA-Z_][a-zA-Z0-9_.()]*``.
    - Filter *values* (the part after ``=eq.``, ``=gte.`` etc.) are URL-encoded so
      that user-supplied data can never break out of the value position.
    - Control params (``select``, ``order``, ``limit``, ``offset``, ``on_conflict``)
      are passed through after key validation.
    - Segments containing fragment identifiers (``#``) or semicolons are rejected.
    """
    if not raw_filters:
        return ""
    # Reject obvious injection attempts early.
    if "#" in raw_filters or ";" in raw_filters:
        raise ValueError("Illegal characters in query filter")

    safe_parts: list[str] = []
    for segment in raw_filters.split("&"):
        if not segment:
            continue
        eq_pos = segment.find("=")
        if eq_pos == -1:
            # Bare key with no value - skip silently.
            continue
        key = segment[:eq_pos]
        value = segment[eq_pos + 1 :]

        if not _SAFE_KEY_RE.match(key):
            raise ValueError(f"Unsafe filter key rejected: {key!r}")

        if key in _POSTGREST_CONTROL_PARAMS:
            # Control params: encode the value but keep the key verbatim.
            safe_parts.append(f"{key}={quote(unquote(value), safe='*,.:()!-')}")
        else:
            # Column filter - value has the form ``operator.actual_value``.
            dot_pos = value.find(".")
            if dot_pos == -1:
                # Operator-less value (unusual but harmless).
                safe_parts.append(f"{key}={quote(unquote(value), safe='')}")
            else:
                operator = value[:dot_pos]
                actual_value = value[dot_pos + 1 :]
                if not _SAFE_OPERATOR_RE.match(operator):
                    raise ValueError(f"Unsafe filter operator rejected: {operator!r}")
                safe_parts.append(f"{key}={operator}.{quote(unquote(actual_value), safe=',():-:+T')}")
    return "&".join(safe_parts)


def direct_db_query(table: str, method: str = "GET", payload: dict = None, filters: str = ""):
    """Perform a direct HTTP query to Supabase (bypass library validation).

    Parameters
    ----------
    table : str
        PostgREST table name - validated to contain only safe characters.
    method : str
        HTTP method (GET, POST, PATCH, DELETE).
    payload : dict | None
        JSON body for POST/PATCH requests.
    filters : str
        Raw PostgREST query string. Each segment is sanitized and values
        are URL-encoded before being appended to the URL.
    """
    import json
    from urllib import error, request

    # --- Validate table name ---
    if not _SAFE_TABLE_RE.match(table):
        raise ValueError(f"Invalid table name: {table!r}")

    url = os.getenv("SUPABASE_URL", "").strip().strip("/")
    key = _supabase_key()
    env = validate_supabase_env(require_service_role=True)
    if not env.success:
        raise ValueError(env.message)

    api_url = f"{url}/rest/v1/{table}"
    if filters:
        api_url += f"?{_sanitize_postgrest_filters(filters)}"

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    data = json.dumps(payload).encode() if payload else None
    req = request.Request(api_url, headers=headers, data=data, method=method)

    try:
        with request.urlopen(req) as response:  # nosec B310
            res_body = response.read().decode()
            return json.loads(res_body) if res_body else []
    except error.HTTPError as e:
        err_msg = e.read().decode()
        logger.error("Direct DB Error: %s - %s", e.code, err_msg)
        raise ValueError(f"Database Error: {err_msg}")
    except Exception as e:
        logger.error("Direct DB Generic Error: %s", e)
        raise ValueError(f"Koneksi Database Gagal: {str(e)}")
