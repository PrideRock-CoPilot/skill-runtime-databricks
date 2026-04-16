# Skill Runtime for Databricks Apps

Clean, deploy-ready repository for running the Skill Runtime as a single Databricks App that serves:

- Web UI
- REST API
- MCP endpoint at `/mcp`

## What This Repo Contains

- `app.py`: entrypoint that starts the API and auto-builds the frontend when `runtime/web/dist` is missing.
- `app.yaml`: Databricks App command and environment variables.
- `runtime/api/`: FastAPI backend and MCP server surface.
- `runtime/web/`: React frontend source.
- `deploy/databricks/`: Genie Code templates and MCP config example.
- `scripts/bootstrap_genie_runtime.py`: generates workspace/user bootstrap files for Genie Code.

## Prerequisites

- Databricks CLI configured for your workspace.
- Workspace host: `https://dbc-e26a2f07-7a87.cloud.databricks.com`.
- App name: `orchestrator`.

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8000`.

## Deploy to Databricks App

Sync source:

```powershell
databricks sync --watch . /Workspace/Users/pliekhus@outlook.com/orchestrator
```

Deploy app:

```powershell
databricks apps deploy orchestrator --source-code-path /Workspace/Users/pliekhus@outlook.com/orchestrator
```

The deployed app URL is expected to be:

`https://orchestrator-7474657980342662.aws.databricksapps.com`

MCP endpoint:

`https://orchestrator-7474657980342662.aws.databricksapps.com/mcp`

## Genie Code Bootstrap

Generate workspace and user bootstrap files:

```powershell
.venv\Scripts\python.exe scripts\bootstrap_genie_runtime.py --force --user-id pliekhus@outlook.com --mcp-url https://orchestrator-7474657980342662.aws.databricksapps.com/mcp
```

Generated output:

- `.runtime/genie-bootstrap/Workspace/.assistant_workspace_instructions.md`
- `.runtime/genie-bootstrap/Users/pliekhus@outlook.com/.assistant_instructions.md`
- `.runtime/genie-bootstrap/Users/pliekhus@outlook.com/.assistant/skills/company-runtime-bridge/SKILL.md`
- `.runtime/genie-bootstrap/Users/pliekhus@outlook.com/company-skill-runtime.mcp.json`

## Source-Only Sync Policy

This repo uses `.databricksignore` to avoid syncing generated files and local artifacts:

- Python cache, virtual environments
- `runtime/web/node_modules`
- `runtime/web/dist`
- local runtime output (`.runtime`, `output`)
- editor and local tool folders

The frontend is built automatically at runtime by `app.py` if `dist` is missing.

## Repository Layout

```text
.
|-- app.py
|-- app.yaml
|-- databricks.yml
|-- requirements.txt
|-- deploy/
|   `-- databricks/
|-- scripts/
|   `-- bootstrap_genie_runtime.py
`-- runtime/
	|-- api/
	`-- web/
```
