from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP


def register_mcp_resources(
    mcp: FastMCP,
    *,
    service_getter: Callable[[], Any],
    skill_detail: Callable[[str, int], dict[str, object]],
) -> None:
    @mcp.resource("skill://registry", mime_type="application/json", name="skill-registry")
    def skill_registry_resource() -> str:
        return json.dumps(service_getter().repository.list_skills(), indent=2)

    @mcp.resource("skill://activation-contract", mime_type="application/json", name="activation-contract")
    def activation_contract_resource() -> str:
        contract = {
            "required_flow": [
                "route_skill_request → returns action directive",
                "follow action: activate → load_skill_context + activate_skill",
                "follow action: auto-build → activate build_skill_id, create_skill, activate it",
                "follow action: trivial-bypass → answer directly",
                "answer within the active worker contract",
                "record_skill_outcome(type='event') for handoffs or retries",
                "record_skill_outcome(type='alignment') after substantial responses",
            ],
            "directive_fields": {
                "action": "activate | auto-build | trivial-bypass",
                "next_step": "explicit instruction — follow as a directive",
                "build_skill_id": "skill to activate when action is auto-build",
            },
            "goal": "The server decides what to do. The model follows the action and next_step directives.",
        }
        return json.dumps(contract, indent=2)

    @mcp.resource("skill://memory-triggers", mime_type="application/json", name="memory-triggers")
    def memory_triggers_resource() -> str:
        return json.dumps(service_getter().repository.list_memory_triggers(limit=50), indent=2)

    @mcp.resource("skill://chat-execution-contract", mime_type="application/json", name="chat-execution-contract")
    def chat_execution_contract_resource() -> str:
        contract = {
            "required_sections_for_non_trivial_turns": ["## Todo", "## Skill Activation", "## Security Warning (only when relevant)", "## Next Step or Result"],
            "format_rules": [
                "Use Markdown headers instead of plain prose blobs.",
                "Announce newly activated skills by name and reason.",
                "Keep todo items visible and short.",
                "When a guarded write may hit policy, warn before attempting it.",
                "Do not suggest bypassing corporate security or transport controls.",
            ],
            "databricks_guardrail": "Before writing files, tables, or governed storage in Databricks-like environments, surface a security warning and stop if the platform denies the action.",
        }
        return json.dumps(contract, indent=2)

    @mcp.resource("skill://{skill_id}/gate/{gate_level}", mime_type="application/json", name="skill-gate")
    def skill_gate_resource(skill_id: str, gate_level: str) -> str:
        return json.dumps(skill_detail(skill_id, int(gate_level)), indent=2)