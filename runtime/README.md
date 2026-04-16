# Skill Runtime MVP

This local prototype turns the existing `.codex/skills` packets and persona-first `identity/<worker>/...` folders into hidden machine-facing Parquet tables and exposes both:

- a browser app for humans
- an MCP server for agents

## What It Includes

- FastAPI backend for:
  - skill compilation into gated Parquet bundles
  - skill search and prompt routing
  - progressive gate loading
  - multi-user project separation with one shared company runtime
  - explicit skill activation and response-alignment scoring
  - parking-lot state for warm skills
  - feedback events
  - AI-native Kanban work items
- React frontend for:
  - routing prompts to likely specialists
  - browsing skills by human-facing name
  - loading more of a skill as task complexity grows
  - parking and resuming skills
  - moving work across a PM-style board
- MCP adapter for:
  - tool-first skill search, routing, and gated loading
  - parking-lot management
  - feedback capture
  - project board access
  - both `stdio` and Streamable HTTP transports

## Machine Storage

The machine-only data now lives under `.runtime/data/` with separate stores that mirror the examples you shared:

- `.runtime/data/identity/`
- `.runtime/data/board/`
- `.runtime/data/memory/`

Current runtime tables:

### Identity

- `skill_registry.parquet`
- `skill_identity.parquet`
- `job_posting.parquet`
- `skill_trait_profiles.parquet`
- `skill_version.parquet`
- `decision_log.parquet`
- `person_definition_checklist.parquet`
- `role_qualification_rules.parquet`

### Board

- `goals.parquet`
- `tasks.parquet`
- `task_transitions.parquet`
- `audit_log.parquet`
- `comments.parquet`
- `epic.parquet`
- `sprints.parquet`
- `sprint_tasks.parquet`

### Memory

- `analytics.parquet`
- `activations.parquet`
- `config.parquet`
- `decision.parquet`
- `memories.parquet`
- `route.parquet`
- `response_alignment.parquet`
- `sessions.parquet`
- `skill_events.parquet`
- `skills.parquet`
- `tags.parquet`
- `triggers.parquet`
- `pulse.json`
- `disabled.json`
- `disabled_payload.json`

Supported source shapes:

- `.codex/skills/<skill>/SKILL.md` packet format
- `identity/<worker>/metadata/*.md` plus `persona/*.md` persona-first format
- `identity/_templates/person-definition-checklist.csv`
- `identity/_templates/role-qualification-rules.csv`

## Local Run

### 1. Install backend dependencies

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_skill_runtime.ps1 -InstallDependencies
```

This creates a repo-local virtual environment at `.runtime/.venv` so the runtime and MCP server do not depend on global Python packages.

### 2. Compile the runtime tables

```powershell
.runtime\.venv\Scripts\python.exe scripts\compile_skill_runtime.py
```

### 3. Start the API

```powershell
.runtime\.venv\Scripts\python.exe -m uvicorn runtime.api.app.main:app --reload --app-dir .
```

### 4. Install frontend dependencies

```powershell
Set-Location runtime/web
npm install
```

### 5. Start the web app

```powershell
npm run dev
```

Then open `http://localhost:5173`.

### Shortcut

If you want both windows started for you:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_skill_runtime.ps1 -InstallDependencies
```

## MCP Server

The runtime now includes an MCP adapter in `runtime.api.app.mcp_server`.

### Local stdio transport

This is the easiest path for agent clients that support local MCP commands.

Command:

```powershell
E:\Skills\.runtime\.venv\Scripts\python.exe -m runtime.api.app.mcp_server
```

Recommended environment:

- `SKILL_RUNTIME_MCP_TRANSPORT=stdio`

Example client config shape:

```json
{
  "mcpServers": {
    "skill-runtime": {
      "command": "E:\\Skills\\.runtime\\.venv\\Scripts\\python.exe",
      "args": ["-m", "runtime.api.app.mcp_server"],
      "cwd": "E:\\Skills",
      "env": {
        "SKILL_RUNTIME_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Local Streamable HTTP transport

If you want a hosted-style local endpoint:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_skill_runtime_mcp.ps1 -InstallDependencies
```

Default endpoint:

```text
http://127.0.0.1:8001/mcp
```

You can change transport and port with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_skill_runtime_mcp.ps1 -Transport streamable-http -Port 8002
```

### Exposed MCP tools

- `runtime_health`
- `search_skills`
- `route_skill_request`
- `load_skill_context`
- `activate_skill`
- `get_active_skill`
- `list_parking_lot`
- `park_skill`
- `resume_skill`
- `record_skill_event`
- `score_response_alignment`
- `record_skill_feedback`
- `list_projects`
- `create_project`
- `list_work_items`
- `create_work_item`
- `update_work_item`
- `get_dashboard`
- `store_memory`
- `recall_memories`
- `list_memories`
- `update_memory`
- `archive_memory`

Resources:

- `skill://registry`
- `skill://activation-contract`
- `skill://{skill_id}/gate/{gate_level}`

## Recommended Architecture

Treat the system as three layers:

- Markdown and identity folders are the human authoring surface.
- Parquet is the hidden machine runtime.
- MCP is the agent-facing adapter.

For non-trivial discovery and delivery, use project memory deliberately:

- store confirmed requirements, decisions, assumptions, constraints, questions, and handoff context
- recall memory before asking the user to repeat information
- keep end-user escalation focused on critical business decisions

That keeps the end user away from Parquet, keeps skill authoring reviewable, and gives any agent one stable interface for routing and gated loading.

## Template Library

The runtime now includes a project-scoped template library for operator-managed source files such as STTM workbooks, branding packs, and reusable delivery documents.

The flow is:

- upload an approved template into the active project
- keep template metadata in the runtime store
- create a generated working copy from that template
- download either the original template or the generated document from the web app

Generated copies preserve the original file type and start from the stored template bytes, which makes the feature useful for spreadsheet-driven workflows without requiring a separate document system.

## Session History

The runtime now exposes end-user session visibility beyond the current thread.

The board UI and API can now:

- show the sessions connected to a user
- show which project each session belongs to
- open a unified history timeline for a selected session
- keep project-linked session history longer
- roll workspace-only ad hoc session history after 30 days

This makes it easier to answer "which conversations are tied to this user or project?" without forcing the operator to inspect raw Parquet tables.

## Memory Triggers And Chat Guidance

The MCP server now exposes runtime trigger guidance through `list_memory_triggers` and the `skill://memory-triggers` resource.

The trigger set covers:

- when to recall memory before asking follow-up questions
- when to store requirements, decisions, assumptions, and handoffs
- when to supersede outdated memories
- when to warn before governed writes

The server also exposes a `skill://chat-execution-contract` resource so MCP-guided agents can keep a visible `Todo`, announce `Skill Activation`, and surface `Security Warning` sections before guarded actions.

## Databricks and Genie Code

The repo now includes root-level `app.py`, `app.yaml`, and `requirements.txt` so the same codebase can be deployed as a Databricks App.

Important deployment notes:

- mount the MCP endpoint at `/mcp`
- keep the MCP transport stateless
- point `SKILL_RUNTIME_DATA_DIR` at shared durable storage before production use
- keep the app in the same workspace as Genie Code
- load the instruction templates in `deploy/databricks/`

Files added for that setup:

- `app.py`
- `app.yaml`
- `requirements.txt`
- `deploy/databricks/README.md`
- `deploy/databricks/genie-workspace-instructions.md`
- `deploy/databricks/genie-user-instructions.md`
- `deploy/databricks/mcp-server.example.json`
- `deploy/databricks/skills/company-runtime-bridge/SKILL.md`
- `scripts/bootstrap_genie_runtime.py`

## Genie Bootstrap

If you want this repo to generate the Genie-side files you need right now, run:

```powershell
.runtime\.venv\Scripts\python.exe scripts\bootstrap_genie_runtime.py --force
```

That generates a Databricks-like bootstrap tree under `.runtime/genie-bootstrap/` with:

- `Workspace/.assistant_workspace_instructions.md`
- `Users/<user>/.assistant_instructions.md`
- `Users/<user>/.assistant/skills/company-runtime-bridge/SKILL.md`
- `Users/<user>/company-skill-runtime.mcp.json`

Use that output as the handoff package for local testing or for copying into a real workspace/user layout.
