from __future__ import annotations

import json
import mimetypes
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .config import Settings
from .models import (
    ActivateSkillRequest,
    AddCommentRequest,
    AlignmentRequest,
    CreateGeneratedDocumentRequest,
    CreateProjectRequest,
    CreateSkillRequest,
    CreateSprintRequest,
    CreateWorkItemRequest,
    FeedbackRequest,
    ParkSkillRequest,
    ResumeSkillRequest,
    RouteResponse,
    SkillEventRequest,
    StoreMemoryRequest,
    UpdateMemoryRequest,
    UpdateWorkItemRequest,
    normalize_complexity_label,
)
from .storage import ParquetStore
from .tables import (
    TABLE_BOARD_AUDIT_LOG,
    TABLE_BOARD_COMMENTS,
    TABLE_BOARD_EPIC,
    TABLE_BOARD_GOALS,
    TABLE_BOARD_SPRINT_TASKS,
    TABLE_BOARD_SPRINTS,
    TABLE_BOARD_TASK_TRANSITIONS,
    TABLE_BOARD_TASKS,
    TABLE_BOARD_TEMPLATE_DOCUMENTS,
    TABLE_BOARD_TEMPLATES,
    TABLE_MEMORY_ACTIVATIONS,
    TABLE_MEMORY_ALIGNMENT,
    TABLE_MEMORY_ANALYTICS,
    TABLE_MEMORY_CONFIG,
    TABLE_MEMORY_DECISION,
    TABLE_MEMORY_EVENTS,
    TABLE_MEMORY_KNOWLEDGE,
    TABLE_MEMORY_MEMORIES,
    TABLE_MEMORY_ROUTE,
    TABLE_MEMORY_SESSIONS,
    TABLE_MEMORY_SKILLS,
    TABLE_MEMORY_TAGS,
    TABLE_MEMORY_TRIGGERS,
    TABLE_SKILL_IDENTITY,
    TABLE_SKILL_REGISTRY,
)


COMPLEXITY_TO_GATE = {
    "simple": 1,
    "standard": 2,
    "deep": 3,
    "expert": 4,
}

STAGE_ORDER = ["backlog", "discovery", "design", "build", "review", "done"]
SHARED_OWNER_ID = "company"
SHARED_PROJECT_ID = "company-shared-skill-system"
ORCHESTRATOR_SKILL_ID = "orchestrator"
HIRING_SKILL_ID = "TalentDirector"
MIN_SPECIALIST_MATCH_SCORE = 1.5
MIN_DOMAIN_COVERAGE = 0.25
MAX_TEMPLATE_FILE_BYTES = 25 * 1024 * 1024
WORKSPACE_HISTORY_RETENTION_DAYS = 30
DEFAULT_SESSION_HISTORY_LIMIT = 60

# Common words that inflate routing scores without signaling domain fit.
_ROUTING_STOP_WORDS = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "all", "can",
    "was", "one", "our", "out", "has", "had", "how", "its", "may",
    "new", "now", "see", "way", "who", "did", "get", "let", "say",
    "too", "use", "will", "with", "that", "this", "have", "from",
    "they", "been", "make", "like", "just", "know", "take", "come",
    "could", "than", "look", "only", "into", "over", "such", "some",
    "them", "then", "what", "when", "where", "which", "while",
    "about", "would", "there", "their", "should", "these", "other",
    "being", "does", "done", "each", "help", "must", "also", "more",
    "most", "very", "after", "before", "still", "here", "many",
    "well", "back", "much", "give", "keep", "need", "want", "skill",
})


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def parse_utc_timestamp(value: object) -> datetime | None:
    if value in ("", None):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def tokenize(text: str, *, filter_stops: bool = False) -> list[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    if filter_stops:
        tokens = [t for t in tokens if t not in _ROUTING_STOP_WORDS]
    return tokens


def safe_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "user"


class RuntimeRepository:
    def __init__(self, settings: Settings, store: ParquetStore) -> None:
        self.settings = settings
        self.store = store

    def list_skills(self, query: str = "") -> list[dict[str, object]]:
        skills = self.store.read_table(TABLE_SKILL_REGISTRY)
        if skills.empty:
            return []

        ranked = self._rank_skills(skills, query)
        return ranked.drop(columns=["search_text"], errors="ignore").to_dict(orient="records")

    def get_skill(self, skill_id: str) -> dict[str, object] | None:
        skills = self.store.read_table(TABLE_SKILL_REGISTRY)
        if skills.empty:
            return None
        match = skills.loc[skills["skill_id"] == skill_id]
        if match.empty:
            return None
        record = match.iloc[0].to_dict()
        record.pop("search_text", None)
        record.setdefault("search_score", 0)
        return record

    def load_skill_bundles(self, skill_id: str, gate_level: int) -> list[dict[str, object]]:
        bundles = self.store.read_table(TABLE_SKILL_IDENTITY)
        if bundles.empty:
            return []
        filtered = bundles.loc[
            (bundles["skill_id"] == skill_id) & (bundles["gate_level"] <= gate_level)
        ].sort_values(["gate_level", "sort_order"])
        return filtered.to_dict(orient="records")

    def upsert_skill(self, payload: CreateSkillRequest) -> dict[str, object]:
        """Register or update a skill in the runtime registry and add gate-0 bundles."""
        skill_id = payload.skill_id
        search_text = " ".join(
            [
                skill_id,
                payload.display_name,
                payload.description,
                payload.purpose,
                payload.use_when,
                payload.do_not_use_when,
            ]
        ).strip()

        skill_row: dict[str, object] = {
            "skill_id": skill_id,
            "slug": skill_id,
            "name": skill_id.replace("-", " ").title(),
            "display_name": payload.display_name,
            "description": payload.description,
            "packet_level": "runtime-created",
            "source_dir": "",
            "source_format": "mcp-tool",
            "search_text": search_text,
            "updated_at": utc_now(),
        }

        # Upsert in registry
        skills = self.store.read_table(TABLE_SKILL_REGISTRY)
        if not skills.empty and skill_id in skills["skill_id"].values:
            skills.loc[skills["skill_id"] == skill_id, list(skill_row.keys())] = list(skill_row.values())
            self.store.write_table(TABLE_SKILL_REGISTRY, skills)
        else:
            self._append_rows(TABLE_SKILL_REGISTRY, [skill_row])

        # Upsert gate-0 bundles so load_skill_context works
        bundles = self.store.read_table(TABLE_SKILL_IDENTITY)
        existing_bundles = bundles.loc[bundles["skill_id"] == skill_id] if not bundles.empty else pd.DataFrame()

        new_bundles: list[dict[str, object]] = []
        sort_order = 0

        def _add_bundle(title: str, content: str) -> None:
            nonlocal sort_order
            if not content.strip():
                return
            new_bundles.append(
                {
                    "bundle_id": str(uuid4()),
                    "skill_id": skill_id,
                    "gate_level": 0,
                    "gate_name": "router-summary",
                    "title": title,
                    "content": content.strip(),
                    "source_file": "",
                    "sort_order": sort_order,
                }
            )
            sort_order += 1

        _add_bundle("Description", payload.description)
        _add_bundle("Purpose", payload.purpose)
        _add_bundle("Use When", payload.use_when)
        _add_bundle("Do Not Use When", payload.do_not_use_when)
        _add_bundle("Personality", payload.personality)
        _add_bundle("Standards", payload.standards)
        _add_bundle("Handoffs", payload.handoffs)

        if new_bundles:
            # Remove old gate-0 bundles for this skill, then append new ones
            if not existing_bundles.empty:
                bundles = bundles.loc[
                    ~((bundles["skill_id"] == skill_id) & (bundles["gate_level"] == 0))
                ]
                self.store.write_table(TABLE_SKILL_IDENTITY, bundles)
            self._append_rows(TABLE_SKILL_IDENTITY, new_bundles)

        result = skill_row.copy()
        result.pop("search_text", None)
        result["bundles_created"] = len(new_bundles)
        return result

    def plan_project_skills(self, prompt: str) -> dict[str, object]:
        """Suggest domain-specific stakeholder skills needed for a project.

        Returns skill suggestions grouped by phase, plus which already exist
        in the registry so the caller knows what to create.
        """
        prompt_tokens = set(tokenize(prompt, filter_stops=True))

        # Standard project phases and the stakeholder roles each needs
        phase_roles = {
            "discovery": [
                {"role": "domain-owner", "purpose": "Business owner perspective — real constraints, priorities, what matters to daily operations"},
                {"role": "customer", "purpose": "End-user perspective — what buyers actually want, pain points, buying behavior"},
                {"role": "competitor-analyst", "purpose": "Market landscape — what alternatives exist, gaps, differentiation opportunities"},
            ],
            "requirements": [
                {"role": "business-analyst", "purpose": "Translate discovery into structured requirements, user stories, acceptance criteria"},
                {"role": "domain-expert", "purpose": "Subject-matter depth — industry standards, regulations, seasonal patterns, logistics"},
            ],
            "design": [
                {"role": "product-strategist", "purpose": "Feature prioritization, MVP scope, roadmap sequencing"},
                {"role": "ux-designer", "purpose": "User flows, wireframes, accessibility, mobile-first design"},
            ],
            "build": [
                {"role": "app-architect", "purpose": "Technical architecture, stack selection, integration patterns"},
                {"role": "app-builder", "purpose": "Implementation — frontend, backend, database, deployment"},
            ],
            "review": [
                {"role": "qa-tester", "purpose": "Test strategy, edge cases, acceptance validation"},
                {"role": "reviewer", "purpose": "Code review, UX review, stakeholder sign-off"},
            ],
        }

        # Determine domain prefix from the prompt
        domain_words = [t for t in prompt_tokens if len(t) > 3]
        domain_prefix = "-".join(domain_words[:2]) if domain_words else "project"

        # Check which of these already exist in the registry
        skills = self.store.read_table(TABLE_SKILL_REGISTRY)
        existing_ids = set(skills["skill_id"].tolist()) if not skills.empty else set()

        suggestions: list[dict[str, object]] = []
        existing_matches: list[str] = []

        for phase, roles in phase_roles.items():
            for role_info in roles:
                # Check both domain-prefixed and generic versions
                domain_skill_id = f"{domain_prefix}-{role_info['role']}"
                generic_skill_id = role_info["role"]

                if domain_skill_id in existing_ids:
                    existing_matches.append(domain_skill_id)
                elif generic_skill_id in existing_ids:
                    existing_matches.append(generic_skill_id)
                else:
                    suggestions.append({
                        "suggested_skill_id": domain_skill_id,
                        "role": role_info["role"],
                        "phase": phase,
                        "purpose": role_info["purpose"],
                        "exists": False,
                    })

        return {
            "domain_prefix": domain_prefix,
            "prompt": prompt,
            "total_suggested": len(suggestions) + len(existing_matches),
            "already_exist": existing_matches,
            "skills_to_create": suggestions,
            "next_step": (
                f"Create the skills listed in skills_to_create using create_skill. "
                f"Use the domain prefix '{domain_prefix}' for skill_ids. "
                f"Start with the discovery phase — create the domain-owner and customer skills first, "
                f"then activate the domain-owner to begin gathering requirements. "
                f"Create additional phase skills as the project progresses."
            ),
        }

    # ------------------------------------------------------------------
    # Knowledge memory (enterprise / user / project scopes)
    # ------------------------------------------------------------------

    def _visible_project_ids(self, user_id: str) -> set[str]:
        """Return project_ids the user can access (own + shared)."""
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        if projects.empty:
            return set()
        own = projects.loc[projects["user_id"] == user_id, "project_id"].tolist() if "user_id" in projects.columns else []
        shared = projects.loc[projects["visibility"] == "shared", "project_id"].tolist() if "visibility" in projects.columns else []
        return set(own) | set(shared)

    def _can_access_memory(self, row: dict, user_id: str, accessible_project_ids: set[str]) -> bool:
        """Check if a user can access a memory row based on scope."""
        scope = row.get("scope", "")
        if scope == "enterprise":
            return True
        if scope == "user":
            return row.get("user_id", "") == user_id
        if scope == "project":
            return row.get("project_id", "") in accessible_project_ids
        return False

    def _coerce_int(self, value: object, default: int = 0) -> int:
        try:
            if value in ("", None):
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _coerce_float(self, value: object, default: float = 0.0) -> float:
        try:
            if value in ("", None):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _coerce_bool(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _normalize_memory_category(self, category: str) -> str:
        value = (category or "note").strip().lower()
        return value or "note"

    def _normalize_memory_status(self, category: str, status: str = "") -> str:
        value = (status or "").strip().lower()
        if value:
            return value
        if category == "question":
            return "open"
        if category == "assumption":
            return "provisional"
        return "confirmed"

    def _default_memory_importance(self, category: str) -> int:
        return {
            "decision": 5,
            "constraint": 5,
            "requirement": 4,
            "handoff": 4,
            "preference": 3,
            "question": 3,
            "lesson": 3,
            "convention": 4,
            "assumption": 2,
            "note": 1,
        }.get(category, 2)

    def _default_memory_confidence(self, status: str) -> float:
        return {
            "confirmed": 0.95,
            "provisional": 0.6,
            "open": 0.35,
            "superseded": 0.1,
            "rejected": 0.0,
        }.get(status, 0.7)

    def _normalize_memory_source(self, source: str) -> str:
        value = (source or "").strip().lower()
        return value or "worker"

    def _normalize_memory_owner(self, owner: str, source: str) -> str:
        value = (owner or "").strip().lower()
        if value:
            return value
        if source == "user":
            return "end-user"
        if source == "system":
            return "system"
        return "shared"

    def _normalize_memory_tags(self, tags: str) -> str:
        seen: set[str] = set()
        normalized: list[str] = []
        for part in re.split(r"[,\n]+", tags or ""):
            raw = part.strip().lower()
            if not raw:
                continue
            token = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
            if token and token not in seen:
                normalized.append(token)
                seen.add(token)
        return ",".join(normalized)

    def _sync_memory_tags(self, tags: str, scope: str) -> None:
        normalized_tags = [tag for tag in self._normalize_memory_tags(tags).split(",") if tag]
        if not normalized_tags:
            return
        tags_df = self.store.read_table(TABLE_MEMORY_TAGS)
        if tags_df.empty:
            tags_df = pd.DataFrame(columns=["tag_id", "tag", "scope"])
        existing = {
            (str(row.get("tag", "")), str(row.get("scope", "")))
            for row in tags_df.to_dict(orient="records")
        }
        new_rows = []
        for tag in normalized_tags:
            key = (tag, scope)
            if key in existing:
                continue
            new_rows.append({"tag_id": str(uuid4()), "tag": tag, "scope": scope})
            existing.add(key)
        if new_rows:
            updated = pd.concat([tags_df, pd.DataFrame(new_rows)], ignore_index=True)
            self.store.write_table(TABLE_MEMORY_TAGS, updated)

    def _memory_category_weight(self, category: str) -> float:
        return {
            "decision": 3.0,
            "constraint": 3.0,
            "requirement": 2.5,
            "handoff": 2.0,
            "preference": 1.5,
            "question": 1.0,
            "assumption": 0.5,
            "lesson": 1.0,
            "convention": 1.5,
            "note": 0.0,
        }.get(category, 0.5)

    def _memory_status_weight(self, status: str) -> float:
        return {
            "confirmed": 3.0,
            "provisional": 1.0,
            "open": 0.0,
            "superseded": -4.0,
            "rejected": -6.0,
        }.get(status, 0.0)

    def _memory_recency_bonus(self, updated_at: object) -> float:
        try:
            if updated_at in ("", None):
                return 0.0
            updated_dt = datetime.fromisoformat(str(updated_at))
        except ValueError:
            return 0.0
        age_days = max((datetime.now(UTC) - updated_dt).days, 0)
        if age_days <= 7:
            return 2.0
        if age_days <= 30:
            return 1.0
        if age_days <= 90:
            return 0.5
        return 0.0

    def _memory_sort_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        sorted_df = df.copy()
        sorted_df["_pinned"] = sorted_df["pinned"].apply(self._coerce_bool)
        sorted_df["_importance"] = sorted_df.apply(
            lambda row: self._coerce_int(row.get("importance"), self._default_memory_importance(self._normalize_memory_category(str(row.get("category", ""))))),
            axis=1,
        )
        sorted_df["_access_count"] = sorted_df["access_count"].apply(lambda value: self._coerce_int(value, 0))
        return sorted_df.sort_values(
            ["_pinned", "_importance", "updated_at", "_access_count"],
            ascending=[False, False, False, False],
        )

    def _touch_memories(self, memory_ids: list[str]) -> None:
        if not memory_ids:
            return
        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if df.empty:
            return
        now = utc_now()
        changed = False
        for memory_id in memory_ids:
            mask = df["memory_id"] == memory_id
            if not mask.any():
                continue
            index = df.index[mask][0]
            current_count = self._coerce_int(df.at[index, "access_count"], 0)
            df.at[index, "access_count"] = current_count + 1
            df.at[index, "last_accessed_at"] = now
            changed = True
        if changed:
            self.store.write_table(TABLE_MEMORY_KNOWLEDGE, df)

    def _memory_match_score(self, row: dict[str, object], query_tokens: set[str], query_text: str) -> float:
        category = self._normalize_memory_category(str(row.get("category", "")))
        status = self._normalize_memory_status(category, str(row.get("status", "")))
        importance = self._coerce_int(row.get("importance"), self._default_memory_importance(category))
        confidence = self._coerce_float(row.get("confidence"), self._default_memory_confidence(status))
        subject = str(row.get("subject", "")).lower()
        content = str(row.get("content", "")).lower()
        tags = str(row.get("tags", "")).lower()
        score = 0.0
        text_hits = 0

        for token in query_tokens:
            if token in subject:
                score += 3.0
                text_hits += 1
            if token in tags:
                score += 2.0
                text_hits += 1
            if token in content:
                score += 1.0
                text_hits += 1

        if query_text and query_text in subject:
            score += 4.0
            text_hits += 1

        if query_tokens and text_hits == 0:
            return 0.0

        score += importance * 1.5
        score += confidence * 4.0
        score += self._memory_category_weight(category)
        score += self._memory_status_weight(status)
        score += self._memory_recency_bonus(row.get("updated_at"))
        score += min(self._coerce_int(row.get("access_count"), 0), 5) * 0.2
        if self._coerce_bool(row.get("pinned")):
            score += 4.0
        return score

    def store_memory(
        self,
        payload: StoreMemoryRequest,
        user_id: str = "",
        session_id: str = "",
    ) -> dict[str, object]:
        resolved_user = self._normalize_user_id(user_id)
        now = utc_now()

        if payload.scope == "project" and not payload.project_id:
            raise ValueError("project_id is required when scope is 'project'")

        category = self._normalize_memory_category(payload.category)
        status = self._normalize_memory_status(category, payload.status)
        importance = payload.importance or self._default_memory_importance(category)
        confidence = payload.confidence or self._default_memory_confidence(status)
        source = self._normalize_memory_source(payload.source)
        owner = self._normalize_memory_owner(payload.owner, source)
        tags = self._normalize_memory_tags(payload.tags)
        subject = payload.subject.strip()
        content = payload.content.strip()

        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if not df.empty:
            active = df.copy()
            if "archived" in active.columns:
                active = active.loc[active["archived"].astype(str).str.lower() != "true"]

            duplicate = active.loc[
                (active["scope"].fillna("") == payload.scope)
                & (active["user_id"].fillna("") == resolved_user)
                & (active["project_id"].fillna("") == payload.project_id)
                & (active["category"].fillna("").str.lower() == category)
                & (active["subject"].fillna("").str.strip() == subject)
                & (active["content"].fillna("").str.strip() == content)
                & (active["source"].fillna("").str.lower() == source)
            ]
            if not duplicate.empty:
                existing_id = str(duplicate.iloc[0]["memory_id"])
                mask = df["memory_id"] == existing_id
                df.loc[mask, "updated_at"] = now
                self.store.write_table(TABLE_MEMORY_KNOWLEDGE, df)
                return {
                    "memory_id": existing_id,
                    "scope": payload.scope,
                    "subject": subject,
                    "category": category,
                    "status": "already-stored",
                }

            if payload.supersedes_memory_id:
                superseded_mask = df["memory_id"] == payload.supersedes_memory_id
                if superseded_mask.any():
                    df.loc[superseded_mask, "status"] = "superseded"
                    df.loc[superseded_mask, "updated_at"] = now
                    self.store.write_table(TABLE_MEMORY_KNOWLEDGE, df)

        memory_id = str(uuid4())
        row = {
            "memory_id": memory_id,
            "scope": payload.scope,
            "user_id": resolved_user,
            "project_id": payload.project_id,
            "category": category,
            "subject": subject,
            "content": content,
            "skill_id": payload.skill_id,
            "session_id": session_id,
            "tags": tags,
            "status": status,
            "importance": importance,
            "confidence": confidence,
            "source": source,
            "owner": owner,
            "decision_scope": (payload.decision_scope or "").strip().lower(),
            "pinned": payload.pinned,
            "supersedes_memory_id": payload.supersedes_memory_id,
            "expires_at": payload.expires_at,
            "last_accessed_at": "",
            "access_count": 0,
            "created_at": now,
            "updated_at": now,
            "archived": False,
        }
        self._append_rows(TABLE_MEMORY_KNOWLEDGE, [row])
        self._sync_memory_tags(tags, payload.scope)
        return {
            "memory_id": memory_id,
            "scope": payload.scope,
            "subject": subject,
            "category": category,
            "status": "stored",
            "memory_status": status,
            "importance": importance,
            "confidence": confidence,
        }

    def recall_memories(
        self,
        query: str,
        scope: str = "",
        user_id: str = "",
        project_id: str = "",
        category: str = "",
        limit: int = 10,
    ) -> list[dict[str, object]]:
        resolved_user = self._normalize_user_id(user_id)
        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if df.empty:
            return []

        # Filter out archived
        if "archived" in df.columns:
            df = df.loc[df["archived"].astype(str).str.lower() != "true"]

        # Scope filter
        if scope:
            df = df.loc[df["scope"] == scope]

        # Project filter
        if project_id:
            df = df.loc[df["project_id"] == project_id]

        # Category filter
        if category:
            df = df.loc[df["category"] == category]

        # Access control: filter rows the user can see
        accessible_projects = self._visible_project_ids(resolved_user)
        # For user scope, only show the user's own memories
        # For project scope, only show projects the user can access
        # For enterprise scope, show all
        mask = df.apply(
            lambda r: self._can_access_memory(r.to_dict(), resolved_user, accessible_projects),
            axis=1,
        )
        df = df.loc[mask]

        if df.empty:
            return []

        # Score by query token overlap plus memory quality signals.
        if query.strip():
            query_tokens = set(tokenize(query, filter_stops=True))
            if query_tokens:
                df = df.copy()
                query_text = query.strip().lower()
                df["_score"] = df.apply(
                    lambda row: self._memory_match_score(row.to_dict(), query_tokens, query_text),
                    axis=1,
                )
                df = df.loc[df["_score"] > 0].sort_values("_score", ascending=False)
            else:
                df = self._memory_sort_frame(df)
        else:
            df = self._memory_sort_frame(df)

        results = df.head(limit)
        memory_ids = results["memory_id"].astype(str).tolist() if "memory_id" in results.columns else []
        self._touch_memories(memory_ids)
        payload = results.copy()
        if "_score" in payload.columns:
            payload["relevance_score"] = payload["_score"].round(2)
        cols = [c for c in payload.columns if not c.startswith("_")]
        return payload[cols].to_dict(orient="records")

    def list_memories(
        self,
        scope: str = "",
        user_id: str = "",
        project_id: str = "",
        category: str = "",
        limit: int = 20,
    ) -> list[dict[str, object]]:
        resolved_user = self._normalize_user_id(user_id)
        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if df.empty:
            return []

        if "archived" in df.columns:
            df = df.loc[df["archived"].astype(str).str.lower() != "true"]

        if scope:
            df = df.loc[df["scope"] == scope]
        if project_id:
            df = df.loc[df["project_id"] == project_id]
        if category:
            df = df.loc[df["category"] == category]

        accessible_projects = self._visible_project_ids(resolved_user)
        mask = df.apply(
            lambda r: self._can_access_memory(r.to_dict(), resolved_user, accessible_projects),
            axis=1,
        )
        df = df.loc[mask]

        df = self._memory_sort_frame(df)
        results = df.head(limit)
        memory_ids = results["memory_id"].astype(str).tolist() if "memory_id" in results.columns else []
        self._touch_memories(memory_ids)
        cols = [c for c in results.columns if not c.startswith("_")]
        return results[cols].to_dict(orient="records")

    def update_memory(
        self,
        memory_id: str,
        payload: UpdateMemoryRequest,
        user_id: str = "",
    ) -> dict[str, object]:
        resolved_user = self._normalize_user_id(user_id)
        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if df.empty:
            raise ValueError(f"Memory not found: {memory_id}")

        mask = df["memory_id"] == memory_id
        if not mask.any():
            raise ValueError(f"Memory not found: {memory_id}")

        row = df.loc[mask].iloc[0].to_dict()

        # Access check: only the author can update
        if row.get("user_id", "") != resolved_user:
            raise ValueError("Not authorized to update this memory")

        updates: dict[str, object] = {"updated_at": utc_now()}
        if payload.subject is not None:
            updates["subject"] = payload.subject
        if payload.content is not None:
            updates["content"] = payload.content
        if payload.category is not None:
            category = self._normalize_memory_category(payload.category)
            updates["category"] = category
            if payload.status is None:
                updates["status"] = self._normalize_memory_status(category, "")
        if payload.tags is not None:
            updates["tags"] = self._normalize_memory_tags(payload.tags)
        if payload.status is not None:
            category = self._normalize_memory_category(str(updates.get("category", row.get("category", ""))))
            updates["status"] = self._normalize_memory_status(category, payload.status)
        if payload.importance is not None:
            updates["importance"] = payload.importance
        if payload.confidence is not None:
            updates["confidence"] = payload.confidence
        if payload.source is not None:
            updates["source"] = self._normalize_memory_source(payload.source)
        if payload.owner is not None:
            source = str(updates.get("source", row.get("source", "")))
            updates["owner"] = self._normalize_memory_owner(payload.owner, source)
        if payload.decision_scope is not None:
            updates["decision_scope"] = payload.decision_scope.strip().lower()
        if payload.pinned is not None:
            updates["pinned"] = payload.pinned
        if payload.supersedes_memory_id is not None:
            updates["supersedes_memory_id"] = payload.supersedes_memory_id
            superseded_mask = df["memory_id"] == payload.supersedes_memory_id
            if superseded_mask.any():
                df.loc[superseded_mask, "status"] = "superseded"
                df.loc[superseded_mask, "updated_at"] = updates["updated_at"]
        if payload.expires_at is not None:
            updates["expires_at"] = payload.expires_at

        for col, val in updates.items():
            df.loc[mask, col] = val

        self.store.write_table(TABLE_MEMORY_KNOWLEDGE, df)
        if "tags" in updates:
            scope_value = str(row.get("scope", ""))
            self._sync_memory_tags(str(updates["tags"]), scope_value)
        return {"memory_id": memory_id, "status": "updated", "fields_changed": list(updates.keys())}

    def list_memory_triggers(self, category: str = "", client_type: str = "", limit: int = 20) -> list[dict[str, object]]:
        triggers = self.store.read_table(TABLE_MEMORY_TRIGGERS)
        if triggers.empty:
            return []

        filtered = triggers.copy()
        if "active" in filtered.columns:
            filtered = filtered.loc[filtered["active"].astype(str).str.lower() != "false"]

        normalized_category = category.strip().lower()
        normalized_client_type = client_type.strip().lower()

        if normalized_category and "category" in filtered.columns:
            filtered = filtered.loc[
                filtered["category"].fillna("").astype(str).str.lower().isin({"", "any", normalized_category})
            ]

        if normalized_client_type and "client_type" in filtered.columns:
            def _matches_client(value: object) -> bool:
                raw = str(value or "").strip().lower()
                if not raw or raw == "any":
                    return True
                parts = {part.strip() for part in raw.split(",") if part.strip()}
                return normalized_client_type in parts

            filtered = filtered.loc[filtered["client_type"].apply(_matches_client)]

        if "weight" in filtered.columns:
            filtered["weight"] = filtered["weight"].apply(self._coerce_float)
            filtered = filtered.sort_values(["weight", "title"], ascending=[False, True])
        else:
            filtered = filtered.sort_values("title")

        return filtered.head(limit).to_dict(orient="records")

    def archive_memory(
        self,
        memory_id: str,
        user_id: str = "",
    ) -> dict[str, object]:
        resolved_user = self._normalize_user_id(user_id)
        df = self.store.read_table(TABLE_MEMORY_KNOWLEDGE)
        if df.empty:
            raise ValueError(f"Memory not found: {memory_id}")

        mask = df["memory_id"] == memory_id
        if not mask.any():
            raise ValueError(f"Memory not found: {memory_id}")

        row = df.loc[mask].iloc[0].to_dict()
        if row.get("user_id", "") != resolved_user:
            raise ValueError("Not authorized to archive this memory")

        df.loc[mask, "archived"] = True
        df.loc[mask, "updated_at"] = utc_now()
        self.store.write_table(TABLE_MEMORY_KNOWLEDGE, df)
        return {"memory_id": memory_id, "status": "archived"}

    def route_request(
        self,
        prompt: str,
        complexity: str | None,
        session_id: str | None = None,
        user_id: str = "",
        project_id: str = "",
        client_type: str = "web",
    ) -> RouteResponse:
        resolved_complexity = normalize_complexity_label(complexity) or self._detect_complexity(prompt)
        skills = self.store.read_table(TABLE_SKILL_REGISTRY)
        ranked = self._rank_skills(skills, prompt)
        resolved_user_id = self._normalize_user_id(user_id)
        self._ensure_user_workspace(resolved_user_id)
        resolved_project_id = project_id or self._default_project_id_for_user(resolved_user_id)

        orchestrator_match = self._route_match_for_skill(ORCHESTRATOR_SKILL_ID)
        specialist_candidates = ranked.loc[~ranked["skill_id"].isin([ORCHESTRATOR_SKILL_ID, HIRING_SKILL_ID])]
        specialist_matches = specialist_candidates.head(4)[["skill_id", "display_name", "description", "search_score"]].to_dict(orient="records")

        top_specialist = specialist_matches[0] if specialist_matches else None
        needs_hiring = (not top_specialist) or float(top_specialist.get("search_score", 0)) < MIN_SPECIALIST_MATCH_SCORE

        # Domain coverage check: even if score passes, does the specialist
        # actually cover the prompt's content words?
        if top_specialist and not needs_hiring:
            prompt_content = set(tokenize(prompt, filter_stops=True))
            if prompt_content:
                spec_text = (
                    str(top_specialist.get("description", "")) + " "
                    + str(top_specialist.get("display_name", ""))
                ).lower()
                covered = sum(1 for t in prompt_content if t in spec_text)
                if covered / len(prompt_content) < MIN_DOMAIN_COVERAGE:
                    needs_hiring = True

        matches: list[dict[str, object]] = []
        if orchestrator_match:
            matches.append(orchestrator_match)
        if needs_hiring:
            hiring_match = self._route_match_for_skill(HIRING_SKILL_ID)
            if hiring_match:
                matches.append(hiring_match)
        matches.extend(specialist_matches)
        matches = matches[:5]

        top_skill_id = matches[0]["skill_id"] if matches else ""
        top_display_name = matches[0]["display_name"] if matches else ""

        if session_id:
            if orchestrator_match:
                self.activate_skill(
                    ORCHESTRATOR_SKILL_ID,
                    ActivateSkillRequest(
                        session_id=session_id,
                        user_id=resolved_user_id,
                        project_id=resolved_project_id,
                        client_type=client_type,
                        gate_level=1,
                        prompt=prompt,
                        activation_reason="Default orchestration layer activated before specialist routing",
                    ),
                )

            self._touch_session(
                session_id,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                client_type=client_type,
                top_skill_id=top_skill_id,
                active_skill_id=ORCHESTRATOR_SKILL_ID if orchestrator_match else "",
            )
            self._append_rows(
                TABLE_MEMORY_ROUTE,
                [
                    {
                        "route_id": str(uuid4()),
                        "session_id": session_id,
                        "user_id": resolved_user_id,
                        "project_id": resolved_project_id,
                        "client_type": client_type,
                        "prompt": prompt,
                        "complexity": resolved_complexity,
                        "recommended_gate": COMPLEXITY_TO_GATE[resolved_complexity],
                        "top_skill_id": top_skill_id,
                        "top_display_name": top_display_name,
                        "created_at": utc_now(),
                    }
                ],
            )

            if needs_hiring:
                self._start_hiring_process(
                    session_id=session_id,
                    user_id=resolved_user_id,
                    project_id=resolved_project_id,
                    client_type=client_type,
                    prompt=prompt,
                )

        # Determine action directive for the caller
        is_trivial = resolved_complexity == "simple"
        if is_trivial and not top_specialist:
            action = "trivial-bypass"
            next_step = "Task is trivial. Answer directly without activation."
            build_skill_id = ""
        elif needs_hiring:
            action = "auto-build"
            build_skill_id = "ultimate-skill-builder"
            # Project-level prompts get the full planning directive
            if resolved_complexity in ("deep", "expert"):
                next_step = (
                    f"No specialist matched this request. This looks like a project. "
                    f"Call plan_project_skills to get the full stakeholder skill roster, "
                    f"then call create_skill for each discovery-phase skill, "
                    f"then activate the domain-owner skill and begin gathering requirements. "
                    f"Create later-phase skills as the project progresses. Do not ask the user."
                )
            else:
                next_step = (
                    f"No specialist matched this request. "
                    f"Call create_skill to register the missing skill in the server "
                    f"(skill_id, display_name, description, purpose, use_when, personality, standards, handoffs), "
                    f"then activate the new skill and answer the original request. Do not ask the user."
                )
        else:
            action = "activate"
            rec_skill = top_specialist["skill_id"] if top_specialist else (top_skill_id or "")
            rec_name = top_specialist.get("display_name", "") if top_specialist else top_display_name
            next_step = (
                f"Activate {rec_skill} ({rec_name}) at gate {COMPLEXITY_TO_GATE[resolved_complexity]}, "
                f"then answer inside that worker's contract."
            )
            build_skill_id = ""

        # Auto-track: create a work item for every routed request
        tracked_work_item_id = ""
        if session_id and resolved_project_id:
            is_simple = resolved_complexity == "simple"
            auto_stage = "done" if is_simple and action == "trivial-bypass" else "discovery"
            truncated_prompt = prompt[:120].strip()
            tracked_row = {
                "work_item_id": f"wi-{uuid4()}",
                "project_id": resolved_project_id,
                "user_id": resolved_user_id,
                "title": truncated_prompt,
                "summary": prompt[:500],
                "stage": auto_stage,
                "owner_skill_id": top_skill_id,
                "owner_display_name": top_display_name or "Unassigned",
                "priority": "low" if is_simple else ("high" if resolved_complexity in ("deep", "expert") else "medium"),
                "updated_at": utc_now(),
            }
            work_items = self.store.read_table(TABLE_BOARD_TASKS)
            updated = pd.concat([work_items, pd.DataFrame([tracked_row])], ignore_index=True)
            self.store.write_table(TABLE_BOARD_TASKS, updated)
            tracked_work_item_id = tracked_row["work_item_id"]
            self._append_rows(
                TABLE_BOARD_AUDIT_LOG,
                [{
                    "audit_id": str(uuid4()),
                    "entity_type": "work_item",
                    "entity_id": tracked_work_item_id,
                    "action": "auto-created",
                    "detail": f"[{resolved_complexity}] {truncated_prompt}",
                    "created_at": utc_now(),
                }],
            )

        return RouteResponse(
            prompt=prompt,
            complexity=resolved_complexity,
            recommended_gate=COMPLEXITY_TO_GATE[resolved_complexity],
            matches=matches,
            action=action,
            next_step=next_step,
            build_skill_id=build_skill_id,
            work_item_id=tracked_work_item_id,
            project_id=resolved_project_id,
        )

    def list_projects(self, user_id: str = "", include_shared: bool = True) -> list[dict[str, object]]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._ensure_user_workspace(resolved_user_id)
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        if projects.empty:
            return []
        filtered = projects.copy()
        if resolved_user_id:
            mask = filtered["user_id"] == resolved_user_id
            if include_shared:
                mask = mask | (filtered["visibility"] == "shared")
            filtered = filtered.loc[mask]
        return filtered.sort_values("updated_at", ascending=False).to_dict(orient="records")

    def create_project(self, payload: CreateProjectRequest) -> dict[str, object]:
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        user_id = self._normalize_user_id(payload.user_id)
        row = {
            "project_id": f"project-{uuid4()}",
            "user_id": user_id,
            "name": payload.name,
            "summary": payload.summary,
            "owner_name": payload.owner_name or user_id,
            "stage": payload.stage,
            "visibility": payload.visibility,
            "updated_at": utc_now(),
        }
        updated = pd.concat([projects, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_GOALS, updated)
        self._append_rows(
            TABLE_BOARD_AUDIT_LOG,
            [
                {
                    "audit_id": str(uuid4()),
                    "entity_type": "project",
                    "entity_id": row["project_id"],
                    "action": "created",
                    "detail": payload.name,
                    "created_at": utc_now(),
                }
            ],
        )
        return row

    def list_work_items(self, project_id: str | None = None, user_id: str = "") -> list[dict[str, object]]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._ensure_user_workspace(resolved_user_id)
        work_items = self.store.read_table(TABLE_BOARD_TASKS)
        if work_items.empty:
            return []
        filtered = work_items.copy()
        if project_id:
            filtered = filtered.loc[filtered["project_id"] == project_id]
        elif resolved_user_id:
            visible_project_ids = {project["project_id"] for project in self.list_projects(resolved_user_id)}
            filtered = filtered.loc[filtered["project_id"].isin(visible_project_ids)]
        order_map = {stage: index for index, stage in enumerate(STAGE_ORDER)}
        filtered["stage_order"] = filtered["stage"].map(order_map)
        ordered = filtered.sort_values(["stage_order", "updated_at"], ascending=[True, False])
        return ordered.drop(columns=["stage_order"]).to_dict(orient="records")

    def create_work_item(self, payload: CreateWorkItemRequest) -> dict[str, object]:
        work_items = self.store.read_table(TABLE_BOARD_TASKS)
        project = self._project_record(payload.project_id)
        resolved_user_id = self._normalize_user_id(payload.user_id or (project.get("user_id", "") if project else ""))
        row = {
            "work_item_id": str(uuid4()),
            "project_id": payload.project_id,
            "user_id": resolved_user_id,
            "title": payload.title,
            "summary": payload.summary,
            "stage": payload.stage,
            "owner_skill_id": payload.owner_skill_id,
            "owner_display_name": payload.owner_display_name,
            "priority": payload.priority,
            "updated_at": utc_now(),
        }
        updated = pd.concat([work_items, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_TASKS, updated)
        self._touch_project(payload.project_id)
        self._append_rows(
            TABLE_BOARD_AUDIT_LOG,
            [
                {
                    "audit_id": str(uuid4()),
                    "entity_type": "task",
                    "entity_id": row["work_item_id"],
                    "action": "created",
                    "detail": payload.title,
                    "created_at": utc_now(),
                }
            ],
        )
        return row

    def update_work_item(self, work_item_id: str, payload: UpdateWorkItemRequest) -> dict[str, object] | None:
        work_items = self.store.read_table(TABLE_BOARD_TASKS)
        if work_items.empty:
            return None
        match = work_items.index[work_items["work_item_id"] == work_item_id]
        if len(match) == 0:
            return None
        updates = payload.model_dump(exclude_none=True)
        row_index = match[0]
        previous_stage = str(work_items.at[row_index, "stage"])
        for key, value in updates.items():
            work_items.at[row_index, key] = value
        work_items.at[row_index, "updated_at"] = utc_now()
        self.store.write_table(TABLE_BOARD_TASKS, work_items)
        self._touch_project(str(work_items.at[row_index, "project_id"]))
        if "stage" in updates and updates["stage"] != previous_stage:
            self._append_rows(
                TABLE_BOARD_TASK_TRANSITIONS,
                [
                    {
                        "transition_id": str(uuid4()),
                        "work_item_id": work_item_id,
                        "from_stage": previous_stage,
                        "to_stage": updates["stage"],
                        "created_at": utc_now(),
                    }
                ],
            )
        self._append_rows(
            TABLE_BOARD_AUDIT_LOG,
            [
                {
                    "audit_id": str(uuid4()),
                    "entity_type": "task",
                    "entity_id": work_item_id,
                    "action": "updated",
                    "detail": ",".join(sorted(updates.keys())) if updates else "touched",
                    "created_at": utc_now(),
                }
            ],
        )
        return work_items.loc[row_index].to_dict()

    def list_templates(self, project_id: str, user_id: str = "") -> list[dict[str, object]]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._require_project_access(project_id, resolved_user_id)
        templates = self.store.read_table(TABLE_BOARD_TEMPLATES)
        if templates.empty:
            return []
        filtered = templates.loc[
            (templates["project_id"] == project_id)
            & (templates["archived"].astype(str).str.lower() != "true")
        ].copy()
        if filtered.empty:
            return []
        filtered["category"] = filtered["category"].fillna("").replace("", "general")
        ordered = filtered.sort_values(["updated_at", "name"], ascending=[False, True])
        return ordered.to_dict(orient="records")

    def upload_template(
        self,
        *,
        project_id: str,
        user_id: str,
        name: str,
        category: str,
        description: str,
        file_name: str,
        content_type: str,
        payload: bytes,
    ) -> dict[str, object]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._require_project_access(project_id, resolved_user_id)
        self._assert_file_size(payload)

        original_file_name = Path(file_name).name.strip()
        if not original_file_name:
            raise ValueError("Uploaded file name is required")

        extension = self._normalized_file_extension(original_file_name)
        template_name = name.strip() or Path(original_file_name).stem
        template_id = f"tpl-{uuid4()}"
        relative_path = self._asset_relative_path("templates", project_id, template_id, extension)
        self.store.write_bytes("files", relative_path, payload)

        row = {
            "template_id": template_id,
            "project_id": project_id,
            "user_id": resolved_user_id,
            "name": template_name,
            "category": self._normalize_template_category(category),
            "description": description.strip(),
            "original_file_name": original_file_name,
            "stored_relative_path": relative_path,
            "file_extension": extension,
            "mime_type": self._guess_mime_type(original_file_name, content_type),
            "size_bytes": len(payload),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "archived": False,
        }
        templates = self.store.read_table(TABLE_BOARD_TEMPLATES)
        updated = pd.concat([templates, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_TEMPLATES, updated)
        self._touch_project(project_id)
        self._append_rows(
            TABLE_BOARD_AUDIT_LOG,
            [
                {
                    "audit_id": str(uuid4()),
                    "entity_type": "template",
                    "entity_id": template_id,
                    "action": "uploaded",
                    "detail": template_name,
                    "created_at": utc_now(),
                }
            ],
        )
        return row

    def _template_record(self, template_id: str, user_id: str = "") -> dict[str, object] | None:
        templates = self.store.read_table(TABLE_BOARD_TEMPLATES)
        if templates.empty:
            return None
        match = templates.loc[
            (templates["template_id"] == template_id)
            & (templates["archived"].astype(str).str.lower() != "true")
        ]
        if match.empty:
            return None
        row = match.iloc[0].to_dict()
        resolved_user_id = self._normalize_user_id(user_id)
        if resolved_user_id:
            self._require_project_access(str(row.get("project_id", "")), resolved_user_id)
        return row

    def list_generated_documents(self, project_id: str, user_id: str = "") -> list[dict[str, object]]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._require_project_access(project_id, resolved_user_id)
        documents = self.store.read_table(TABLE_BOARD_TEMPLATE_DOCUMENTS)
        if documents.empty:
            return []
        filtered = documents.loc[
            (documents["project_id"] == project_id)
            & (documents["archived"].astype(str).str.lower() != "true")
        ]
        if filtered.empty:
            return []
        return filtered.sort_values(["updated_at", "name"], ascending=[False, True]).to_dict(orient="records")

    def create_generated_document(
        self,
        project_id: str,
        template_id: str,
        payload: CreateGeneratedDocumentRequest,
    ) -> dict[str, object]:
        resolved_user_id = self._normalize_user_id(payload.user_id)
        self._require_project_access(project_id, resolved_user_id)
        template = self._template_record(template_id, resolved_user_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        if str(template.get("project_id", "")) != project_id:
            raise ValueError("Template does not belong to the active project")

        source_path = self._asset_absolute_path(str(template["stored_relative_path"]))
        if not source_path.exists():
            raise ValueError("Template file is missing from storage")

        document_id = f"doc-{uuid4()}"
        extension = str(template.get("file_extension", ""))
        document_name = payload.name.strip()
        file_name = self._template_file_name(document_name, extension)
        relative_path = self._asset_relative_path("generated", project_id, document_id, extension)
        file_bytes = source_path.read_bytes()
        self.store.write_bytes("files", relative_path, file_bytes)

        row = {
            "document_id": document_id,
            "template_id": template_id,
            "project_id": project_id,
            "user_id": resolved_user_id,
            "name": document_name,
            "description": payload.description.strip(),
            "file_name": file_name,
            "stored_relative_path": relative_path,
            "file_extension": extension,
            "mime_type": str(template.get("mime_type", self._guess_mime_type(file_name))),
            "size_bytes": len(file_bytes),
            "source_template_name": str(template.get("name", "")),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "archived": False,
        }
        documents = self.store.read_table(TABLE_BOARD_TEMPLATE_DOCUMENTS)
        updated = pd.concat([documents, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_TEMPLATE_DOCUMENTS, updated)
        self._touch_project(project_id)
        self._append_rows(
            TABLE_BOARD_AUDIT_LOG,
            [
                {
                    "audit_id": str(uuid4()),
                    "entity_type": "template_document",
                    "entity_id": document_id,
                    "action": "generated",
                    "detail": document_name,
                    "created_at": utc_now(),
                }
            ],
        )
        return row

    def get_template_file(self, template_id: str, user_id: str = "") -> dict[str, object] | None:
        template = self._template_record(template_id, user_id)
        if not template:
            return None
        path = self._asset_absolute_path(str(template["stored_relative_path"]))
        if not path.exists():
            return None
        return {
            "path": path,
            "file_name": str(template.get("original_file_name", "template")),
            "mime_type": str(template.get("mime_type", "application/octet-stream")),
            "record": template,
        }

    def get_generated_document_file(self, document_id: str, user_id: str = "") -> dict[str, object] | None:
        documents = self.store.read_table(TABLE_BOARD_TEMPLATE_DOCUMENTS)
        if documents.empty:
            return None
        match = documents.loc[
            (documents["document_id"] == document_id)
            & (documents["archived"].astype(str).str.lower() != "true")
        ]
        if match.empty:
            return None
        row = match.iloc[0].to_dict()
        resolved_user_id = self._normalize_user_id(user_id)
        self._require_project_access(str(row.get("project_id", "")), resolved_user_id)
        path = self._asset_absolute_path(str(row["stored_relative_path"]))
        if not path.exists():
            return None
        return {
            "path": path,
            "file_name": str(row.get("file_name", "document")),
            "mime_type": str(row.get("mime_type", "application/octet-stream")),
            "record": row,
        }

    def list_parking_lot(self, session_id: str, user_id: str = "") -> list[dict[str, object]]:
        parking = self.store.read_table(TABLE_MEMORY_SKILLS)
        if parking.empty:
            return []
        filtered = parking.loc[(parking["session_id"] == session_id) & (parking["status"] == "parked")]
        resolved_user_id = self._normalize_user_id(user_id)
        if resolved_user_id:
            filtered = filtered.loc[filtered["user_id"] == resolved_user_id]
        return filtered.sort_values("parked_at", ascending=False).to_dict(orient="records")

    def park_skill(self, skill_id: str, payload: ParkSkillRequest) -> dict[str, object]:
        parking = self.store.read_table(TABLE_MEMORY_SKILLS)
        skill = self.get_skill(skill_id)
        resolved_user_id = self._normalize_user_id(payload.user_id)
        resolved_project_id = payload.project_id or self._default_project_id_for_user(resolved_user_id)
        row = {
            "parking_id": str(uuid4()),
            "session_id": payload.session_id,
            "user_id": resolved_user_id,
            "project_id": resolved_project_id,
            "client_type": payload.client_type,
            "skill_id": skill_id,
            "display_name": skill["display_name"] if skill else skill_id,
            "gate_level": payload.gate_level,
            "status": "parked",
            "note": payload.note,
            "parked_at": utc_now(),
            "resumed_at": "",
        }
        updated = pd.concat([parking, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_MEMORY_SKILLS, updated)
        self._touch_session(
            payload.session_id,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            client_type=payload.client_type,
            top_skill_id=skill_id,
        )
        self._append_memory(
            scope="session",
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            session_id=payload.session_id,
            memory_type="parked-skill",
            subject_id=skill_id,
            skill_id=skill_id,
            summary=payload.note or f"Parked {row['display_name']} at gate {payload.gate_level}",
        )
        return row

    def resume_skill(self, skill_id: str, payload: ResumeSkillRequest) -> dict[str, object] | None:
        parking = self.store.read_table(TABLE_MEMORY_SKILLS)
        if parking.empty:
            return None
        resolved_user_id = self._normalize_user_id(payload.user_id)
        filtered = parking.loc[
            (parking["skill_id"] == skill_id)
            & (parking["session_id"] == payload.session_id)
            & (parking["status"] == "parked")
        ]
        if resolved_user_id:
            filtered = filtered.loc[filtered["user_id"] == resolved_user_id]
        if filtered.empty:
            return None
        row_index = filtered.index[0]
        parking.at[row_index, "status"] = "resumed"
        parking.at[row_index, "resumed_at"] = utc_now()
        self.store.write_table(TABLE_MEMORY_SKILLS, parking)
        self._touch_session(
            payload.session_id,
            user_id=str(parking.at[row_index, "user_id"]),
            project_id=str(parking.at[row_index, "project_id"]),
            client_type=str(parking.at[row_index, "client_type"]),
            top_skill_id=skill_id,
        )
        return parking.loc[row_index].to_dict()

    def activate_skill(self, skill_id: str, payload: ActivateSkillRequest) -> dict[str, object]:
        activations = self.store.read_table(TABLE_MEMORY_ACTIVATIONS)
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_id}")

        resolved_user_id = self._normalize_user_id(payload.user_id)
        resolved_project_id = payload.project_id or self._default_project_id_for_user(resolved_user_id)
        if not activations.empty:
            mask = (
                (activations["session_id"] == payload.session_id)
                & (activations["user_id"] == resolved_user_id)
                & (activations["status"] == "active")
            )
            active_rows = activations.index[mask]
            for row_index in active_rows:
                activations.at[row_index, "status"] = "superseded"
                activations.at[row_index, "deactivated_at"] = utc_now()

        row = {
            "activation_id": str(uuid4()),
            "session_id": payload.session_id,
            "user_id": resolved_user_id,
            "project_id": resolved_project_id,
            "client_type": payload.client_type,
            "skill_id": skill_id,
            "display_name": skill["display_name"],
            "gate_level": payload.gate_level,
            "status": "active",
            "route_prompt": payload.prompt,
            "activation_reason": payload.activation_reason or "Skill activated through runtime contract",
            "activated_at": utc_now(),
            "deactivated_at": "",
        }
        updated = pd.concat([activations, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_MEMORY_ACTIVATIONS, updated)
        self._touch_session(
            payload.session_id,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            client_type=payload.client_type,
            top_skill_id=skill_id,
            active_skill_id=skill_id,
        )
        self.record_skill_event(
            SkillEventRequest(
                session_id=payload.session_id,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                activation_id=row["activation_id"],
                skill_id=skill_id,
                event_type="skill_activated",
                status="info",
                summary=f"Activated {skill['display_name']} at gate {payload.gate_level}.",
                payload={
                    "prompt": payload.prompt,
                    "activation_reason": row["activation_reason"],
                    "client_type": payload.client_type,
                },
            )
        )
        return row

    def get_active_skill(self, session_id: str, user_id: str = "") -> dict[str, object] | None:
        activations = self.store.read_table(TABLE_MEMORY_ACTIVATIONS)
        if activations.empty:
            return None
        filtered = activations.loc[(activations["session_id"] == session_id) & (activations["status"] == "active")]
        resolved_user_id = self._normalize_user_id(user_id)
        if resolved_user_id:
            filtered = filtered.loc[filtered["user_id"] == resolved_user_id]
        if filtered.empty:
            return None
        latest = filtered.sort_values("activated_at", ascending=False).iloc[0]
        return latest.to_dict()

    def list_user_sessions(self, user_id: str = "", project_id: str = "", limit: int = 40) -> list[dict[str, object]]:
        resolved_user_id = self._normalize_user_id(user_id)
        self._ensure_user_workspace(resolved_user_id)
        self._prune_expired_workspace_sessions(resolved_user_id)

        sessions = self.store.read_table(TABLE_MEMORY_SESSIONS)
        if sessions.empty:
            return []

        filtered = sessions.loc[sessions["user_id"] == resolved_user_id].copy()
        accessible_projects = self._visible_project_ids(resolved_user_id)
        if accessible_projects:
            filtered = filtered.loc[filtered["project_id"].isin(accessible_projects)]
        if project_id:
            self._require_project_access(project_id, resolved_user_id)
            filtered = filtered.loc[filtered["project_id"] == project_id]
        if filtered.empty:
            return []

        requested_limit = limit if limit > 0 else 40
        default_project_id = self._default_project_id_for_user(resolved_user_id)
        project_name_map = {
            str(row.get("project_id", "")): str(row.get("name", ""))
            for row in self.store.read_table(TABLE_BOARD_GOALS).to_dict(orient="records")
        }

        routes = self.store.read_table(TABLE_MEMORY_ROUTE)
        if not routes.empty:
            routes = routes.loc[routes["user_id"] == resolved_user_id].copy()
        events = self.store.read_table(TABLE_MEMORY_EVENTS)
        if not events.empty:
            events = events.loc[events["user_id"] == resolved_user_id].copy()

        session_rows: list[dict[str, object]] = []
        for row in filtered.to_dict(orient="records"):
            session_id = str(row.get("session_id", ""))
            project_ref = str(row.get("project_id", ""))
            history_scope = "workspace" if project_ref == default_project_id else "project"

            session_routes = routes.loc[routes["session_id"] == session_id] if not routes.empty else pd.DataFrame()
            session_events = events.loc[events["session_id"] == session_id] if not events.empty else pd.DataFrame()
            last_route_prompt = ""
            if not session_routes.empty:
                latest_route = session_routes.sort_values("created_at", ascending=False).iloc[0].to_dict()
                last_route_prompt = str(latest_route.get("prompt", "")).strip()

            session_rows.append(
                {
                    "session_id": session_id,
                    "user_id": resolved_user_id,
                    "project_id": project_ref,
                    "project_name": project_name_map.get(project_ref, ""),
                    "client_type": str(row.get("client_type", "")),
                    "status": str(row.get("status", "")),
                    "top_skill_id": str(row.get("top_skill_id", "")),
                    "active_skill_id": str(row.get("active_skill_id", "")),
                    "last_used_at": str(row.get("last_used_at", "")),
                    "last_route_prompt": last_route_prompt,
                    "route_count": 0 if session_routes.empty else int(len(session_routes.index)),
                    "event_count": 0 if session_events.empty else int(len(session_events.index)),
                    "history_scope": history_scope,
                    "retention_days": WORKSPACE_HISTORY_RETENTION_DAYS if history_scope == "workspace" else None,
                }
            )

        session_rows.sort(key=lambda item: str(item.get("last_used_at", "")), reverse=True)
        return session_rows[:requested_limit]

    def get_session_history(self, session_id: str, user_id: str = "", limit: int = DEFAULT_SESSION_HISTORY_LIMIT) -> dict[str, object] | None:
        resolved_user_id = self._normalize_user_id(user_id)
        self._ensure_user_workspace(resolved_user_id)
        self._prune_expired_workspace_sessions(resolved_user_id)

        session_index = {
            str(item.get("session_id", "")): item
            for item in self.list_user_sessions(resolved_user_id, limit=200)
        }
        session = session_index.get(session_id)
        if not session:
            return None

        requested_limit = limit if limit > 0 else DEFAULT_SESSION_HISTORY_LIMIT
        timeline: list[dict[str, object]] = []

        routes = self.store.read_table(TABLE_MEMORY_ROUTE)
        if not routes.empty:
            session_routes = routes.loc[
                (routes["session_id"] == session_id) & (routes["user_id"] == resolved_user_id)
            ].sort_values("created_at", ascending=False)
            for row in session_routes.to_dict(orient="records"):
                prompt_preview = str(row.get("prompt", "")).strip()
                top_display_name = str(row.get("top_display_name", "")).strip()
                detail = f"[{row.get('complexity', 'unknown')}] {prompt_preview}"
                if top_display_name:
                    detail = f"{detail} -> {top_display_name}"
                timeline.append(
                    {
                        "entry_id": str(row.get("route_id", "")),
                        "entry_type": "route",
                        "title": "Request routed",
                        "detail": detail,
                        "created_at": str(row.get("created_at", "")),
                        "skill_id": str(row.get("top_skill_id", "")),
                    }
                )

        events = self.store.read_table(TABLE_MEMORY_EVENTS)
        if not events.empty:
            session_events = events.loc[
                (events["session_id"] == session_id) & (events["user_id"] == resolved_user_id)
            ].sort_values("created_at", ascending=False)
            for row in session_events.to_dict(orient="records"):
                event_type = str(row.get("event_type", "event"))
                title = {
                    "skill_activated": "Worker activated",
                    "alignment_scored": "Alignment scored",
                    "feedback_recorded": "Feedback recorded",
                    "hiring_process_started": "Hiring started",
                }.get(event_type, event_type.replace("_", " ").title())
                timeline.append(
                    {
                        "entry_id": str(row.get("event_id", "")),
                        "entry_type": "event",
                        "title": title,
                        "detail": str(row.get("summary", "")),
                        "created_at": str(row.get("created_at", "")),
                        "skill_id": str(row.get("skill_id", "")),
                    }
                )

        alignments = self.store.read_table(TABLE_MEMORY_ALIGNMENT)
        if not alignments.empty:
            session_alignments = alignments.loc[
                (alignments["session_id"] == session_id) & (alignments["user_id"] == resolved_user_id)
            ].sort_values("created_at", ascending=False)
            for row in session_alignments.to_dict(orient="records"):
                score = self._coerce_int(row.get("score", 0))
                detail = f"{row.get('display_name', row.get('skill_id', 'Worker'))}: {score}/100. {row.get('summary', '')}"
                timeline.append(
                    {
                        "entry_id": str(row.get("alignment_id", "")),
                        "entry_type": "alignment",
                        "title": "Alignment review",
                        "detail": detail.strip(),
                        "created_at": str(row.get("created_at", "")),
                        "skill_id": str(row.get("skill_id", "")),
                    }
                )

        timeline.sort(
            key=lambda item: parse_utc_timestamp(item.get("created_at")) or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return {
            "session": session,
            "timeline": timeline[:requested_limit],
        }

    # ------------------------------------------------------------------
    # Sprint management
    # ------------------------------------------------------------------

    def create_sprint(self, payload: CreateSprintRequest, user_id: str = "") -> dict[str, object]:
        resolved_user = self._normalize_user_id(user_id)
        sprints = self.store.read_table(TABLE_BOARD_SPRINTS)
        row = {
            "sprint_id": f"sprint-{uuid4()}",
            "project_id": payload.project_id,
            "user_id": resolved_user,
            "name": payload.name,
            "status": payload.status,
            "created_at": utc_now(),
        }
        updated = pd.concat([sprints, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_SPRINTS, updated)
        self._append_rows(TABLE_BOARD_AUDIT_LOG, [{
            "audit_id": str(uuid4()),
            "entity_type": "sprint",
            "entity_id": row["sprint_id"],
            "action": "created",
            "detail": payload.name,
            "created_at": utc_now(),
        }])
        return row

    def list_sprints(self, project_id: str = "", user_id: str = "") -> list[dict[str, object]]:
        resolved_user = self._normalize_user_id(user_id)
        sprints = self.store.read_table(TABLE_BOARD_SPRINTS)
        if sprints.empty:
            return []
        if project_id:
            sprints = sprints.loc[sprints["project_id"] == project_id]
        return sprints.sort_values("created_at", ascending=False).to_dict(orient="records")

    def update_sprint_status(self, sprint_id: str, status: str) -> dict[str, object]:
        sprints = self.store.read_table(TABLE_BOARD_SPRINTS)
        if sprints.empty:
            raise ValueError(f"Sprint not found: {sprint_id}")
        mask = sprints["sprint_id"] == sprint_id
        if not mask.any():
            raise ValueError(f"Sprint not found: {sprint_id}")
        sprints.loc[mask, "status"] = status
        self.store.write_table(TABLE_BOARD_SPRINTS, sprints)
        self._append_rows(TABLE_BOARD_AUDIT_LOG, [{
            "audit_id": str(uuid4()),
            "entity_type": "sprint",
            "entity_id": sprint_id,
            "action": "status-changed",
            "detail": status,
            "created_at": utc_now(),
        }])
        return sprints.loc[mask].iloc[0].to_dict()

    def add_to_sprint(self, sprint_id: str, work_item_id: str) -> dict[str, object]:
        sprint_tasks = self.store.read_table(TABLE_BOARD_SPRINT_TASKS)
        # Check for duplicate
        if not sprint_tasks.empty:
            dupe = sprint_tasks.loc[
                (sprint_tasks["sprint_id"] == sprint_id)
                & (sprint_tasks["work_item_id"] == work_item_id)
            ]
            if not dupe.empty:
                return {"sprint_task_id": dupe.iloc[0]["sprint_task_id"], "status": "already_assigned"}
        row = {
            "sprint_task_id": str(uuid4()),
            "sprint_id": sprint_id,
            "work_item_id": work_item_id,
        }
        updated = pd.concat([sprint_tasks, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_SPRINT_TASKS, updated)
        return {**row, "status": "assigned"}

    def remove_from_sprint(self, sprint_id: str, work_item_id: str) -> dict[str, object]:
        sprint_tasks = self.store.read_table(TABLE_BOARD_SPRINT_TASKS)
        if sprint_tasks.empty:
            raise ValueError("No sprint tasks found")
        mask = (sprint_tasks["sprint_id"] == sprint_id) & (sprint_tasks["work_item_id"] == work_item_id)
        if not mask.any():
            raise ValueError(f"Work item {work_item_id} not in sprint {sprint_id}")
        sprint_tasks = sprint_tasks.loc[~mask]
        self.store.write_table(TABLE_BOARD_SPRINT_TASKS, sprint_tasks)
        return {"sprint_id": sprint_id, "work_item_id": work_item_id, "status": "removed"}

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def add_comment(self, payload: AddCommentRequest, user_id: str = "", skill_id: str = "") -> dict[str, object]:
        resolved_user = self._normalize_user_id(user_id)
        author = skill_id if skill_id else resolved_user
        row = {
            "comment_id": str(uuid4()),
            "entity_type": payload.entity_type,
            "entity_id": payload.entity_id,
            "author": author,
            "body": payload.body,
            "created_at": utc_now(),
        }
        self._append_rows(TABLE_BOARD_COMMENTS, [row])
        return row

    def list_comments(self, entity_type: str, entity_id: str) -> list[dict[str, object]]:
        comments = self.store.read_table(TABLE_BOARD_COMMENTS)
        if comments.empty:
            return []
        filtered = comments.loc[
            (comments["entity_type"] == entity_type)
            & (comments["entity_id"] == entity_id)
        ]
        return filtered.sort_values("created_at", ascending=True).to_dict(orient="records")

    # ------------------------------------------------------------------
    # Task transitions (read-only — writes happen via update_work_item)
    # ------------------------------------------------------------------

    def list_transitions(self, work_item_id: str) -> list[dict[str, object]]:
        transitions = self.store.read_table(TABLE_BOARD_TASK_TRANSITIONS)
        if transitions.empty:
            return []
        filtered = transitions.loc[transitions["work_item_id"] == work_item_id]
        return filtered.sort_values("created_at", ascending=True).to_dict(orient="records")

    def record_skill_event(self, payload: SkillEventRequest) -> dict[str, object]:
        events = self.store.read_table(TABLE_MEMORY_EVENTS)
        resolved_user_id = self._normalize_user_id(payload.user_id)
        resolved_project_id = payload.project_id or self._default_project_id_for_user(resolved_user_id)
        active_skill = self.get_active_skill(payload.session_id, resolved_user_id)
        activation_id = payload.activation_id or (active_skill.get("activation_id", "") if active_skill else "")
        skill_id = payload.skill_id or (active_skill.get("skill_id", "") if active_skill else "")
        row = {
            "event_id": str(uuid4()),
            "activation_id": activation_id,
            "session_id": payload.session_id,
            "user_id": resolved_user_id,
            "project_id": resolved_project_id,
            "skill_id": skill_id,
            "event_type": payload.event_type,
            "status": payload.status,
            "summary": payload.summary,
            "payload_json": json.dumps(payload.payload, ensure_ascii=True),
            "created_at": utc_now(),
        }
        updated = pd.concat([events, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_MEMORY_EVENTS, updated)
        self._touch_session(
            payload.session_id,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            client_type=active_skill.get("client_type", "web") if active_skill else "web",
            top_skill_id=skill_id,
            active_skill_id=active_skill.get("skill_id", "") if active_skill else "",
        )
        return row

    def score_response_alignment(self, payload: AlignmentRequest) -> dict[str, object]:
        alignments = self.store.read_table(TABLE_MEMORY_ALIGNMENT)
        resolved_user_id = self._normalize_user_id(payload.user_id)
        resolved_project_id = payload.project_id or self._default_project_id_for_user(resolved_user_id)
        active_skill = self.get_active_skill(payload.session_id, resolved_user_id)
        skill_id = payload.skill_id or (active_skill.get("skill_id", "") if active_skill else "")
        skill = self.get_skill(skill_id) if skill_id else None
        if not skill:
            raise ValueError("A skill must be active or explicitly provided before alignment can be scored")

        gate_level = payload.gate_level or int(active_skill.get("gate_level", 1) if active_skill else 1)
        bundles = self.load_skill_bundles(skill_id, gate_level)
        latest_route = self._latest_route(payload.session_id, resolved_user_id)

        checks = {
            "active_skill_present": bool(active_skill),
            "active_skill_matches_requested_skill": not payload.skill_id or payload.skill_id == skill_id,
            "route_top_match": bool(latest_route) and latest_route.get("top_skill_id", "") == skill_id,
            "gate_context_loaded": len(bundles) > 0,
            "prompt_scope_match": self._prompt_scope_match(skill_id, payload.prompt),
            "response_excerpt_present": len(payload.response_excerpt.strip()) >= 24,
        }

        score = 0
        score += 30 if checks["active_skill_present"] else 0
        score += 15 if checks["active_skill_matches_requested_skill"] else 0
        score += 20 if checks["route_top_match"] else 0
        score += 15 if checks["gate_context_loaded"] else 0
        score += 10 if checks["prompt_scope_match"] else 0
        score += 10 if checks["response_excerpt_present"] else 0

        if score >= 80:
            status = "aligned"
        elif score >= 55:
            status = "partial"
        else:
            status = "weak"

        summary = (
            f"{skill['display_name']} alignment scored {score}/100 "
            f"with status {status} at gate {gate_level}."
        )
        row = {
            "alignment_id": str(uuid4()),
            "activation_id": active_skill.get("activation_id", "") if active_skill else "",
            "session_id": payload.session_id,
            "user_id": resolved_user_id,
            "project_id": resolved_project_id,
            "skill_id": skill_id,
            "display_name": skill["display_name"],
            "gate_level": gate_level,
            "score": score,
            "status": status,
            "summary": summary,
            "checks_json": json.dumps(checks, ensure_ascii=True),
            "created_at": utc_now(),
        }
        updated = pd.concat([alignments, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_MEMORY_ALIGNMENT, updated)
        self.record_skill_event(
            SkillEventRequest(
                session_id=payload.session_id,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                activation_id=row["activation_id"],
                skill_id=skill_id,
                event_type="alignment_scored",
                status=status,
                summary=summary,
                payload={"checks": checks, "note": payload.note},
            )
        )
        return row

    def record_feedback(self, payload: FeedbackRequest) -> dict[str, object]:
        feedback = self.store.read_table(TABLE_MEMORY_ANALYTICS)
        resolved_user_id = self._normalize_user_id(payload.user_id)
        resolved_project_id = payload.project_id or self._default_project_id_for_user(resolved_user_id)
        row = {
            "feedback_id": str(uuid4()),
            "session_id": payload.session_id,
            "user_id": resolved_user_id,
            "project_id": resolved_project_id,
            "client_type": payload.client_type,
            "skill_id": payload.skill_id,
            "rating": payload.rating,
            "prompt": payload.prompt,
            "response_excerpt": payload.response_excerpt,
            "note": payload.note,
            "work_item_id": payload.work_item_id,
            "created_at": utc_now(),
        }
        updated = pd.concat([feedback, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_MEMORY_ANALYTICS, updated)
        self._touch_session(
            payload.session_id,
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            client_type=payload.client_type,
            top_skill_id=payload.skill_id,
        )
        self._append_memory(
            scope="company",
            user_id=resolved_user_id,
            project_id=resolved_project_id,
            session_id=payload.session_id,
            memory_type="skill-feedback",
            subject_id=payload.skill_id,
            skill_id=payload.skill_id,
            summary=f"{payload.rating} feedback for {payload.skill_id}: {payload.prompt[:180]}",
        )
        self.record_skill_event(
            SkillEventRequest(
                session_id=payload.session_id,
                user_id=resolved_user_id,
                project_id=resolved_project_id,
                skill_id=payload.skill_id,
                event_type="feedback_recorded",
                status="info",
                summary=f"Recorded {payload.rating} feedback for {payload.skill_id}.",
                payload={"work_item_id": payload.work_item_id, "note": payload.note},
            )
        )
        return row

    def recent_events(self, user_id: str, session_id: str = "", limit: int = 12) -> list[dict[str, object]]:
        events = self.store.read_table(TABLE_MEMORY_EVENTS)
        if events.empty:
            return []
        resolved_user_id = self._normalize_user_id(user_id)
        filtered = events.loc[events["user_id"] == resolved_user_id]
        if session_id:
            filtered = filtered.loc[filtered["session_id"] == session_id]
        return filtered.sort_values("created_at", ascending=False).head(limit).to_dict(orient="records")

    def latest_alignment(self, user_id: str, session_id: str = "") -> dict[str, object] | None:
        alignments = self.store.read_table(TABLE_MEMORY_ALIGNMENT)
        if alignments.empty:
            return None
        resolved_user_id = self._normalize_user_id(user_id)
        filtered = alignments.loc[alignments["user_id"] == resolved_user_id]
        if session_id:
            filtered = filtered.loc[filtered["session_id"] == session_id]
        if filtered.empty:
            return None
        return filtered.sort_values("created_at", ascending=False).iloc[0].to_dict()

    def build_session_story(self, session_id: str, user_id: str) -> dict[str, object]:
        resolved_user_id = self._normalize_user_id(user_id)
        active_skill = self.get_active_skill(session_id, resolved_user_id)
        latest_route = self._latest_route(session_id, resolved_user_id)
        events = self.recent_events(resolved_user_id, session_id=session_id, limit=6)

        hiring_started = any(event.get("event_type") == "hiring_process_started" for event in events)

        if hiring_started:
            headline = "We are starting hiring for a missing specialist skill."
            current_step = "TalentDirector is creating coverage for your request."
            next_step = "Once the new skill is added, reroute your prompt to continue automatically."
        elif active_skill and active_skill.get("skill_id") == ORCHESTRATOR_SKILL_ID:
            headline = "Your request is in orchestration."
            current_step = "Orchestrator is selecting or preparing the right specialist."
            next_step = "Review the recommended skill list and activate the best specialist if needed."
        elif active_skill:
            display_name = str(active_skill.get("display_name", "the active skill"))
            headline = f"{display_name} is actively working on your request."
            current_step = f"{display_name} is running at gate {active_skill.get('gate_level', 1)}."
            next_step = "Review the response and mark feedback as correct or wrong to improve future routing."
        else:
            headline = "No worker is active yet."
            current_step = "Route your request to start the workflow."
            next_step = "After routing, the orchestrator will load and guide specialist selection."

        if latest_route and latest_route.get("prompt"):
            prompt_preview = str(latest_route.get("prompt", "")).strip()
            if prompt_preview:
                headline = f"{headline} Latest request: {prompt_preview[:96]}{'...' if len(prompt_preview) > 96 else ''}"

        timeline: list[dict[str, object]] = []
        for event in events:
            event_type = str(event.get("event_type", "event"))
            title = {
                "skill_activated": "Worker activated",
                "alignment_scored": "Quality check recorded",
                "feedback_recorded": "User feedback saved",
                "hiring_process_started": "Hiring process started",
            }.get(event_type, event_type.replace("_", " ").title())
            timeline.append(
                {
                    "title": title,
                    "detail": str(event.get("summary", "")),
                    "time": str(event.get("created_at", "")),
                }
            )

        active_worker = str(active_skill.get("display_name", "None")) if active_skill else "None"
        return {
            "headline": headline,
            "current_step": current_step,
            "next_step": next_step,
            "active_worker": active_worker,
            "hiring_in_progress": hiring_started,
            "timeline": timeline,
        }

    def seed_defaults(self) -> None:
        self._ensure_table(
            TABLE_BOARD_GOALS,
            ["project_id", "user_id", "name", "summary", "owner_name", "stage", "visibility", "updated_at"],
        )
        self._ensure_table(
            TABLE_BOARD_TASKS,
            [
                "work_item_id",
                "project_id",
                "user_id",
                "title",
                "summary",
                "stage",
                "owner_skill_id",
                "owner_display_name",
                "priority",
                "updated_at",
            ],
        )
        self._ensure_table(TABLE_BOARD_AUDIT_LOG, ["audit_id", "entity_type", "entity_id", "action", "detail", "created_at"])
        self._ensure_table(TABLE_BOARD_COMMENTS, ["comment_id", "entity_type", "entity_id", "author", "body", "created_at"])
        self._ensure_table(TABLE_BOARD_EPIC, ["epic_id", "title", "summary", "created_at"])
        self._ensure_table(TABLE_BOARD_SPRINT_TASKS, ["sprint_task_id", "sprint_id", "work_item_id"])
        self._ensure_table(TABLE_BOARD_SPRINTS, ["sprint_id", "project_id", "user_id", "name", "status", "created_at"])
        self._ensure_table(TABLE_BOARD_TASK_TRANSITIONS, ["transition_id", "work_item_id", "from_stage", "to_stage", "created_at"])
        self._ensure_table(
            TABLE_BOARD_TEMPLATES,
            [
                "template_id",
                "project_id",
                "user_id",
                "name",
                "category",
                "description",
                "original_file_name",
                "stored_relative_path",
                "file_extension",
                "mime_type",
                "size_bytes",
                "created_at",
                "updated_at",
                "archived",
            ],
        )
        self._ensure_table(
            TABLE_BOARD_TEMPLATE_DOCUMENTS,
            [
                "document_id",
                "template_id",
                "project_id",
                "user_id",
                "name",
                "description",
                "file_name",
                "stored_relative_path",
                "file_extension",
                "mime_type",
                "size_bytes",
                "source_template_name",
                "created_at",
                "updated_at",
                "archived",
            ],
        )

        self._ensure_table(
            TABLE_MEMORY_ACTIVATIONS,
            [
                "activation_id",
                "session_id",
                "user_id",
                "project_id",
                "client_type",
                "skill_id",
                "display_name",
                "gate_level",
                "status",
                "route_prompt",
                "activation_reason",
                "activated_at",
                "deactivated_at",
            ],
        )
        self._ensure_table(
            TABLE_MEMORY_ANALYTICS,
            [
                "feedback_id",
                "session_id",
                "user_id",
                "project_id",
                "client_type",
                "skill_id",
                "rating",
                "prompt",
                "response_excerpt",
                "note",
                "work_item_id",
                "created_at",
            ],
        )
        self._ensure_table(
            TABLE_MEMORY_ALIGNMENT,
            [
                "alignment_id",
                "activation_id",
                "session_id",
                "user_id",
                "project_id",
                "skill_id",
                "display_name",
                "gate_level",
                "score",
                "status",
                "summary",
                "checks_json",
                "created_at",
            ],
        )
        self._ensure_table(TABLE_MEMORY_CONFIG, ["config_key", "config_value", "updated_at"])
        self._ensure_table(TABLE_MEMORY_DECISION, ["decision_id", "session_id", "decision_type", "detail", "created_at"])
        self._ensure_table(
            TABLE_MEMORY_EVENTS,
            [
                "event_id",
                "activation_id",
                "session_id",
                "user_id",
                "project_id",
                "skill_id",
                "event_type",
                "status",
                "summary",
                "payload_json",
                "created_at",
            ],
        )
        self._ensure_table(
            TABLE_MEMORY_MEMORIES,
            ["memory_id", "scope", "user_id", "project_id", "session_id", "memory_type", "subject_id", "skill_id", "summary", "created_at"],
        )
        self._ensure_table(
            TABLE_MEMORY_KNOWLEDGE,
            [
                "memory_id", "scope", "user_id", "project_id", "category",
                "subject", "content", "skill_id", "session_id", "tags",
                "status", "importance", "confidence", "source", "owner",
                "decision_scope", "pinned", "supersedes_memory_id", "expires_at",
                "last_accessed_at", "access_count", "created_at", "updated_at", "archived",
            ],
        )
        self._ensure_table(
            TABLE_MEMORY_ROUTE,
            [
                "route_id",
                "session_id",
                "user_id",
                "project_id",
                "client_type",
                "prompt",
                "complexity",
                "recommended_gate",
                "top_skill_id",
                "top_display_name",
                "created_at",
            ],
        )
        self._ensure_table(
            TABLE_MEMORY_SESSIONS,
            ["session_id", "user_id", "project_id", "client_type", "status", "top_skill_id", "active_skill_id", "last_used_at"],
        )
        self._ensure_table(
            TABLE_MEMORY_SKILLS,
            [
                "parking_id",
                "session_id",
                "user_id",
                "project_id",
                "client_type",
                "skill_id",
                "display_name",
                "gate_level",
                "status",
                "note",
                "parked_at",
                "resumed_at",
            ],
        )
        self._ensure_table(TABLE_MEMORY_TAGS, ["tag_id", "tag", "scope"])
        self._ensure_table(
            TABLE_MEMORY_TRIGGERS,
            ["trigger_id", "skill_id", "trigger_kind", "title", "trigger_text", "action_text", "category", "client_type", "weight", "active"],
        )

        self._seed_memory_files()
        self._seed_memory_triggers()
        self._seed_shared_project()
        self._ensure_user_workspace(self.settings.default_user_id)
        self._prune_expired_workspace_sessions()

    def _seed_shared_project(self) -> None:
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        if not projects.empty and SHARED_PROJECT_ID in set(projects["project_id"]):
            return

        now = utc_now()
        shared_row = {
            "project_id": SHARED_PROJECT_ID,
            "user_id": SHARED_OWNER_ID,
            "name": "Company Skill Runtime",
            "summary": "Shared company control plane for skill routing, activation, audit, and memory learning across Genie Code and IDE users.",
            "owner_name": "Skill Runtime Platform",
            "stage": "active",
            "visibility": "shared",
            "updated_at": now,
        }

        projects = pd.concat([projects, pd.DataFrame([shared_row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_GOALS, projects)

        work_items = self.store.read_table(TABLE_BOARD_TASKS)
        if work_items.empty:
            default_items = [
                {
                    "work_item_id": str(uuid4()),
                    "project_id": SHARED_PROJECT_ID,
                    "user_id": SHARED_OWNER_ID,
                    "title": "Govern shared skill creation",
                    "summary": "Prevent 700+ users from spawning overlapping skills and isolated memories.",
                    "stage": "discovery",
                    "owner_skill_id": "ultimate-skill-builder",
                    "owner_display_name": self._display_name_for("ultimate-skill-builder", "Calder Vale"),
                    "priority": "high",
                    "updated_at": now,
                },
                {
                    "work_item_id": str(uuid4()),
                    "project_id": SHARED_PROJECT_ID,
                    "user_id": SHARED_OWNER_ID,
                    "title": "Standardize activation contract",
                    "summary": "Make the MCP and instruction contract prove which worker is active and how aligned each turn is.",
                    "stage": "design",
                    "owner_skill_id": "architect",
                    "owner_display_name": self._display_name_for("architect", "Adrian Cross"),
                    "priority": "high",
                    "updated_at": now,
                },
                {
                    "work_item_id": str(uuid4()),
                    "project_id": SHARED_PROJECT_ID,
                    "user_id": SHARED_OWNER_ID,
                    "title": "Ship centralized runtime service",
                    "summary": "Expose one shared MCP surface for Genie Code and company IDE clients.",
                    "stage": "build",
                    "owner_skill_id": "app-builder",
                    "owner_display_name": self._display_name_for("app-builder", "Jules Mercer"),
                    "priority": "high",
                    "updated_at": now,
                },
                {
                    "work_item_id": str(uuid4()),
                    "project_id": SHARED_PROJECT_ID,
                    "user_id": SHARED_OWNER_ID,
                    "title": "Measure skill alignment",
                    "summary": "Track activation, handoff, and response alignment so end users can see whether the active worker is actually in control.",
                    "stage": "review",
                    "owner_skill_id": "app-qa",
                    "owner_display_name": self._display_name_for("app-qa", "Mara Ellison"),
                    "priority": "medium",
                    "updated_at": now,
                },
            ]
            self.store.write_table(TABLE_BOARD_TASKS, pd.DataFrame(default_items))

    def _ensure_user_workspace(self, user_id: str) -> None:
        resolved_user_id = self._normalize_user_id(user_id)
        if not resolved_user_id:
            return
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        default_project_id = self._default_project_id_for_user(resolved_user_id)
        if not projects.empty and default_project_id in set(projects["project_id"]):
            return
        row = {
            "project_id": default_project_id,
            "user_id": resolved_user_id,
            "name": f"{resolved_user_id} workspace",
            "summary": "Private project lane for tracking what this user's Genie Code or IDE sessions are doing.",
            "owner_name": resolved_user_id,
            "stage": "active",
            "visibility": "private",
            "updated_at": utc_now(),
        }
        updated = pd.concat([projects, pd.DataFrame([row])], ignore_index=True)
        self.store.write_table(TABLE_BOARD_GOALS, updated)

    def _default_project_id_for_user(self, user_id: str) -> str:
        return f"user-{safe_identifier(user_id)}-workspace"

    def _is_workspace_session(self, project_id: str, user_id: str) -> bool:
        resolved_user_id = self._normalize_user_id(user_id)
        return project_id == self._default_project_id_for_user(resolved_user_id)

    def _prune_expired_workspace_sessions(self, user_id: str = "") -> None:
        sessions = self.store.read_table(TABLE_MEMORY_SESSIONS)
        if sessions.empty:
            return

        cutoff = datetime.now(UTC) - timedelta(days=WORKSPACE_HISTORY_RETENTION_DAYS)
        resolved_user_id = self._normalize_user_id(user_id)
        expired_session_ids: list[str] = []

        for row in sessions.to_dict(orient="records"):
            row_user_id = self._normalize_user_id(str(row.get("user_id", "")))
            if resolved_user_id and row_user_id != resolved_user_id:
                continue
            project_id = str(row.get("project_id", ""))
            if not self._is_workspace_session(project_id, row_user_id):
                continue
            last_used_at = parse_utc_timestamp(row.get("last_used_at"))
            if last_used_at and last_used_at < cutoff:
                expired_session_ids.append(str(row.get("session_id", "")))

        if not expired_session_ids:
            return

        session_table = sessions.loc[~sessions["session_id"].isin(expired_session_ids)].copy()
        self.store.write_table(TABLE_MEMORY_SESSIONS, session_table)

        related_tables = [
            TABLE_MEMORY_ACTIVATIONS,
            TABLE_MEMORY_ANALYTICS,
            TABLE_MEMORY_ALIGNMENT,
            TABLE_MEMORY_EVENTS,
            TABLE_MEMORY_MEMORIES,
            TABLE_MEMORY_ROUTE,
            TABLE_MEMORY_SKILLS,
        ]
        for table_name in related_tables:
            dataframe = self.store.read_table(table_name)
            if dataframe.empty or "session_id" not in dataframe.columns:
                continue
            cleaned = dataframe.loc[~dataframe["session_id"].isin(expired_session_ids)].copy()
            if len(cleaned.index) != len(dataframe.index):
                self.store.write_table(table_name, cleaned)

    def _project_record(self, project_id: str) -> dict[str, object] | None:
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        if projects.empty:
            return None
        match = projects.loc[projects["project_id"] == project_id]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def _display_name_for(self, skill_id: str, fallback: str) -> str:
        skill = self.get_skill(skill_id)
        if not skill:
            return fallback
        return str(skill["display_name"])

    def _normalize_user_id(self, user_id: str) -> str:
        return (user_id or self.settings.default_user_id).strip().lower()

    def _require_project_access(self, project_id: str, user_id: str) -> None:
        resolved_user = self._normalize_user_id(user_id)
        accessible_projects = self._visible_project_ids(resolved_user)
        if project_id not in accessible_projects:
            raise ValueError(f"Project not accessible: {project_id}")

    def _sanitize_file_component(self, value: str, fallback: str) -> str:
        cleaned = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-._")
        return cleaned or fallback

    def _normalized_file_extension(self, file_name: str) -> str:
        suffix = Path(file_name).suffix.lower()
        if not suffix:
            return ""
        return suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""

    def _guess_mime_type(self, file_name: str, declared_type: str = "") -> str:
        if declared_type and declared_type != "application/octet-stream":
            return declared_type
        guessed, _ = mimetypes.guess_type(file_name)
        return guessed or "application/octet-stream"

    def _asset_relative_path(self, kind: str, project_id: str, asset_id: str, extension: str) -> str:
        project_token = self._sanitize_file_component(project_id, "project")
        return str(Path(kind) / project_token / f"{asset_id}{extension}")

    def _asset_absolute_path(self, relative_path: str) -> Path:
        return self.store.binary_path("files", relative_path)

    def _assert_file_size(self, payload: bytes) -> None:
        if not payload:
            raise ValueError("File is empty")
        if len(payload) > MAX_TEMPLATE_FILE_BYTES:
            raise ValueError(f"File exceeds {MAX_TEMPLATE_FILE_BYTES // (1024 * 1024)} MB limit")

    def _normalize_template_category(self, category: str) -> str:
        normalized = self._sanitize_file_component(category, "general")
        return normalized.replace(".", "-")

    def _template_file_name(self, name: str, extension: str) -> str:
        stem = self._sanitize_file_component(name, "document")
        return f"{stem}{extension}"

    def _ensure_table(self, table_name: str, columns: list[str]) -> None:
        if not self.store.exists(table_name):
            self.store.write_table(table_name, pd.DataFrame(columns=columns))
            return
        dataframe = self.store.read_table(table_name)
        missing = [column for column in columns if column not in dataframe.columns]
        if not missing:
            return
        for column in missing:
            dataframe[column] = ""
        self.store.write_table(table_name, dataframe)

    def _touch_project(self, project_id: str) -> None:
        projects = self.store.read_table(TABLE_BOARD_GOALS)
        if projects.empty:
            return
        match = projects.index[projects["project_id"] == project_id]
        if len(match) == 0:
            return
        projects.at[match[0], "updated_at"] = utc_now()
        self.store.write_table(TABLE_BOARD_GOALS, projects)

    def _touch_session(
        self,
        session_id: str,
        *,
        user_id: str,
        project_id: str,
        client_type: str,
        top_skill_id: str = "",
        active_skill_id: str = "",
    ) -> None:
        sessions = self.store.read_table(TABLE_MEMORY_SESSIONS)
        resolved_user_id = self._normalize_user_id(user_id)
        resolved_project_id = project_id or self._default_project_id_for_user(resolved_user_id)
        match = sessions.index[(sessions["session_id"] == session_id) & (sessions["user_id"] == resolved_user_id)]
        if len(match) == 0:
            row = {
                "session_id": session_id,
                "user_id": resolved_user_id,
                "project_id": resolved_project_id,
                "client_type": client_type,
                "status": "active",
                "top_skill_id": top_skill_id,
                "active_skill_id": active_skill_id or top_skill_id,
                "last_used_at": utc_now(),
            }
            sessions = pd.concat([sessions, pd.DataFrame([row])], ignore_index=True)
        else:
            row_index = match[0]
            sessions.at[row_index, "status"] = "active"
            sessions.at[row_index, "project_id"] = resolved_project_id
            sessions.at[row_index, "client_type"] = client_type
            if top_skill_id:
                sessions.at[row_index, "top_skill_id"] = top_skill_id
            if active_skill_id:
                sessions.at[row_index, "active_skill_id"] = active_skill_id
            sessions.at[row_index, "last_used_at"] = utc_now()
        self.store.write_table(TABLE_MEMORY_SESSIONS, sessions)

    def _append_rows(self, table_name: str, rows: list[dict[str, object]]) -> None:
        current = self.store.read_table(table_name)
        updated = pd.concat([current, pd.DataFrame(rows)], ignore_index=True)
        self.store.write_table(table_name, updated)

    def _append_memory(
        self,
        *,
        scope: str,
        user_id: str,
        project_id: str,
        session_id: str,
        memory_type: str,
        subject_id: str,
        skill_id: str,
        summary: str,
    ) -> None:
        self._append_rows(
            TABLE_MEMORY_MEMORIES,
            [
                {
                    "memory_id": str(uuid4()),
                    "scope": scope,
                    "user_id": user_id,
                    "project_id": project_id,
                    "session_id": session_id,
                    "memory_type": memory_type,
                    "subject_id": subject_id,
                    "skill_id": skill_id,
                    "summary": summary,
                    "created_at": utc_now(),
                }
            ],
        )

    def _seed_memory_files(self) -> None:
        config = self.store.read_table(TABLE_MEMORY_CONFIG)
        if config.empty:
            self.store.write_table(
                TABLE_MEMORY_CONFIG,
                pd.DataFrame(
                    [
                        {
                            "config_key": "runtime_mode",
                            "config_value": "centralized-multi-user",
                            "updated_at": utc_now(),
                        }
                    ]
                ),
            )
        self.store.write_json("memory", "pulse.json", {"status": "ready", "updated_at": utc_now()})
        self.store.write_json("memory", "disabled.json", {"skills": [], "routes": []})
        self.store.write_json("memory", "disabled_payload.json", {"payloads": []})

    def _seed_memory_triggers(self) -> None:
        triggers = self.store.read_table(TABLE_MEMORY_TRIGGERS)
        if not triggers.empty:
            active_titles = {str(row.get("title", "")).strip().lower() for row in triggers.to_dict(orient="records")}
        else:
            active_titles = set()

        default_rows = [
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "recall",
                "title": "Recall before follow-up",
                "trigger_text": "Before asking the user for more information, recall project, user, and enterprise memories relevant to the unresolved topic.",
                "action_text": "Call recall_memories first. Only ask the user if the remaining issue is critical, stale, or contradictory.",
                "category": "question",
                "client_type": "any",
                "weight": 10,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "recall",
                "title": "Recall on skill activation",
                "trigger_text": "When a new specialist skill is activated, pull relevant project memories before continuing the flow.",
                "action_text": "Call recall_memories using the project_id and the active skill domain so the worker starts with the existing brief.",
                "category": "handoff",
                "client_type": "any",
                "weight": 9,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "store",
                "title": "Store confirmed requirement",
                "trigger_text": "A user or authoritative worker confirms business behavior, constraints, or workflow rules.",
                "action_text": "Call store_memory with category=requirement or constraint, status=confirmed, and explicit tags.",
                "category": "requirement",
                "client_type": "any",
                "weight": 9,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "store",
                "title": "Store resolved decision",
                "trigger_text": "A business, design, technical, or delivery decision is made and should survive handoff.",
                "action_text": "Call store_memory with category=decision, decision_scope set, and owner/source filled in.",
                "category": "decision",
                "client_type": "any",
                "weight": 9,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "store",
                "title": "Store bounded assumption",
                "trigger_text": "The agent makes a safe bounded assumption instead of escalating a routine issue to the end user.",
                "action_text": "Call store_memory with category=assumption so later workers understand what was carried forward.",
                "category": "assumption",
                "client_type": "any",
                "weight": 8,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "store",
                "title": "Store handoff note",
                "trigger_text": "A specialist hands off work, changes plan, or finishes a phase that another worker will pick up later.",
                "action_text": "Call store_memory with category=handoff and capture the downstream context that should not be rediscovered.",
                "category": "handoff",
                "client_type": "any",
                "weight": 8,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "update",
                "title": "Update contradictory memory",
                "trigger_text": "New evidence contradicts an existing memory or replaces an outdated decision.",
                "action_text": "Use update_memory or superseding store_memory so the older memory is marked superseded instead of silently drifting.",
                "category": "decision",
                "client_type": "any",
                "weight": 8,
                "active": True,
            },
            {
                "trigger_id": str(uuid4()),
                "skill_id": "",
                "trigger_kind": "security",
                "title": "Warn before guarded writes",
                "trigger_text": "Before writing files, tables, secrets, or governed storage in Databricks or another managed environment, surface a security warning.",
                "action_text": "Announce a Security Warning header, explain the likely corporate guardrail, and do not ask the user to bypass it. Stop if policy blocks the write.",
                "category": "security",
                "client_type": "genie-code,web,api,ide",
                "weight": 10,
                "active": True,
            },
        ]

        rows_to_add = [row for row in default_rows if row["title"].strip().lower() not in active_titles]
        if rows_to_add:
            self._append_rows(TABLE_MEMORY_TRIGGERS, rows_to_add)

    def _detect_complexity(self, prompt: str) -> str:
        lowered = prompt.lower()
        word_count = len(tokenize(prompt))
        expert_markers = ["architecture", "workflow", "migrate", "governance", "platform", "cross-system"]
        deep_markers = [
            "build", "implement", "review", "release", "validate", "design",
            "activate", "route", "plan", "website", "application", "project",
            "system", "product", "service", "deploy", "create app",
        ]
        if any(marker in lowered for marker in expert_markers):
            return "expert"
        if any(marker in lowered for marker in deep_markers) or word_count > 20:
            return "deep"
        if word_count > 8:
            return "standard"
        return "simple"

    def _rank_skills(self, skills: pd.DataFrame, query: str) -> pd.DataFrame:
        if skills.empty:
            return skills

        ranked = skills.copy()
        ranked["search_score"] = 0.0
        tokens = sorted(set(tokenize(query, filter_stops=True)))
        if not tokens:
            return ranked.sort_values("display_name")

        for token in tokens:
            ranked["search_score"] += ranked["search_text"].str.contains(token, case=False).astype(float)
            ranked["search_score"] += ranked["description"].str.contains(token, case=False).astype(float) * 0.5
            ranked["search_score"] += ranked["display_name"].str.contains(token, case=False).astype(float) * 1.5

        filtered = ranked.loc[ranked["search_score"] > 0].copy()
        if filtered.empty:
            filtered = ranked.copy()
        return filtered.sort_values(["search_score", "display_name"], ascending=[False, True])

    def _latest_route(self, session_id: str, user_id: str) -> dict[str, object] | None:
        routes = self.store.read_table(TABLE_MEMORY_ROUTE)
        if routes.empty:
            return None
        filtered = routes.loc[(routes["session_id"] == session_id) & (routes["user_id"] == user_id)]
        if filtered.empty:
            return None
        return filtered.sort_values("created_at", ascending=False).iloc[0].to_dict()

    def _prompt_scope_match(self, skill_id: str, prompt: str) -> bool:
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        prompt_tokens = set(tokenize(prompt))
        skill_tokens = set(tokenize(str(skill.get("description", "")) + " " + str(skill.get("name", ""))))
        return len(prompt_tokens & skill_tokens) > 0

    def _route_match_for_skill(self, skill_id: str) -> dict[str, object] | None:
        skill = self.get_skill(skill_id)
        if not skill:
            return None
        return {
            "skill_id": skill["skill_id"],
            "display_name": skill["display_name"],
            "description": skill["description"],
            "search_score": 999.0 if skill_id == ORCHESTRATOR_SKILL_ID else float(skill.get("search_score", 0) or 0),
        }

    def _start_hiring_process(
        self,
        *,
        session_id: str,
        user_id: str,
        project_id: str,
        client_type: str,
        prompt: str,
    ) -> None:
        hiring_skill = self.get_skill(HIRING_SKILL_ID)
        if not hiring_skill:
            return

        self.create_work_item(
            CreateWorkItemRequest(
                project_id=project_id,
                user_id=user_id,
                title="Start hiring process for missing skill coverage",
                summary=f"No specialist skill matched strongly for prompt: {prompt[:240]}",
                stage="backlog",
                owner_skill_id=HIRING_SKILL_ID,
                owner_display_name=str(hiring_skill.get("display_name", "Talent Director")),
                priority="high",
            )
        )
        self.record_skill_event(
            SkillEventRequest(
                session_id=session_id,
                user_id=user_id,
                project_id=project_id,
                skill_id=HIRING_SKILL_ID,
                event_type="hiring_process_started",
                status="info",
                summary="No suitable specialist skill found. Hiring process started via TalentDirector.",
                payload={"prompt": prompt, "client_type": client_type},
            )
        )
