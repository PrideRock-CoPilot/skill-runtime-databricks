Use the company Skill Runtime MCP server for non-trivial work.

Required operating contract:

1. Route the request with `route_skill_request`.
2. Load the recommended gate with `load_skill_context`.
3. Activate the chosen worker with `activate_skill`.
4. Load `list_memory_triggers` and follow `.codex/instructions/chat-execution-contract.md`.
5. Answer inside that worker's scope, evidence rules, and handoff rules.
6. Use visible Markdown structure for non-trivial turns:
   - `## Todo`
   - `## Skill Activation`
   - `## Security Warning` when relevant
   - `## Result` or `## Next Step`
7. If the worker hands off, retries, or changes plan, write a visible event with `record_skill_event`.
8. After producing a substantial response, call `score_response_alignment`.
9. When the user says "yes correct" or "no wrong", call `record_skill_feedback`.

Do not skip activation and answer as a generic assistant when the task is non-trivial.

Use shared skills before inventing new ones. The company runtime is the primary skill registry and shared memory surface.
Do not suggest bypassing Databricks, Unity Catalog, storage, or corporate security controls. Warn before governed writes.
