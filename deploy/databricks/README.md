# Databricks and Genie Code Setup

This runtime is packaged so one Databricks App can expose:

- the human web app
- the REST API
- the custom MCP endpoint at `/mcp`

## Deployment Shape

1. Deploy this repo as a Databricks App in the same workspace as Genie Code.
2. Set `SKILL_RUNTIME_DATA_DIR` to shared storage before production use.
3. Point Genie Code and approved IDE clients at `https://<your-app-url>/mcp`.
4. Load the workspace instruction template so Genie Code routes, activates, and scores alignment on non-trivial work.

## Fastest Way To Try It Now

Generate the Genie-side files locally:

```powershell
.runtime\.venv\Scripts\python.exe scripts\bootstrap_genie_runtime.py --force
```

That writes a Databricks-like layout under `.runtime/genie-bootstrap/` with:

- `Workspace/.assistant_workspace_instructions.md`
- `Users/<user>/.assistant_instructions.md`
- `Users/<user>/.assistant/skills/company-runtime-bridge/SKILL.md`
- `Users/<user>/company-skill-runtime.mcp.json`

## Shared Storage

The runtime writes Parquet files under `SKILL_RUNTIME_DATA_DIR`.

For local testing, `app.yaml` uses `/tmp/skill-runtime-data`.

For company-wide shared skills and memories, replace that with a shared path such as a Unity Catalog volume or another durable shared mount. The important rule is:

- shared runtime data must be durable
- all users must hit the same backend storage
- user/project separation must come from table fields, not separate app deployments

## Current Tool Surface

The MCP server stays under the Genie Code limit by exposing a compact tool set for:

- routing
- gated loading
- activation
- parking
- alignment scoring
- feedback
- project tracking

## Auth Note

This local slice is ready for hosted deployment shape, but it does not yet enforce Databricks user authorization in code. For production, wire Databricks App auth so:

- shared system writes can use app identity where appropriate
- user-scoped actions can honor forwarded user identity and scopes

The current backend already stores `user_id`, `project_id`, and `client_type` on runtime events, so the storage model is ready for that next hardening step.
