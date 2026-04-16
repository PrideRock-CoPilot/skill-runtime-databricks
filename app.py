from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from runtime.api.app.main import app

_REPO_ROOT = Path(__file__).parent
_WEB_DIR = _REPO_ROOT / "runtime" / "web"
_DIST_DIR = _WEB_DIR / "dist"


def _build_web() -> None:
    """Build the React frontend if dist/ is absent.

    Databricks runtimes may not have Node/npm available by default; do not fail
    the process if the build cannot run. API + MCP should still start.
    """
    if _DIST_DIR.exists():
        return
    print("[app] dist/ not found — building frontend...", flush=True)
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        subprocess.run([npm, "install"], cwd=_WEB_DIR, check=True)
        subprocess.run([npm, "run", "build"], cwd=_WEB_DIR, check=True)
        print("[app] frontend build complete.", flush=True)
    except FileNotFoundError:
        print("[app] npm is not available; continuing without web UI build.", flush=True)
    except subprocess.CalledProcessError as exc:
        print(f"[app] frontend build failed ({exc}); continuing with API/MCP only.", flush=True)


def main() -> None:
    _build_web()
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=os.getenv("SKILL_RUNTIME_LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()
