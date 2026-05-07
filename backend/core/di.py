"""
Simple DI container for the backend.
This is intentionally lightweight; it supports registering
providers (callables) or concrete instances and resolving them.
"""
from typing import Any, Callable, Dict

_CONTAINER: Dict[str, Any] = {}


def register(name: str, provider: Any) -> None:
    """Register a provider or instance under `name`.

    If `provider` is callable it will be called when `resolve` is invoked.
    """
    _CONTAINER[name] = provider


def resolve(name: str, default: Any = None) -> Any:
    """Resolve a dependency by name.

    Returns `default` when not found.
    """
    provider = _CONTAINER.get(name)
    if provider is None:
        return default
    try:
        if callable(provider):
            return provider()
    except Exception:
        # If provider is a callable that raises, return it directly
        pass
    return provider


def clear() -> None:
    _CONTAINER.clear()
