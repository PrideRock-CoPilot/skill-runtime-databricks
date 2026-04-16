from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.api.app.compiler import SkillCompiler
from runtime.api.app.config import get_settings
from runtime.api.app.storage import ParquetStore


def main() -> None:
    settings = get_settings()
    store = ParquetStore(settings)
    compiler = SkillCompiler(settings, store)
    results = compiler.compile()
    print(
        f"Compiled {results['skills']} skills into {results['bundles']} gated bundles at "
        f"{settings.data_dir}"
    )


if __name__ == "__main__":
    main()
