from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .config import Settings
from .storage import ParquetStore
from .tables import (
    TABLE_DECISION_LOG,
    TABLE_JOB_POSTING,
    TABLE_PERSON_DEFINITION_CHECKLIST,
    TABLE_ROLE_QUALIFICATION_RULES,
    TABLE_SKILL_IDENTITY,
    TABLE_SKILL_REGISTRY,
    TABLE_SKILL_TRAIT_PROFILES,
    TABLE_SKILL_VERSION,
)


GATE_NAMES = {
    0: "router",
    1: "definition",
    2: "execution",
    3: "specialist",
    4: "full",
}

SKILL_SECTION_GATES = {
    "Purpose": 1,
    "Use This Skill When": 1,
    "Do Not Use This Skill When": 1,
    "Required Inputs": 2,
    "Expected Outputs": 2,
    "Operating Rules": 2,
    "Completion Standard": 2,
    "Default Posture Under Sparse Prompts": 3,
}

SUPPORT_FILE_GATES = {
    "workflow.md": 3,
    "handoffs.md": 3,
    "anti-patterns.md": 3,
    "decision-tree.md": 4,
    "examples.md": 4,
    "identity.md": 4,
    "job-description.md": 4,
    "persona.md": 4,
    "responsibilities.md": 4,
    "resume.md": 4,
    "review-checklist.md": 4,
    "starter-prompts.md": 4,
    "story.md": 4,
    "soul.md": 4,
    "SUMMARY.md": 4,
    "templates.md": 4,
}

IDENTITY_GATE_MAP = {
    "metadata/authority.md": 1,
    "metadata/capabilities.md": 1,
    "jobPosting.md": 1,
    "metadata/reasoning.md": 2,
    "metadata/workflows.md": 2,
    "metadata/handoffs.md": 2,
    "persona/personality.md": 3,
    "persona/beliefs.md": 3,
    "persona/expertise.md": 3,
    "persona/scars.md": 3,
    "persona/origin.md": 3,
    "governance-review.md": 4,
    "lore-briefing.md": 4,
    "naming-assessment.md": 4,
    "README.md": 4,
}


@dataclass
class CompiledSkill:
    skill_row: dict[str, object]
    bundles: list[dict[str, object]]
    job_posting_row: dict[str, object]
    trait_rows: list[dict[str, object]]
    version_row: dict[str, object]


def parse_frontmatter(document: str) -> tuple[dict[str, str], str]:
    if not document.startswith("---"):
        return {}, document

    lines = document.splitlines()
    metadata: dict[str, str] = {}
    body_start = 0
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            body_start = index + 1
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    body = "\n".join(lines[body_start:]).strip()
    return metadata, body


def parse_markdown_sections(document: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_title: str | None = None
    current_lines: list[str] = []

    for line in document.splitlines():
        if line.startswith("## "):
            if current_title:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = []
            continue
        if line.startswith("# "):
            continue
        if current_title:
            current_lines.append(line)

    if current_title:
        sections[current_title] = "\n".join(current_lines).strip()

    return sections


def pretty_title(file_name: str) -> str:
    stem = Path(file_name).stem
    return stem.replace("-", " ").replace("_", " ").title()


def humanize_name(name: str) -> str:
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", name.replace("-", " ").replace("_", " "))
    return re.sub(r"\s+", " ", spaced).strip().title()


def strip_markup(text: str) -> str:
    stripped = re.sub(r"<[^>]+>", " ", text)
    stripped = re.sub(r"`([^`]+)`", r"\1", stripped)
    stripped = re.sub(r"[*_>#-]", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip()


def extract_display_name(summary_text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", summary_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def extract_packet_level(summary_text: str) -> str:
    match = re.search(r"Packet Level</strong></td><td>([^<]+)</td>", summary_text)
    if match:
        return match.group(1).strip()
    return "unknown"


def read_optional(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8").strip()


def first_meaningful_paragraph(*documents: str) -> str:
    for document in documents:
        for paragraph in document.split("\n\n"):
            cleaned = strip_markup(paragraph)
            if len(cleaned) >= 20:
                return cleaned
    return ""


def content_excerpt(text: str, limit: int = 600) -> str:
    cleaned = strip_markup(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def trait_type_for_source(source_file: str) -> str:
    normalized = source_file.replace("\\", "/").lower()
    if "persona/" in normalized:
        return f"persona:{Path(normalized).stem}"
    return Path(normalized).stem


class SkillCompiler:
    def __init__(self, settings: Settings, store: ParquetStore) -> None:
        self.settings = settings
        self.store = store

    def compile(self) -> dict[str, int]:
        skill_rows: list[dict[str, object]] = []
        bundle_rows: list[dict[str, object]] = []
        job_posting_rows: list[dict[str, object]] = []
        trait_rows: list[dict[str, object]] = []
        version_rows: list[dict[str, object]] = []

        if self.settings.skill_source_dir.exists():
            for skill_dir in sorted(self.settings.skill_source_dir.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue
                compiled_skill = self._compile_skill(skill_dir)
                skill_rows.append(compiled_skill.skill_row)
                bundle_rows.extend(compiled_skill.bundles)
                job_posting_rows.append(compiled_skill.job_posting_row)
                trait_rows.extend(compiled_skill.trait_rows)
                version_rows.append(compiled_skill.version_row)

        if self.settings.identity_source_dir.exists():
            for skill_dir in sorted(self.settings.identity_source_dir.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                    continue
                if not ((skill_dir / "metadata").exists() or (skill_dir / "persona").exists()):
                    continue
                compiled_skill = self._compile_identity_skill(skill_dir)
                skill_rows.append(compiled_skill.skill_row)
                bundle_rows.extend(compiled_skill.bundles)
                job_posting_rows.append(compiled_skill.job_posting_row)
                trait_rows.extend(compiled_skill.trait_rows)
                version_rows.append(compiled_skill.version_row)

        self.store.write_table(TABLE_SKILL_REGISTRY, pd.DataFrame(skill_rows))
        self.store.write_table(TABLE_SKILL_IDENTITY, pd.DataFrame(bundle_rows))
        self.store.write_table(TABLE_JOB_POSTING, pd.DataFrame(job_posting_rows))
        self.store.write_table(TABLE_SKILL_TRAIT_PROFILES, pd.DataFrame(trait_rows))
        self.store.write_table(TABLE_SKILL_VERSION, pd.DataFrame(version_rows))
        self.store.write_table(TABLE_DECISION_LOG, pd.DataFrame(columns=["decision_id", "skill_id", "decision_type", "detail", "created_at"]))
        self._compile_identity_templates()

        return {"skills": len(skill_rows), "bundles": len(bundle_rows)}

    def _compile_skill(self, skill_dir: Path) -> CompiledSkill:
        skill_id = skill_dir.name
        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        summary_path = skill_dir / "SUMMARY.md"
        summary_text = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""

        frontmatter, skill_body = parse_frontmatter(skill_text)
        skill_sections = parse_markdown_sections(skill_body)

        fallback_name = frontmatter.get("name", skill_id)
        display_name = extract_display_name(summary_text, fallback_name.replace("-", " ").title())
        description = frontmatter.get("description", "").strip()
        purpose = skill_sections.get("Purpose", "").strip()
        use_when = skill_sections.get("Use This Skill When", "").strip()
        do_not_use = skill_sections.get("Do Not Use This Skill When", "").strip()

        search_text = strip_markup(
            " ".join(
                [
                    skill_id,
                    fallback_name,
                    display_name,
                    description,
                    purpose,
                    use_when,
                    do_not_use,
                    summary_text[:2500],
                ]
            )
        )

        skill_row = {
            "skill_id": skill_id,
            "slug": skill_id,
            "name": fallback_name,
            "display_name": display_name,
            "description": description,
            "packet_level": extract_packet_level(summary_text),
            "source_dir": str(skill_dir.relative_to(self.settings.repo_root)),
            "source_format": "codex-packet",
            "search_text": search_text,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        bundles: list[dict[str, object]] = []
        sort_order = 0

        bundles.append(
            {
                "bundle_id": str(uuid4()),
                "skill_id": skill_id,
                "gate_level": 0,
                "gate_name": GATE_NAMES[0],
                "title": "Router Summary",
                "content": "\n\n".join(
                    part
                    for part in [
                        description,
                        purpose,
                        "Use when:\n" + use_when if use_when else "",
                        "Do not use when:\n" + do_not_use if do_not_use else "",
                    ]
                    if part
                ).strip(),
                "source_file": "SKILL.md",
                "sort_order": sort_order,
            }
        )
        sort_order += 1

        for title, gate_level in SKILL_SECTION_GATES.items():
            content = skill_sections.get(title, "").strip()
            if not content:
                continue
            bundles.append(
                {
                    "bundle_id": str(uuid4()),
                    "skill_id": skill_id,
                    "gate_level": gate_level,
                    "gate_name": GATE_NAMES[gate_level],
                    "title": title,
                    "content": content,
                    "source_file": "SKILL.md",
                    "sort_order": sort_order,
                }
            )
            sort_order += 1

        for file_name, gate_level in SUPPORT_FILE_GATES.items():
            file_path = skill_dir / file_name
            if not file_path.exists():
                continue
            bundles.append(
                {
                    "bundle_id": str(uuid4()),
                    "skill_id": skill_id,
                    "gate_level": gate_level,
                    "gate_name": GATE_NAMES[gate_level],
                    "title": pretty_title(file_name),
                    "content": file_path.read_text(encoding="utf-8").strip(),
                    "source_file": file_name,
                    "sort_order": sort_order,
                }
            )
            sort_order += 1

        trait_rows = self._build_trait_rows(skill_id, display_name, skill_row["source_format"], bundles)
        job_posting_row = {
            "job_posting_id": str(uuid4()),
            "skill_id": skill_id,
            "display_name": display_name,
            "description": description,
            "job_posting": content_excerpt(
                "\n\n".join(
                    section
                    for section in [
                        description,
                        purpose,
                        "Use when:\n" + use_when if use_when else "",
                        "Do not use when:\n" + do_not_use if do_not_use else "",
                    ]
                    if section
                )
            ),
            "source_file": "SKILL.md",
            "updated_at": skill_row["updated_at"],
        }
        version_row = {
            "version_id": str(uuid4()),
            "skill_id": skill_id,
            "source_format": skill_row["source_format"],
            "source_dir": skill_row["source_dir"],
            "bundle_count": len(bundles),
            "compiled_at": skill_row["updated_at"],
        }

        return CompiledSkill(
            skill_row=skill_row,
            bundles=bundles,
            job_posting_row=job_posting_row,
            trait_rows=trait_rows,
            version_row=version_row,
        )

    def _compile_identity_skill(self, skill_dir: Path) -> CompiledSkill:
        skill_id = skill_dir.name
        readme_text = read_optional(skill_dir / "README.md")
        job_posting = read_optional(skill_dir / "jobPosting.md")
        capabilities = read_optional(skill_dir / "metadata" / "capabilities.md")
        authority = read_optional(skill_dir / "metadata" / "authority.md")
        reasoning = read_optional(skill_dir / "metadata" / "reasoning.md")
        workflows = read_optional(skill_dir / "metadata" / "workflows.md")
        handoffs = read_optional(skill_dir / "metadata" / "handoffs.md")
        beliefs = read_optional(skill_dir / "persona" / "beliefs.md")
        expertise = read_optional(skill_dir / "persona" / "expertise.md")
        origin = read_optional(skill_dir / "persona" / "origin.md")
        personality = read_optional(skill_dir / "persona" / "personality.md")
        scars = read_optional(skill_dir / "persona" / "scars.md")

        fallback_name = humanize_name(skill_id)
        display_name = extract_display_name(readme_text, fallback_name)
        description = first_meaningful_paragraph(job_posting, capabilities, authority, readme_text) or (
            f"{display_name} identity packet compiled from metadata and persona source files."
        )

        search_text = strip_markup(
            " ".join(
                [
                    skill_id,
                    fallback_name,
                    display_name,
                    description,
                    capabilities,
                    authority,
                    reasoning,
                    workflows,
                    handoffs,
                    beliefs,
                    expertise,
                    origin,
                    personality,
                    scars,
                    readme_text,
                ]
            )
        )

        compiled_at = datetime.now(UTC).isoformat()
        skill_row = {
            "skill_id": skill_id,
            "slug": skill_id,
            "name": fallback_name,
            "display_name": display_name,
            "description": description,
            "packet_level": "identity-packet",
            "source_dir": str(skill_dir.relative_to(self.settings.repo_root)),
            "source_format": "identity-v6",
            "search_text": search_text,
            "updated_at": compiled_at,
        }

        bundles: list[dict[str, object]] = []
        sort_order = 0

        router_summary = "\n\n".join(
            section
            for section in [
                description,
                "Authority\n" + authority if authority else "",
                "Capabilities\n" + capabilities if capabilities else "",
                "Job Posting\n" + job_posting if job_posting else "",
            ]
            if section
        ).strip()
        bundles.append(
            {
                "bundle_id": str(uuid4()),
                "skill_id": skill_id,
                "gate_level": 0,
                "gate_name": GATE_NAMES[0],
                "title": "Router Summary",
                "content": router_summary,
                "source_file": "identity",
                "sort_order": sort_order,
            }
        )
        sort_order += 1

        for relative_path, gate_level in IDENTITY_GATE_MAP.items():
            file_path = skill_dir / Path(relative_path)
            content = read_optional(file_path)
            if not content:
                continue
            bundles.append(
                {
                    "bundle_id": str(uuid4()),
                    "skill_id": skill_id,
                    "gate_level": gate_level,
                    "gate_name": GATE_NAMES[gate_level],
                    "title": pretty_title(relative_path),
                    "content": content,
                    "source_file": relative_path.replace("\\", "/"),
                    "sort_order": sort_order,
                }
            )
            sort_order += 1

        trait_rows = self._build_trait_rows(skill_id, display_name, skill_row["source_format"], bundles)
        job_posting_row = {
            "job_posting_id": str(uuid4()),
            "skill_id": skill_id,
            "display_name": display_name,
            "description": description,
            "job_posting": content_excerpt(job_posting or router_summary),
            "source_file": "jobPosting.md" if job_posting else "identity",
            "updated_at": compiled_at,
        }
        version_row = {
            "version_id": str(uuid4()),
            "skill_id": skill_id,
            "source_format": skill_row["source_format"],
            "source_dir": skill_row["source_dir"],
            "bundle_count": len(bundles),
            "compiled_at": compiled_at,
        }

        return CompiledSkill(
            skill_row=skill_row,
            bundles=bundles,
            job_posting_row=job_posting_row,
            trait_rows=trait_rows,
            version_row=version_row,
        )

    def _build_trait_rows(
        self,
        skill_id: str,
        display_name: str,
        source_format: str,
        bundles: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        trait_rows: list[dict[str, object]] = []
        for bundle in bundles:
            source_file = str(bundle["source_file"])
            gate_level = int(bundle["gate_level"])
            if gate_level < 3 and "persona/" not in source_file.replace("\\", "/").lower():
                continue
            title = str(bundle["title"])
            if title == "Router Summary":
                continue
            trait_rows.append(
                {
                    "trait_id": str(uuid4()),
                    "skill_id": skill_id,
                    "display_name": display_name,
                    "source_format": source_format,
                    "trait_type": trait_type_for_source(source_file),
                    "gate_level": gate_level,
                    "title": title,
                    "content": content_excerpt(str(bundle["content"])),
                    "source_file": source_file,
                }
            )
        return trait_rows

    def _compile_identity_templates(self) -> None:
        templates_dir = self.settings.identity_source_dir / "_templates"
        checklist_csv = templates_dir / "person-definition-checklist.csv"
        rules_csv = templates_dir / "role-qualification-rules.csv"

        if checklist_csv.exists():
            checklist_df = pd.read_csv(checklist_csv)
            self.store.write_table(TABLE_PERSON_DEFINITION_CHECKLIST, checklist_df)

        if rules_csv.exists():
            rules_df = pd.read_csv(rules_csv)
            self.store.write_table(TABLE_ROLE_QUALIFICATION_RULES, rules_df)
