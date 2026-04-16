"""Databricks Apps authentication helpers.

Databricks Apps inject the authenticated user's OAuth token as the
``x-forwarded-access-token`` request header on every inbound request.
This module provides:
- A ``contextvars`` token store so any part of the app (including MCP
  tool handlers) can retrieve the current user's token without needing
  direct access to the HTTP request object.
- A FastAPI middleware that populates the store on every request.
- A FastAPI dependency that returns a ready-to-use ``WorkspaceClient``,
  falling back to SDK default credential chain (env vars / profile) when
  the header is absent (local dev).
"""
from __future__ import annotations

import os
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Context variable — populated per-request in DatabricksAuthMiddleware
# ---------------------------------------------------------------------------
_token_var: ContextVar[str] = ContextVar("databricks_forwarded_token", default="")


def get_forwarded_token() -> str:
    """Return the Databricks OAuth token forwarded by the Databricks App proxy.

    Returns an empty string when not running inside a Databricks App (e.g.
    local dev), in which case SDK credential chain picks up env vars.
    """
    return _token_var.get()


# ---------------------------------------------------------------------------
# Middleware — must be added to the FastAPI app before any route is mounted
# ---------------------------------------------------------------------------
class DatabricksAuthMiddleware(BaseHTTPMiddleware):
    """Populates the per-request token contextvar from the forwarded header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        token = request.headers.get("x-forwarded-access-token", "")
        _token_var_token = _token_var.set(token)
        try:
            return await call_next(request)
        finally:
            _token_var.reset(_token_var_token)


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a WorkspaceClient for the current user
# ---------------------------------------------------------------------------
def get_workspace_client():
    """FastAPI dependency that returns a ``WorkspaceClient`` for the current user.

    When running inside a Databricks App the forwarded access token is used
    (on-behalf-of-user auth).  Locally the SDK credential chain is used
    (``DATABRICKS_HOST`` + ``DATABRICKS_TOKEN`` env vars, ``~/.databrickscfg``
    profile, etc.).
    """
    try:
        from databricks.sdk import WorkspaceClient  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "databricks-sdk is required for Databricks auth. "
            "Run: pip install databricks-sdk"
        ) from exc

    host = os.getenv("DATABRICKS_HOST", "")
    token = get_forwarded_token()

    if token and host:
        return WorkspaceClient(host=host, token=token)

    # Fallback: SDK discovers credentials from environment / config file
    return WorkspaceClient()
