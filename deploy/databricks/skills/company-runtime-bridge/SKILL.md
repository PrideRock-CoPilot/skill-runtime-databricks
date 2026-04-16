---
name: company-runtime-bridge
description: Use the company Skill Runtime MCP server as the first stop for non-trivial work. Route the task, load the gated worker context, activate the worker, record events, score alignment, and write feedback so skills and memories stay centralized instead of fragmenting per user.
---

# Company Runtime Bridge

Use this skill when the request is non-trivial and the company Skill Runtime MCP server is available.

## Required flow

1. `route_skill_request`
2. `load_skill_context`
3. `activate_skill`
4. answer within the active worker contract
5. `record_skill_event` when the worker retries, hands off, or changes course
6. `score_response_alignment`
7. `record_skill_feedback` when the user confirms or rejects the result

## Rules

- Prefer the shared company skill registry over creating a new local skill.
- Prefer the shared company memory store over private ad hoc memory.
- Use the current user's private project lane for personal work tracking unless a shared project is explicitly requested.
- Do not treat tone alone as evidence that the correct worker is active. Activation and alignment must be visible.

## Do not use this skill when

- the request is trivial and one-shot
- the MCP server is unavailable
- the user explicitly asks to bypass the shared runtime
