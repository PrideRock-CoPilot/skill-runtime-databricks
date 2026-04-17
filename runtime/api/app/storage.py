from __future__ import annotations

import json
import os
import sqlite3
from threading import Lock
from pathlib import Path

import pandas as pd

from .config import Settings


class ParquetStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = Lock()
        self._ensure_writable_data_dir()

    def _ensure_writable_data_dir(self) -> None:
        configured_dir = self.settings.data_dir
        try:
            configured_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            fallback_dir = Path(os.getenv("SKILL_RUNTIME_FALLBACK_DATA_DIR", "/tmp/skill-runtime-data"))
            fallback_dir.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self.settings, "data_dir", fallback_dir)
            print(
                f"[storage] data dir '{configured_dir}' unavailable ({exc}); using '{fallback_dir}'",
                flush=True,
            )

    def _resolve_table_ref(self, table_ref: str) -> tuple[str, str]:
        if "." in table_ref:
            return tuple(table_ref.split(".", 1))  # type: ignore[return-value]
        return "runtime", table_ref

    def group_dir(self, group_name: str):
        group_path = self.settings.data_dir / group_name
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path

    def table_path(self, table_ref: str):
        group_name, table_name = self._resolve_table_ref(table_ref)
        return self.group_dir(group_name) / f"{table_name}.parquet"

    def json_path(self, group_name: str, file_name: str):
        return self.group_dir(group_name) / file_name

    def binary_path(self, group_name: str, relative_path: str | Path):
        path = self.group_dir(group_name) / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, table_ref: str) -> bool:
        return self.table_path(table_ref).exists()

    def read_table(self, table_ref: str) -> pd.DataFrame:
        path = self.table_path(table_ref)
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path)

    def write_table(self, table_ref: str, dataframe: pd.DataFrame) -> None:
        path = self.table_path(table_ref)
        tmp_path = path.with_suffix(".tmp.parquet")
        with self._lock:
            dataframe.to_parquet(tmp_path, index=False)
            tmp_path.replace(path)

    def write_json(self, group_name: str, file_name: str, payload: object) -> None:
        path = self.json_path(group_name, file_name)
        tmp_path = path.with_suffix(".tmp")
        with self._lock:
            tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_path.replace(path)

    def write_bytes(self, group_name: str, relative_path: str | Path, payload: bytes) -> Path:
        path = self.binary_path(group_name, relative_path)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        with self._lock:
            tmp_path.write_bytes(payload)
            tmp_path.replace(path)
        return path

    def read_bytes(self, group_name: str, relative_path: str | Path) -> bytes:
        return self.binary_path(group_name, relative_path).read_bytes()


class SqlTableStore(ParquetStore):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._db_path = self._resolve_sqlite_path(settings.database_url)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_sqlite_path(self, database_url: str) -> Path:
        normalized = database_url.strip()
        if normalized.startswith("sqlite:///"):
            target = normalized[len("sqlite:///") :]
        elif normalized.startswith("sqlite://"):
            target = normalized[len("sqlite://") :]
        else:
            target = normalized

        if not target:
            return self.settings.data_dir / "skill_runtime.db"

        path = Path(target)
        if not path.is_absolute():
            path = self.settings.repo_root / path
        return path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _table_name(self, table_ref: str) -> str:
        group_name, table_name = self._resolve_table_ref(table_ref)
        return f"{group_name}__{table_name}"

    def exists(self, table_ref: str) -> bool:
        table_name = self._table_name(table_ref)
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            )
            return cursor.fetchone() is not None

    def read_table(self, table_ref: str) -> pd.DataFrame:
        table_name = self._table_name(table_ref)
        if not self.exists(table_ref):
            return pd.DataFrame()
        with self._connect() as connection:
            return pd.read_sql_query(f'SELECT * FROM "{table_name}"', connection)

    def write_table(self, table_ref: str, dataframe: pd.DataFrame) -> None:
        table_name = self._table_name(table_ref)
        with self._lock:
            with self._connect() as connection:
                dataframe.to_sql(table_name, connection, index=False, if_exists="replace")


def build_store(settings: Settings) -> ParquetStore:
    backend = settings.storage_backend.strip().lower()
    if backend in {"sql", "database", "db"}:
        return SqlTableStore(settings)
    return ParquetStore(settings)
