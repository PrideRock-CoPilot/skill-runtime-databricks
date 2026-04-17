from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .databricks_auth import DatabricksAuthMiddleware
from .mcp_server import create_mcp_server
from .routes.memory import router as memory_router
from .routes.projects import router as projects_router
from .routes.quality import router as quality_router
from .routes.runtime import router as runtime_router
from .routes.sessions import router as sessions_router
from .routes.skills import router as skills_router
from .runtime_service import get_runtime_service
from .static_app import SinglePageApp

_mcp_server = create_mcp_server(
    streamable_http_path="/",
    stateless_http=os.getenv("SKILL_RUNTIME_MCP_STATELESS", "false").lower() in {"1", "true", "yes", "on"},
)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    current_runtime_service = get_runtime_service()
    fastapi_app.state.runtime_service = current_runtime_service
    fastapi_app.state.settings = current_runtime_service.settings
    fastapi_app.state.compiler = current_runtime_service.compiler
    fastapi_app.state.repository = current_runtime_service.repository
    async with _mcp_server.session_manager.run():
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="Skill Runtime API", version="0.2.0", lifespan=lifespan, redirect_slashes=False)
    runtime_service_instance = get_runtime_service()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime_service_instance.settings.allowed_web_origins),
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(DatabricksAuthMiddleware)

    @app.middleware("http")
    async def normalize_mcp_path(request, call_next):
        if request.scope["path"] == "/mcp":
            request.scope["path"] = "/mcp/"
        return await call_next(request)

    app.mount("/mcp", _mcp_server.streamable_http_app())

    app.include_router(runtime_router)
    app.include_router(skills_router)
    app.include_router(projects_router)
    app.include_router(memory_router)
    app.include_router(sessions_router)
    app.include_router(quality_router)

    web_dist_dir = runtime_service_instance.settings.repo_root / "runtime" / "web" / "dist"
    if web_dist_dir.exists():
        app.mount("/", SinglePageApp(directory=str(web_dist_dir), html=True), name="runtime-web")

    return app