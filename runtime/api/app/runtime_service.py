from __future__ import annotations

import os
from dataclasses import dataclass
from threading import Lock

from .compiler import SkillCompiler
from .config import Settings, get_settings
from .repository import RuntimeRepository
from .storage import ParquetStore, build_store


@dataclass
class RuntimeService:
    settings: Settings
    store: ParquetStore
    compiler: SkillCompiler
    repository: RuntimeRepository

    def initialize(self) -> None:
        # Skip initialization for dev testing if SKILL_RUNTIME_SKIP_INIT is set
        if os.getenv("SKILL_RUNTIME_SKIP_INIT", "").lower() in {"1", "true", "yes"}:
            return
        if self.settings.auto_compile or not self.store.exists("identity.skill_registry"):
            self.compiler.compile()
        self.repository.seed_defaults()

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "repo_root": str(self.settings.repo_root),
            "skill_source_dir": str(self.settings.skill_source_dir),
            "identity_source_dir": str(self.settings.identity_source_dir),
            "data_dir": str(self.settings.data_dir),
            "storage_backend": self.settings.storage_backend,
            "database_url": self.settings.database_url if self.settings.storage_backend in {"sql", "database", "db"} else "",
            "databricks_host": self.settings.databricks_host,
            "databricks_app_url": self.settings.databricks_app_url,
            "mcp_http_path": "/mcp",
            "shared_scope": "company-shared",
        }


_runtime_service: RuntimeService | None = None
_runtime_lock = Lock()


def get_runtime_service() -> RuntimeService:
    global _runtime_service

    if _runtime_service is not None:
        return _runtime_service

    with _runtime_lock:
        if _runtime_service is None:
            settings = get_settings()
            store = build_store(settings)
            compiler = SkillCompiler(settings, store)
            repository = RuntimeRepository(settings, store)
            service = RuntimeService(
                settings=settings,
                store=store,
                compiler=compiler,
                repository=repository,
            )
            service.initialize()
            _runtime_service = service

    return _runtime_service
