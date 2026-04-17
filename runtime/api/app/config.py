from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _list_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    if not value.strip():
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    skill_source_dir: Path
    identity_source_dir: Path
    runtime_root: Path
    data_dir: Path
    default_session_id: str = "local-dev-session"
    default_user_id: str = "local.user@company.test"
    auto_compile: bool = True
    storage_backend: str = "parquet"
    database_url: str = ""
    databricks_host: str = ""
    databricks_app_url: str = ""
    allowed_web_origins: tuple[str, ...] = ()


def get_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[3]
    runtime_root = Path(os.getenv("SKILL_RUNTIME_ROOT", str(repo_root / ".runtime")))
    data_dir = Path(os.getenv("SKILL_RUNTIME_DATA_DIR", str(runtime_root / "data")))
    storage_backend = os.getenv("SKILL_RUNTIME_STORAGE_BACKEND", "parquet").strip().lower() or "parquet"
    default_database_url = f"sqlite:///{(data_dir / 'skill_runtime.db').as_posix()}"
    database_url = os.getenv("SKILL_RUNTIME_DATABASE_URL", default_database_url).strip()
    databricks_host = os.getenv("DATABRICKS_HOST", "").strip()
    databricks_app_url = os.getenv("DATABRICKS_APP_URL", "").strip()

    configured_origins = list(_list_env("SKILL_RUNTIME_ALLOWED_ORIGINS"))
    for origin in (databricks_host, databricks_app_url):
        if origin and origin not in configured_origins:
            configured_origins.append(origin)

    return Settings(
        repo_root=repo_root,
        skill_source_dir=repo_root / ".codex" / "skills",
        identity_source_dir=repo_root / "identity",
        runtime_root=runtime_root,
        data_dir=data_dir,
        default_session_id=os.getenv("SKILL_RUNTIME_DEFAULT_SESSION_ID", "local-dev-session"),
        default_user_id=os.getenv("SKILL_RUNTIME_DEFAULT_USER_ID", "local.user@company.test"),
        auto_compile=_bool_env("SKILL_RUNTIME_AUTO_COMPILE", True),
        storage_backend=storage_backend,
        database_url=database_url,
        databricks_host=databricks_host,
        databricks_app_url=databricks_app_url,
        allowed_web_origins=tuple(configured_origins),
    )
