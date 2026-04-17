from __future__ import annotations

from .repository import RuntimeRepository
from .runtime_service import RuntimeService, get_runtime_service


def runtime_service() -> RuntimeService:
    return get_runtime_service()


def repository() -> RuntimeRepository:
    return runtime_service().repository