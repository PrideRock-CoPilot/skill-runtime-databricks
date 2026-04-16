from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_ROOT = REPO_ROOT / "deploy" / "databricks"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Re-run with --force to overwrite.")
    path.write_text(content, encoding="utf-8")


def build_workspace_instructions(mcp_url: str) -> str:
    base = read_text(DEPLOY_ROOT / "genie-workspace-instructions.md").rstrip()
    return (
        f"{base}\n\n"
        "Runtime endpoint:\n\n"
        f"- MCP server URL: `{mcp_url}`\n"
    )


def build_user_instructions(mcp_url: str, user_id: str) -> str:
    base = read_text(DEPLOY_ROOT / "genie-user-instructions.md").rstrip()
    return (
        f"{base}\n\n"
        "Runtime endpoint:\n\n"
        f"- MCP server URL: `{mcp_url}`\n"
        f"- Runtime user id: `{user_id}`\n"
    )


def build_setup_guide(target_root: Path, user_id: str, mcp_url: str) -> str:
    return "\n".join(
        [
            "# Genie Code Local Bootstrap",
            "",
            "Generated files:",
            "",
            f"- Workspace instructions: `{(target_root / 'Workspace' / '.assistant_workspace_instructions.md').as_posix()}`",
            f"- User instructions: `{(target_root / 'Users' / user_id / '.assistant_instructions.md').as_posix()}`",
            f"- Bridge skill: `{(target_root / 'Users' / user_id / '.assistant' / 'skills' / 'company-runtime-bridge' / 'SKILL.md').as_posix()}`",
            f"- MCP config example: `{(target_root / 'Users' / user_id / 'company-skill-runtime.mcp.json').as_posix()}`",
            "",
            "Manual Genie Code steps:",
            "",
            "1. Open Genie Code settings in the target workspace.",
            "2. Add a custom MCP server that points to the URL below.",
            f"3. Use `{mcp_url}` as the MCP server URL.",
            "4. Apply the generated workspace instruction file at the workspace scope.",
            "5. Apply the generated user instruction file at the user scope.",
            "6. Add the generated bridge skill folder to the user's `.assistant/skills/` location if it is not already there.",
            "",
            "The bridge skill is intentionally thin. The real routing, memory, and activation behavior stays in the shared MCP runtime.",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Genie Code bootstrap files for the shared skill runtime.")
    parser.add_argument(
        "--target-root",
        default=str(REPO_ROOT / ".runtime" / "genie-bootstrap"),
        help="Directory where the Databricks-like Workspace/Users structure should be generated.",
    )
    parser.add_argument(
        "--user-id",
        default="local.user@company.test",
        help="User id to place under the generated Users/ tree.",
    )
    parser.add_argument(
        "--mcp-url",
        default="http://localhost:8000/mcp",
        help="MCP server URL to embed in the generated instructions.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite previously generated files.",
    )
    args = parser.parse_args()

    target_root = Path(args.target_root).resolve()
    user_id = args.user_id
    mcp_url = args.mcp_url

    workspace_instructions_path = target_root / "Workspace" / ".assistant_workspace_instructions.md"
    user_root = target_root / "Users" / user_id
    user_instructions_path = user_root / ".assistant_instructions.md"
    skill_path = user_root / ".assistant" / "skills" / "company-runtime-bridge" / "SKILL.md"
    mcp_config_path = user_root / "company-skill-runtime.mcp.json"
    setup_guide_path = target_root / "README.md"

    write_text(workspace_instructions_path, build_workspace_instructions(mcp_url), args.force)
    write_text(user_instructions_path, build_user_instructions(mcp_url, user_id), args.force)
    write_text(skill_path, read_text(DEPLOY_ROOT / "skills" / "company-runtime-bridge" / "SKILL.md"), args.force)
    write_text(
        mcp_config_path,
        json.dumps({"mcpServers": {"company-skill-runtime": {"url": mcp_url}}}, indent=2),
        args.force,
    )
    write_text(setup_guide_path, build_setup_guide(target_root, user_id, mcp_url), args.force)

    print(f"Generated Genie bootstrap under: {target_root}")
    print(f"Workspace instructions: {workspace_instructions_path}")
    print(f"User instructions: {user_instructions_path}")
    print(f"Bridge skill: {skill_path}")
    print(f"MCP config example: {mcp_config_path}")


if __name__ == "__main__":
    main()
