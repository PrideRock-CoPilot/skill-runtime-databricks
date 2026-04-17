from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from runtime.api.app.mcp_management_tools import register_management_tools
from runtime.api.app.mcp_resources import register_mcp_resources
from runtime.api.app.mcp_skill_tools import register_skill_tools

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

from runtime.api.app.models import SkillDetailResponse
from runtime.api.app.runtime_service import get_runtime_service


def _service():
    return get_runtime_service()


# Per-session identity context store ----------------------------------------
_session_contexts: dict[str, dict[str, str]] = {}


def _default_session_id(session_id: str = "") -> str:
    return session_id or _service().settings.default_session_id


def _default_user_id(user_id: str = "", *, _sid: str = "") -> str:
    if user_id:
        return user_id
    if _sid:
        stored = _session_contexts.get(_sid, {})
        if stored.get("user_id"):
            return stored["user_id"]
    return _service().settings.default_user_id


def _public_hosts() -> tuple[list[str], list[str]]:
    hosts = [
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
    ]
    origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
    ]
    for candidate in (_service().settings.databricks_host, _service().settings.databricks_app_url):
        if not candidate:
            continue
        parsed = urlparse(candidate)
        hostname = parsed.netloc or parsed.path
        if not hostname:
            continue
        if hostname not in hosts:
            hosts.append(hostname)
        if candidate not in origins:
            origins.append(candidate)
    return hosts, origins


def _transport_security() -> TransportSecuritySettings:
    strict_transport = os.getenv("SKILL_RUNTIME_MCP_STRICT_TRANSPORT", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not strict_transport:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"],
        )

    hosts, origins = _public_hosts()
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


@asynccontextmanager
async def mcp_lifespan(_: FastMCP):
    _service()
    yield


def _skill_detail(skill_id: str, gate_level: int) -> dict[str, object]:
    service = _service()
    skill = service.repository.get_skill(skill_id)
    if not skill:
        raise ValueError(f"Unknown skill: {skill_id}")
    bundles = service.repository.load_skill_bundles(skill_id, gate_level)
    response = SkillDetailResponse(
        skill=skill,
        requested_gate=gate_level,
        loaded_gates=sorted({bundle["gate_level"] for bundle in bundles}),
        bundles=bundles,
    )
    return response.model_dump()


def _register_tools(mcp: FastMCP) -> FastMCP:  # noqa: C901
    register_skill_tools(
        mcp,
        service_getter=_service,
        default_session_id=_default_session_id,
        default_user_id=_default_user_id,
        skill_detail=_skill_detail,
        session_contexts=_session_contexts,
    )
    register_management_tools(
        mcp,
        service_getter=_service,
        default_session_id=_default_session_id,
        default_user_id=_default_user_id,
    )
    register_mcp_resources(mcp, service_getter=_service, skill_detail=_skill_detail)

    return mcp


def create_mcp_server(
    *,
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str = "/mcp",
    stateless_http: bool = False,
) -> FastMCP:
    instructions = (
        "This server is the centralized company skill runtime for Genie Code and internal IDEs. "
        "Before answering non-trivial requests, route the request, load the gate bundle, activate the skill, "
        "then keep events and alignment visible. Use the chat execution contract with Todo, Skill Activation, "
        "and Security Warning sections when relevant. Treat Markdown and identity folders as authoring sources of truth, "
        "and treat this MCP server as the runtime control plane."
    )
    server = FastMCP(
        name="Skill Runtime MCP",
        instructions=instructions,
        host=host or os.getenv("SKILL_RUNTIME_MCP_HOST", "127.0.0.1"),
        port=port or int(os.getenv("SKILL_RUNTIME_MCP_PORT", "8001")),
        streamable_http_path=streamable_http_path,
        json_response=True,
        stateless_http=stateless_http,
        log_level=os.getenv("SKILL_RUNTIME_MCP_LOG_LEVEL", "INFO"),
        transport_security=_transport_security(),
        lifespan=mcp_lifespan,
    )
    return _register_tools(server)


def main() -> None:
    transport = os.getenv("SKILL_RUNTIME_MCP_TRANSPORT", "stdio")
    server = create_mcp_server(
        streamable_http_path=os.getenv("SKILL_RUNTIME_MCP_HTTP_PATH", "/mcp"),
        stateless_http=os.getenv("SKILL_RUNTIME_MCP_STATELESS", "false").lower() in {"1", "true", "yes", "on"},
    )
    server.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
