from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.api.app.compiler import SkillCompiler
from runtime.api.app.config import get_settings
from runtime.api.app.repository import RuntimeRepository
from runtime.api.app.storage import build_store
from runtime.api.app import tables as table_constants


def _collect_table_refs() -> list[str]:
    refs: list[str] = []
    for name in dir(table_constants):
        if not name.startswith("TABLE_"):
            continue
        value = getattr(table_constants, name)
        if isinstance(value, str):
            refs.append(value)
    return sorted(set(refs))


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy and initialize runtime storage tables")
    parser.add_argument("--backend", choices=["parquet", "sql"], help="Storage backend override")
    parser.add_argument("--database-url", help="Database URL for SQL backend")
    parser.add_argument("--skip-compile", action="store_true", help="Skip compiler execution")
    args = parser.parse_args()

    if args.backend:
        os.environ["SKILL_RUNTIME_STORAGE_BACKEND"] = args.backend
    if args.database_url:
        os.environ["SKILL_RUNTIME_DATABASE_URL"] = args.database_url

    settings = get_settings()
    store = build_store(settings)
    compiler = SkillCompiler(settings, store)
    repository = RuntimeRepository(settings, store)

    compile_result: dict[str, int] | None = None
    if not args.skip_compile:
        compile_result = compiler.compile()

    repository.seed_defaults()

    table_refs = _collect_table_refs()
    for table in table_refs:
        if not store.exists(table):
            store.write_table(table, pd.DataFrame(columns=["_placeholder"]))
    existing_count = sum(1 for table in table_refs if store.exists(table))

    print(f"storage_backend={settings.storage_backend}")
    if settings.storage_backend in {"sql", "database", "db"}:
        print(f"database_url={settings.database_url}")
    print(f"tables_initialized={existing_count}/{len(table_refs)}")
    if compile_result is not None:
        print(f"compiled_skills={compile_result['skills']}")
        print(f"compiled_bundles={compile_result['bundles']}")


if __name__ == "__main__":
    main()
