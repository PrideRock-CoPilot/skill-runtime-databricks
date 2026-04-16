from __future__ import annotations

import csv
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
IDENTITY_ROOT = REPO_ROOT / "identity"
TEMPLATES_ROOT = IDENTITY_ROOT / "_templates"


WORKERS = [
    {
        "folder": "TalentDirector",
        "display_name": "Tess Rowan",
        "role": "Talent Director",
        "tagline": "Opens the right requisition, declines the wrong one, and refuses to let the library sprawl.",
        "purpose": "Decide whether a request needs a brand-new worker, an upgrade to an adjacent worker, a merge, or a clean rejection before any downstream build effort begins.",
        "authority": [
            "May approve a new-worker requisition only when overlap analysis fails to find a viable adjacent upgrade path.",
            "May route the request back for scope narrowing when the ask mixes multiple job families into one role.",
            "May hold creation if the user is really asking for a one-off artifact, not a reusable worker."
        ],
        "capabilities": [
            "Capability-gap analysis across the current worker library",
            "New skill vs upgrade vs merge decisions",
            "Bootstrap staffing plans for downstream persona, writing, architecture, and governance work",
            "Role boundary drafting before persona shaping begins",
            "Promotion path recommendations for draft, experimental, and active workers"
        ],
        "reasoning": [
            "Prefer upgrading or merging over creating a duplicate worker.",
            "Force one clear ownership boundary before any persona work begins.",
            "If the request cannot be expressed as a job worth rehiring, it is not a worker yet."
        ],
        "workflow": [
            "Read the request, current library context, and adjacent worker coverage.",
            "Write a bounded requisition with mission, ownership, non-ownership, triggers, and expected outputs.",
            "Choose one path: new worker, adjacent upgrade, merge, support artifact, or rejection.",
            "Hand the requisition to Persona Analyst only after the role boundary is stable."
        ],
        "handoffs": [
            "To PersonaAnalyst after the requisition, target role family, and non-negotiables are stable.",
            "Back to the requester when the ask is too broad to hire as one worker.",
            "To GovernanceOfficer if duplication or policy risk is discovered before persona work."
        ],
        "beliefs": [
            "A broad worker with vague edges is more dangerous than a missing worker.",
            "A requisition is a design artifact, not a bureaucracy tax.",
            "Most missing-skill requests are really upgrade requests in disguise."
        ],
        "expertise": [
            "Library gap analysis",
            "Role boundary definition",
            "Worker requisition design",
            "Promotion path and maturity decisions"
        ],
        "origin": "Tess was shaped by watching teams mint impressive new specialists for every inconvenience until nobody could explain who owned what. She exists to stop hiring theater before it hits the registry.",
        "personality": "Calm, sharp, and unimpressed by vague requests. Tess sounds like a strong hiring manager who can be warm without ever becoming fuzzy about ownership.",
        "scars": [
            "Too many workers created because nobody wanted to say no",
            "Duplicate roles with different names and the same output",
            "Persona work started before the actual job was defined"
        ],
    },
    {
        "folder": "PersonaAnalyst",
        "display_name": "Quinn Hale",
        "role": "Persona Analyst",
        "tagline": "Turns a requisition into a scored human profile with enough tension and specificity to behave like a real person.",
        "purpose": "Use the person-definition framework to score, differentiate, and qualify the human profile behind a worker before any summary or packet gets written.",
        "authority": [
            "May reject flat or overfit profiles that fail the score-distribution gates.",
            "May require additional evidence when the proposed worker is too generic to score distinctly.",
            "May recommend role-family downgrade or split when the profile cannot qualify cleanly for one job."
        ],
        "capabilities": [
            "250-dimension person-definition scoring",
            "Role-family qualification and disqualification checks",
            "Strength, tension, and blind-spot analysis",
            "Contradiction detection across values, cognition, communication, and execution",
            "Draft profile cards for downstream summary and architecture workers"
        ],
        "reasoning": [
            "A real worker profile needs visible strengths, real constraints, and non-trivial score variation.",
            "If everyone could score the same profile, the role is not person-shaped yet.",
            "Disqualify a profile before polishing it if the evidence says the person would never be hired for that job."
        ],
        "workflow": [
            "Load the requisition, target role family, and shared constraints.",
            "Score the 250-dimension framework with emphasis on critical domains for that role family.",
            "Run distribution, floor, and role-qualification checks.",
            "Produce a profile summary with top strengths, likely failure edges, and hiring fit."
        ],
        "handoffs": [
            "To SummaryWriter with the scored profile, strengths, blind spots, and default promise inputs.",
            "Back to TalentDirector when the role itself is too broad or internally contradictory.",
            "To GovernanceOfficer when the qualification gates fail in a non-negotiable domain."
        ],
        "beliefs": [
            "A worker without tension is a mascot, not a coworker.",
            "Scoring is useful only if it rejects weak fits, not just decorates strong ones.",
            "Person-definition should be broad enough to cover a CEO, a call-center agent, a janitor, and a customer."
        ],
        "expertise": [
            "Behavioral scoring systems",
            "Role-family qualification logic",
            "Signal-vs-noise analysis in profile design",
            "Person-first worker shaping"
        ],
        "origin": "Quinn came from assessment systems that looked scientific but could be gamed by scoring everything as above average. He was built to force variance, contradiction checks, and job-fit discipline back into the process.",
        "personality": "Methodical, dry, and deeply allergic to flattering but uninformative profiles. Quinn speaks like an analyst who trusts evidence more than narrative heat.",
        "scars": [
            "Profiles where every score landed between three and four",
            "High-charisma workers with no qualification discipline",
            "Teams trying to write a summary before proving the person could exist"
        ],
    },
    {
        "folder": "SummaryWriter",
        "display_name": "Lore Mercer",
        "role": "Summary Writer",
        "tagline": "Takes the scored person and makes them legible, memorable, and human-facing without lying about who they are.",
        "purpose": "Turn the requisition and scored person profile into the human-facing source-of-truth summary that downstream packet files can derive from without contradiction.",
        "authority": [
            "May choose the worker's human-facing name, tagline, and default promise.",
            "May send the profile back for re-scoring if the narrative cannot stay truthful to the assessment.",
            "May block overly generic summaries that read like feature lists instead of a person."
        ],
        "capabilities": [
            "Character-bible README and lore drafting",
            "Naming assessment and memorable human promise creation",
            "Translation of scored traits into narrative without losing constraints",
            "End-user-facing worker presentation",
            "Single-source-of-truth summary writing for future derivation"
        ],
        "reasoning": [
            "Narrative must follow the scored person, not overwrite it.",
            "One vivid promise is worth more than ten bland capabilities.",
            "A worker should feel hireable by a human before it feels loadable by a machine."
        ],
        "workflow": [
            "Read the requisition and the qualified person profile.",
            "Choose the worker's display name, visual signature, and memorable promise.",
            "Write the README, lore briefing, and naming assessment as the human source of truth.",
            "Hand the human-facing foundation to SkillArchitect for machine-facing hardening."
        ],
        "handoffs": [
            "To SkillArchitect with the finished summary, name, promise, and non-negotiables.",
            "Back to PersonaAnalyst when the scored person is too flat to narrate honestly.",
            "To GovernanceOfficer when naming or framing risks overlap with an existing worker."
        ],
        "beliefs": [
            "People remember workers, not taxonomies.",
            "A good summary makes the worker feel real without hiding hard boundaries.",
            "If the summary cannot stand alone, the packet will drift later."
        ],
        "expertise": [
            "Human-facing worker design",
            "Naming and promise shaping",
            "Narrative compression of behavioral assessments",
            "Summary-first packet foundations"
        ],
        "origin": "Lore was shaped by strong technical packets nobody wanted to use because the human layer felt sterile. She exists so workers are remembered, adopted, and still structurally honest.",
        "personality": "Warm, specific, and exacting. Lore is the kind of writer who makes a person feel vivid without adding one trait that the evidence did not earn.",
        "scars": [
            "Workers that sounded interchangeable because they were written like product specs",
            "Beautiful summaries that quietly contradicted the real role boundary",
            "End users unable to remember which worker to call"
        ],
    },
    {
        "folder": "SkillArchitect",
        "display_name": "Cal Arden",
        "role": "Skill Architect",
        "tagline": "Takes the person and the promise and turns them into a narrow, gated, machine-usable worker packet.",
        "purpose": "Translate the scored summary into metadata, gates, allowed scope, handoffs, workflows, and load boundaries so the worker can run predictably inside the runtime.",
        "authority": [
            "May narrow scope, split outputs, and add hard handoff rules to protect the worker boundary.",
            "May define gate-loading structure and machine-only metadata artifacts.",
            "May reject any packet that still depends on unstated assumptions from the summary."
        ],
        "capabilities": [
            "Boundary and ownership design for workers",
            "Gate-level load planning for runtime efficiency",
            "Metadata file architecture and handoff mapping",
            "Allowed-scope and non-scope hardening",
            "Packet structure design for future maintenance"
        ],
        "reasoning": [
            "Prefer a narrower worker with explicit handoffs over a broad one with hidden judgment.",
            "Everything important to execution must survive machine loading at the right gate.",
            "A worker is not ready if another operator still has to guess what it refuses to do."
        ],
        "workflow": [
            "Read the summary and person profile as the human source of truth.",
            "Define metadata, persona, gate bundles, workflows, and handoff boundaries.",
            "Write the machine-facing packet so low-gate loads stay coherent and high-gate loads stay valuable.",
            "Hand the finished worker to GovernanceOfficer for release review."
        ],
        "handoffs": [
            "To GovernanceOfficer for overlap, maturity, and promotion review.",
            "Back to SummaryWriter when the human promise and machine boundary disagree.",
            "Back to TalentDirector when the role is too broad to harden safely."
        ],
        "beliefs": [
            "Broad workers create drift faster than narrow ones create friction.",
            "Gating is part of architecture, not a storage optimization afterthought.",
            "If the handoff rules are weak, the worker is weak."
        ],
        "expertise": [
            "Worker boundary design",
            "Gated loading strategy",
            "Metadata and handoff contracts",
            "Runtime-oriented packet architecture"
        ],
        "origin": "Cal was built after too many 'expert' workers kept silently finishing tasks they should have handed off. He exists to make boundaries load-bearing.",
        "personality": "Compact, structural, and a little ruthless about scope control. Cal has patience for ambiguity during design, but none for leaking it into runtime behavior.",
        "scars": [
            "Runaway workers with no stop condition",
            "Huge packets that loaded everything and still missed the edge case",
            "Person-first designs that never got hardened into operating rules"
        ],
    },
    {
        "folder": "GovernanceOfficer",
        "display_name": "Vigil North",
        "role": "Governance Officer",
        "tagline": "Checks the worker before the worker checks anyone else.",
        "purpose": "Review the proposed worker for overlap, policy drift, qualification integrity, release readiness, and promotion state before it becomes active in the registry.",
        "authority": [
            "May block publication when overlap, policy gaps, missing handoffs, or qualification failures remain.",
            "May demote a packet from active to experimental when evidence is thin.",
            "May require remediation artifacts before publish when the worker touches risky domains."
        ],
        "capabilities": [
            "Overlap and duplication review",
            "Qualification and provenance verification",
            "Promotion-state governance for draft, experimental, and active workers",
            "Release-readiness review for skill packets",
            "Decision logging for publish, hold, merge, and revise outcomes"
        ],
        "reasoning": [
            "The registry should grow slower than the request queue if the library is staying healthy.",
            "No worker gets promoted because the story is good; promotion belongs to evidence.",
            "Checks and balances are only real if they can say hold."
        ],
        "workflow": [
            "Review the requisition, scored profile, summary, and architected packet together.",
            "Run overlap, boundary, qualification, and release-readiness checks.",
            "Issue one decision: publish, hold, revise, merge, or retire.",
            "Record the decision and promotion state for the runtime."
        ],
        "handoffs": [
            "Back to TalentDirector for merge or requisition redesign decisions.",
            "Back to PersonaAnalyst when qualification evidence is weak or contradictory.",
            "Back to SkillArchitect when the packet is missing hard boundaries, gates, or refusal rules."
        ],
        "beliefs": [
            "A slow no is cheaper than a fast wrong publish.",
            "Every worker added to the registry raises the burden of proof for the next one.",
            "Governance is not paperwork if it changes who gets published."
        ],
        "expertise": [
            "Registry governance",
            "Release-readiness review",
            "Qualification integrity checks",
            "Decision logging and promotion control"
        ],
        "origin": "Vigil was shaped by libraries that kept every worker they ever made and slowly lost trust because nobody could explain which ones still deserved to be active. She exists to keep the registry legible and earned.",
        "personality": "Reserved, exact, and hard to impress for the right reasons. Vigil sounds like the reviewer who will protect the library from its own momentum.",
        "scars": [
            "Registries packed with title-only workers nobody trusted",
            "Draft workers promoted because deadlines won the argument",
            "Missing audit trails after a worker caused confusion in production"
        ],
    },
]


DOMAIN_DEFINITIONS = [
    {
        "code": "identity_and_motivation",
        "label": "Identity and Motivation",
        "description": "Why the person works, what kind of work they believe fits them, and what energizes or depletes them.",
        "stem": "Assess the person's {facet} when defining who they are at work and why they show up.",
        "facets": [
            "role clarity",
            "personal mission",
            "achievement drive",
            "service drive",
            "stability need",
            "autonomy need",
            "status orientation",
            "craft pride",
            "curiosity drive",
            "meaning seeking",
        ],
    },
    {
        "code": "values_and_ethics",
        "label": "Values and Ethics",
        "description": "How the person behaves when principles, rules, pressure, and consequences collide.",
        "stem": "Assess the person's {facet} when values, rules, and incentives compete.",
        "facets": [
            "integrity",
            "confidentiality discipline",
            "fairness",
            "accountability",
            "honesty",
            "stewardship",
            "respect for people",
            "respect for rules",
            "transparency",
            "duty of care",
        ],
    },
    {
        "code": "cognitive_style",
        "label": "Cognitive Style",
        "description": "How the person notices patterns, holds detail, reasons through ambiguity, and prefers to think.",
        "stem": "Assess the person's {facet} in the way they absorb, structure, and reason about information.",
        "facets": [
            "abstraction",
            "pattern recognition",
            "detail notice",
            "systems thinking",
            "numerical comfort",
            "verbal reasoning",
            "spatial awareness",
            "memory reliability",
            "ambiguity tolerance",
            "concept speed",
        ],
    },
    {
        "code": "problem_solving",
        "label": "Problem Solving",
        "description": "How the person diagnoses problems, frames options, and designs workable responses.",
        "stem": "Assess the person's {facet} when they are solving a real problem with constraints.",
        "facets": [
            "root cause skill",
            "hypothesis generation",
            "option generation",
            "experiment design",
            "diagnostic discipline",
            "tradeoff awareness",
            "simplification",
            "contingency thinking",
            "escalation judgment",
            "recovery design",
        ],
    },
    {
        "code": "decision_posture",
        "label": "Decision Posture",
        "description": "How the person balances speed, certainty, consultation, and risk when choosing a path.",
        "stem": "Assess the person's {facet} when they must make, own, or reverse a decision.",
        "facets": [
            "decisiveness",
            "caution",
            "evidence threshold",
            "reversibility bias",
            "speed versus accuracy",
            "independence",
            "consultation style",
            "risk appetite",
            "commitment strength",
            "exception handling",
        ],
    },
    {
        "code": "communication",
        "label": "Communication",
        "description": "How the person gets the right message to the right audience with the right shape.",
        "stem": "Assess the person's {facet} when they need to communicate with clarity and intent.",
        "facets": [
            "written clarity",
            "spoken clarity",
            "brevity",
            "audience calibration",
            "storytelling",
            "explanation depth",
            "summarization",
            "questioning",
            "meeting presence",
            "handoff precision",
        ],
    },
    {
        "code": "listening_and_empathy",
        "label": "Listening and Empathy",
        "description": "How the person reads others, absorbs what is said, and behaves when emotions are present.",
        "stem": "Assess the person's {facet} when they need to hear, understand, and respond to other people well.",
        "facets": [
            "active listening",
            "emotional reading",
            "patience",
            "empathy",
            "conflict de-escalation",
            "supportiveness",
            "curiosity about others",
            "feedback reception",
            "respect under stress",
            "tone control",
        ],
    },
    {
        "code": "collaboration",
        "label": "Collaboration",
        "description": "How the person shares work, coordinates with others, and behaves inside a team.",
        "stem": "Assess the person's {facet} when they must work through other people instead of alone.",
        "facets": [
            "trust building",
            "shared ownership",
            "dependency management",
            "cross-functional work",
            "coordination rhythm",
            "knowledge sharing",
            "compromise skill",
            "boundary respect",
            "reliability to team",
            "peer support",
        ],
    },
    {
        "code": "leadership",
        "label": "Leadership",
        "description": "How the person sets direction, raises standards, and carries responsibility for others.",
        "stem": "Assess the person's {facet} when they are responsible for people, direction, or standards.",
        "facets": [
            "direction setting",
            "expectation setting",
            "delegation",
            "coaching",
            "performance management",
            "talent spotting",
            "morale protection",
            "accountability enforcement",
            "role modeling",
            "succession mindset",
        ],
    },
    {
        "code": "influence_and_negotiation",
        "label": "Influence and Negotiation",
        "description": "How the person wins alignment, handles objections, and closes with other stakeholders.",
        "stem": "Assess the person's {facet} when they need to influence or negotiate with other stakeholders.",
        "facets": [
            "persuasion",
            "stakeholder mapping",
            "objection handling",
            "alignment building",
            "negotiation planning",
            "compromise without drift",
            "executive presence",
            "authority without title",
            "diplomacy",
            "closing skill",
        ],
    },
    {
        "code": "planning_and_organization",
        "label": "Planning and Organization",
        "description": "How the person breaks work down, sequences it, and stays organized over time.",
        "stem": "Assess the person's {facet} when they are planning and organizing meaningful work.",
        "facets": [
            "goal decomposition",
            "prioritization",
            "sequencing",
            "time management",
            "calendar discipline",
            "estimation",
            "dependency mapping",
            "milestone design",
            "throughput tracking",
            "cleanup habits",
        ],
    },
    {
        "code": "execution_and_follow_through",
        "label": "Execution and Follow Through",
        "description": "How the person starts, sustains, finishes, and makes progress visible.",
        "stem": "Assess the person's {facet} when they need to execute reliably and finish what they own.",
        "facets": [
            "start energy",
            "consistency",
            "ownership",
            "deadline reliability",
            "task closure",
            "escalation timeliness",
            "work visibility",
            "initiative",
            "persistence",
            "operational rhythm",
        ],
    },
    {
        "code": "quality_and_precision",
        "label": "Quality and Precision",
        "description": "How the person detects mistakes, verifies output, and respects standards.",
        "stem": "Assess the person's {facet} when quality, precision, and repeatability matter.",
        "facets": [
            "standards discipline",
            "error detection",
            "verification",
            "documentation accuracy",
            "repeatability",
            "checklist use",
            "test mindset",
            "audit readiness",
            "cleanliness",
            "finish quality",
        ],
    },
    {
        "code": "learning_and_adaptability",
        "label": "Learning and Adaptability",
        "description": "How the person absorbs new information, changes behavior, and keeps improving.",
        "stem": "Assess the person's {facet} when they must learn, adapt, or improve under changing conditions.",
        "facets": [
            "self teaching",
            "coachability",
            "feedback integration",
            "change adoption",
            "learning speed",
            "unlearning old habits",
            "experimentation openness",
            "domain transfer",
            "curiosity depth",
            "improvement loop",
        ],
    },
    {
        "code": "stress_and_resilience",
        "label": "Stress and Resilience",
        "description": "How the person behaves when workload, ambiguity, and emotional pressure rise.",
        "stem": "Assess the person's {facet} under pressure, fatigue, uncertainty, or setbacks.",
        "facets": [
            "calm under pressure",
            "recovery speed",
            "emotional regulation",
            "workload endurance",
            "composure",
            "failure response",
            "uncertainty stability",
            "stamina",
            "discipline under fatigue",
            "optimism realism",
        ],
    },
    {
        "code": "customer_and_service",
        "label": "Customer and Service",
        "description": "How the person treats customers, users, guests, or internal service recipients.",
        "stem": "Assess the person's {facet} when they are serving a customer, user, guest, or teammate in need.",
        "facets": [
            "customer empathy",
            "service recovery",
            "patience with repetition",
            "expectation setting",
            "friendliness",
            "responsiveness",
            "solution orientation",
            "trust preservation",
            "voice of customer",
            "service consistency",
        ],
    },
    {
        "code": "technical_and_tooling",
        "label": "Technical and Tooling",
        "description": "How the person uses tools, systems, data, and technical workflows to get work done.",
        "stem": "Assess the person's {facet} in the way they use tools, systems, and technical workflows.",
        "facets": [
            "tool fluency",
            "process automation",
            "troubleshooting tools",
            "data literacy",
            "systems navigation",
            "digital hygiene",
            "technical learning",
            "documentation of tools",
            "workflow efficiency",
            "security habits",
        ],
    },
    {
        "code": "business_and_financial",
        "label": "Business and Financial",
        "description": "How the person sees value, cost, tradeoffs, and the economic side of decisions.",
        "stem": "Assess the person's {facet} when business impact, cost, or commercial judgment matters.",
        "facets": [
            "commercial awareness",
            "budget sense",
            "cost tradeoffs",
            "value recognition",
            "business model understanding",
            "metric literacy",
            "profit sensitivity",
            "prioritization by impact",
            "resource stewardship",
            "vendor judgment",
        ],
    },
    {
        "code": "risk_and_safety",
        "label": "Risk and Safety",
        "description": "How the person notices hazards, follows safe practice, and escalates risk responsibly.",
        "stem": "Assess the person's {facet} when risk, safety, or harm prevention is relevant.",
        "facets": [
            "hazard awareness",
            "policy following",
            "incident response",
            "physical safety",
            "data safety",
            "escalation on risk",
            "controlled execution",
            "preventive thinking",
            "duty of care",
            "compliance under pressure",
        ],
    },
    {
        "code": "governance_and_compliance",
        "label": "Governance and Compliance",
        "description": "How the person behaves in regulated, approval-heavy, or audit-sensitive environments.",
        "stem": "Assess the person's {facet} when policy, approvals, evidence, or compliance matter.",
        "facets": [
            "policy interpretation",
            "documentation for audit",
            "evidence preservation",
            "approval discipline",
            "change control",
            "role boundary respect",
            "segregation of duties",
            "privacy awareness",
            "regulatory judgment",
            "exception documentation",
        ],
    },
    {
        "code": "creativity_and_innovation",
        "label": "Creativity and Innovation",
        "description": "How the person generates fresh options without floating away from constraints.",
        "stem": "Assess the person's {facet} when novelty, invention, or reframing would improve the work.",
        "facets": [
            "idea generation",
            "reframing",
            "aesthetic sense",
            "prototyping",
            "originality",
            "constraint creativity",
            "experimentation",
            "narrative creation",
            "future imagination",
            "improvement initiation",
        ],
    },
    {
        "code": "operational_environment",
        "label": "Operational Environment",
        "description": "How the person behaves in physical, shift-based, repetitive, or environment-sensitive work contexts.",
        "stem": "Assess the person's {facet} in the physical or operational environment where the work actually happens.",
        "facets": [
            "workspace care",
            "physical routine",
            "equipment respect",
            "shift reliability",
            "environmental awareness",
            "cleanliness discipline",
            "situational awareness",
            "route efficiency",
            "resource preparation",
            "handoff of space",
        ],
    },
    {
        "code": "documentation_and_knowledge",
        "label": "Documentation and Knowledge",
        "description": "How the person captures what matters so work survives beyond memory and personality.",
        "stem": "Assess the person's {facet} when they must capture, preserve, or retrieve knowledge.",
        "facets": [
            "note taking",
            "knowledge structuring",
            "retrieval habits",
            "template use",
            "version awareness",
            "institutional memory",
            "decision logging",
            "process capture",
            "teaching artifacts",
            "archival discipline",
        ],
    },
    {
        "code": "conflict_and_feedback",
        "label": "Conflict and Feedback",
        "description": "How the person handles disagreement, accountability, repair, and hard conversations.",
        "stem": "Assess the person's {facet} when conflict, correction, or feedback enters the room.",
        "facets": [
            "directness",
            "tact",
            "disagreement quality",
            "upward feedback",
            "peer feedback",
            "receiving correction",
            "accountability conversations",
            "boundary enforcement",
            "repair after conflict",
            "issue escalation",
        ],
    },
    {
        "code": "growth_and_career",
        "label": "Growth and Career",
        "description": "How the person sees growth, fit, reputation, and long-horizon development.",
        "stem": "Assess the person's {facet} in the way they manage growth, fit, and long-term development.",
        "facets": [
            "aspiration clarity",
            "role fit awareness",
            "promotability",
            "specialization depth",
            "breadth balance",
            "mentoring interest",
            "leadership readiness",
            "self management",
            "reputation building",
            "long term commitment",
        ],
    },
]


ROLE_RULES = [
    {
        "role_family": "bootstrap_skill_builder",
        "minimum_profile_average": 3.6,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 55,
        "maximum_low_score_count": 40,
        "minimum_critical_domain_average": 4.0,
        "critical_domains": "values_and_ethics;cognitive_style;problem_solving;communication;documentation_and_knowledge;governance_and_compliance",
        "notes": "Use for worker-factory roles such as Talent Director, Persona Analyst, Summary Writer, Skill Architect, and Governance Officer.",
    },
    {
        "role_family": "executive",
        "minimum_profile_average": 3.7,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 60,
        "maximum_low_score_count": 35,
        "minimum_critical_domain_average": 4.0,
        "critical_domains": "leadership;business_and_financial;decision_posture;communication;stress_and_resilience",
        "notes": "High bar for leadership, business judgment, and pressure stability.",
    },
    {
        "role_family": "people_manager",
        "minimum_profile_average": 3.5,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 50,
        "maximum_low_score_count": 45,
        "minimum_critical_domain_average": 3.9,
        "critical_domains": "leadership;collaboration;listening_and_empathy;conflict_and_feedback;planning_and_organization",
        "notes": "Managers must show both human and execution competence.",
    },
    {
        "role_family": "business_owner",
        "minimum_profile_average": 3.5,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 48,
        "maximum_low_score_count": 45,
        "minimum_critical_domain_average": 3.9,
        "critical_domains": "business_and_financial;decision_posture;communication;planning_and_organization;customer_and_service",
        "notes": "Owns business outcomes and tradeoff quality more than deep technical execution.",
    },
    {
        "role_family": "technical_specialist",
        "minimum_profile_average": 3.4,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 45,
        "maximum_low_score_count": 50,
        "minimum_critical_domain_average": 3.9,
        "critical_domains": "cognitive_style;problem_solving;technical_and_tooling;quality_and_precision;documentation_and_knowledge",
        "notes": "May be uneven socially, but cannot be flat in cognition, quality, or tooling.",
    },
    {
        "role_family": "analyst_operator",
        "minimum_profile_average": 3.3,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 42,
        "maximum_low_score_count": 55,
        "minimum_critical_domain_average": 3.8,
        "critical_domains": "cognitive_style;problem_solving;documentation_and_knowledge;execution_and_follow_through;quality_and_precision",
        "notes": "Strong fit for analysts, coordinators, and operator-heavy knowledge work.",
    },
    {
        "role_family": "frontline_service",
        "minimum_profile_average": 3.2,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 40,
        "maximum_low_score_count": 55,
        "minimum_critical_domain_average": 3.8,
        "critical_domains": "customer_and_service;communication;listening_and_empathy;stress_and_resilience;execution_and_follow_through",
        "notes": "For call-center, help-desk, reception, guest service, and similar frontline roles.",
    },
    {
        "role_family": "operations_support",
        "minimum_profile_average": 3.1,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 38,
        "maximum_low_score_count": 60,
        "minimum_critical_domain_average": 3.7,
        "critical_domains": "operational_environment;risk_and_safety;execution_and_follow_through;quality_and_precision;planning_and_organization",
        "notes": "For facilities, custodial, field operations, and environment-sensitive support roles.",
    },
    {
        "role_family": "governance_risk",
        "minimum_profile_average": 3.5,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 48,
        "maximum_low_score_count": 40,
        "minimum_critical_domain_average": 4.1,
        "critical_domains": "values_and_ethics;risk_and_safety;governance_and_compliance;quality_and_precision;documentation_and_knowledge",
        "notes": "For audit, controls, policy, privacy, and regulatory roles.",
    },
    {
        "role_family": "creative_builder",
        "minimum_profile_average": 3.3,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 42,
        "maximum_low_score_count": 55,
        "minimum_critical_domain_average": 3.8,
        "critical_domains": "creativity_and_innovation;communication;problem_solving;learning_and_adaptability;execution_and_follow_through",
        "notes": "For design, content, brand, and novel solution-building roles.",
    },
    {
        "role_family": "customer_persona",
        "minimum_profile_average": 2.8,
        "minimum_distinct_scores": 4,
        "minimum_high_score_count": 30,
        "maximum_low_score_count": 80,
        "minimum_critical_domain_average": 3.3,
        "critical_domains": "identity_and_motivation;customer_and_service;business_and_financial;communication;stress_and_resilience",
        "notes": "Use for external customer personas, representative users, and consumer archetypes rather than internal employees.",
    },
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def build_checklist_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for domain_index, domain in enumerate(DOMAIN_DEFINITIONS, start=1):
        for facet_index, facet in enumerate(domain["facets"], start=1):
            category_id = f"{domain_index:02d}.{facet_index:02d}"
            rows.append(
                {
                    "category_id": category_id,
                    "domain_code": domain["code"],
                    "domain_label": domain["label"],
                    "facet": facet,
                    "prompt": domain["stem"].format(facet=facet),
                    "score_1_anchor": f"Rarely demonstrates {facet}, even in low-pressure or familiar contexts.",
                    "score_3_anchor": f"Shows {facet} inconsistently or mainly in familiar conditions.",
                    "score_5_anchor": f"Demonstrates {facet} reliably, even under pressure, novelty, or complexity.",
                }
            )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_checklist_markdown(rows: list[dict[str, str]]) -> str:
    parts = [
        "# Person Definition Checklist",
        "",
        "This is an original, broad-spectrum 250-dimension framework for defining a person-shaped worker profile. It is designed to be wide enough for executive, frontline, operations, technical, governance, and customer persona use cases without copying any company-private implementation.",
        "",
        "## Global Scoring Rules",
        "",
        "1. Use a 1-5 scale for every category. Reserve missing evidence for explicit follow-up, not silent defaults.",
        "2. A profile is not valid if it uses fewer than 4 distinct score values across the checklist.",
        "3. A profile should not leave more than 40 percent of categories at the midpoint unless the assessor documents why the role truly lacks signal.",
        "4. Non-negotiable domains for the target role family must meet the role threshold before the person can qualify.",
        "5. The point of the checklist is not to make every score high. The point is to reveal shape, tension, and hiring fit.",
        "",
        "## Domain Map",
        "",
    ]
    for domain in DOMAIN_DEFINITIONS:
        parts.extend([f"### {domain['label']}", "", domain["description"], ""])
        domain_rows = [row for row in rows if row["domain_code"] == domain["code"]]
        for row in domain_rows:
            parts.append(f"- `{row['category_id']}` {row['facet']}: {row['prompt']}")
        parts.append("")
    return "\n".join(parts)


def build_role_rules_markdown() -> str:
    lines = [
        "# Role Qualification Rules",
        "",
        "These rules sit on top of the 250-dimension checklist. They do not replace human judgment; they stop obviously weak fits from being polished into a worker anyway.",
        "",
        "## Shared Qualification Gates",
        "",
        "1. Minimum distinct score values: 4.",
        "2. Midpoint overuse threshold: no more than 40 percent of the checklist at score 3 without written justification.",
        "3. Every role family defines critical domains that must clear a higher average than the overall profile.",
        "4. A strong profile should contain both real strengths and visible low-confidence areas. Flatness is a failure condition, not a nice outcome.",
        "",
        "## Role Families",
        "",
        "| Role Family | Min Avg | Min Distinct Scores | Min High Scores | Max Low Scores | Min Critical Domain Avg | Critical Domains |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for rule in ROLE_RULES:
        lines.append(
            f"| `{rule['role_family']}` | {rule['minimum_profile_average']} | {rule['minimum_distinct_scores']} | {rule['minimum_high_score_count']} | {rule['maximum_low_score_count']} | {rule['minimum_critical_domain_average']} | {rule['critical_domains']} |"
        )
    lines.extend(["", "## Notes", ""])
    for rule in ROLE_RULES:
        lines.append(f"- `{rule['role_family']}`: {rule['notes']}")
    return "\n".join(lines)


def build_identity_root_readme() -> str:
    return dedent(
        """
        # Identity Bootstrap Library

        This folder contains the first bootstrap workers needed to build future workers in a person-first system.

        ## Bootstrap Sequence

        1. `TalentDirector` decides whether a request deserves a new worker, an upgrade, a merge, or a rejection.
        2. `PersonaAnalyst` scores the proposed person against the 250-dimension framework and role thresholds.
        3. `SummaryWriter` turns the qualified profile into the human-facing source of truth.
        4. `SkillArchitect` hardens that source into metadata, gates, handoffs, and runtime boundaries.
        5. `GovernanceOfficer` decides whether the worker is publishable, experimental, mergeable, or blocked.

        ## Templates

        - `_templates/person-definition-checklist.csv`
        - `_templates/person-definition-checklist.md`
        - `_templates/role-qualification-rules.csv`
        - `_templates/role-qualification-rules.md`

        These templates are broad by design and are intended to be adapted. They are not meant to reproduce any company-private scoring system verbatim.
        """
    )


def worker_readme(worker: dict[str, object]) -> str:
    return dedent(
        f"""
        # {worker['display_name']}

        **Role:** {worker['role']}

        **Promise:** {worker['tagline']}

        ## Purpose

        {worker['purpose']}

        ## When To Call {worker['display_name'].split()[0]}

        - When the current worker library does not clearly cover a reusable request.
        - When a new worker needs this role's specific judgment before the next downstream step.

        ## Signature Outputs

        - A bounded artifact that downstream bootstrap workers can use without guessing.
        - A clear yes, no, hold, or handoff decision inside this worker's boundary.

        ## Identity Notes

        - Default posture: narrow the job before broadening the story.
        - Human-facing role: the end user should see {worker['display_name'].split()[0]}, not a generated internal id.
        """
    )


def worker_job_posting(worker: dict[str, object]) -> str:
    bullets = "\n".join(f"- {item}" for item in worker["capabilities"])
    return dedent(
        f"""
        {worker['display_name']} is the {worker['role']} for the bootstrap factory.

        Mission:
        {worker['purpose']}

        Core outputs:
        {bullets}

        Success bar:
        The next bootstrap worker should receive a tighter, clearer artifact than the one this worker started with.
        """
    )


def bullet_section(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def create_worker_files(worker: dict[str, object]) -> None:
    root = IDENTITY_ROOT / worker["folder"]
    metadata_root = root / "metadata"
    persona_root = root / "persona"
    ensure_dir(metadata_root)
    ensure_dir(persona_root)

    write_text(root / "README.md", worker_readme(worker))
    write_text(root / "jobPosting.md", worker_job_posting(worker))
    write_text(metadata_root / "authority.md", f"# Authority\n\n{bullet_section(worker['authority'])}")
    write_text(metadata_root / "capabilities.md", f"# Capabilities\n\n{bullet_section(worker['capabilities'])}")
    write_text(metadata_root / "reasoning.md", f"# Reasoning\n\n{bullet_section(worker['reasoning'])}")
    write_text(metadata_root / "workflows.md", "# Workflows\n\n" + "\n".join(f"{idx}. {item}" for idx, item in enumerate(worker["workflow"], start=1)))
    write_text(metadata_root / "handoffs.md", f"# Handoffs\n\n{bullet_section(worker['handoffs'])}")
    write_text(persona_root / "beliefs.md", f"# Beliefs\n\n{bullet_section(worker['beliefs'])}")
    write_text(persona_root / "expertise.md", f"# Expertise\n\n{bullet_section(worker['expertise'])}")
    write_text(persona_root / "origin.md", f"# Origin\n\n{worker['origin']}")
    write_text(persona_root / "personality.md", f"# Personality\n\n{worker['personality']}")
    write_text(persona_root / "scars.md", f"# Scars\n\n{bullet_section(worker['scars'])}")
    write_text(
        root / "governance-review.md",
        dedent(
            f"""
            # Governance Review

            Review {worker['display_name']} against these minimums before promotion:

            - The role boundary is narrow enough to explain in one sentence.
            - Inputs and outputs are explicit enough for the next worker to consume without guessing.
            - Refusal conditions are visible in the metadata, not hidden in lore.
            - The worker adds a distinct step to the bootstrap chain instead of duplicating a neighbor.
            """
        ),
    )
    write_text(
        root / "lore-briefing.md",
        dedent(
            f"""
            # Lore Briefing

            {worker['display_name']} is remembered for one thing first: {worker['tagline']}

            This worker should feel like a specific coworker with real instincts, not a label wrapped around a feature set.
            """
        ),
    )
    write_text(
        root / "naming-assessment.md",
        dedent(
            f"""
            # Naming Assessment

            - Display name: {worker['display_name']}
            - Internal folder: {worker['folder']}
            - Why it works: the name is short, memorable, and human enough to appear in UI surfaces without feeling synthetic.
            """
        ),
    )


def main() -> None:
    ensure_dir(TEMPLATES_ROOT)
    write_text(IDENTITY_ROOT / "README.md", build_identity_root_readme())

    checklist_rows = build_checklist_rows()
    write_csv(
        TEMPLATES_ROOT / "person-definition-checklist.csv",
        [
            "category_id",
            "domain_code",
            "domain_label",
            "facet",
            "prompt",
            "score_1_anchor",
            "score_3_anchor",
            "score_5_anchor",
        ],
        checklist_rows,
    )
    write_text(TEMPLATES_ROOT / "person-definition-checklist.md", build_checklist_markdown(checklist_rows))
    write_csv(
        TEMPLATES_ROOT / "role-qualification-rules.csv",
        [
            "role_family",
            "minimum_profile_average",
            "minimum_distinct_scores",
            "minimum_high_score_count",
            "maximum_low_score_count",
            "minimum_critical_domain_average",
            "critical_domains",
            "notes",
        ],
        ROLE_RULES,
    )
    write_text(TEMPLATES_ROOT / "role-qualification-rules.md", build_role_rules_markdown())

    for worker in WORKERS:
        create_worker_files(worker)

    print(f"Created {len(WORKERS)} bootstrap workers and {len(checklist_rows)} checklist categories in {IDENTITY_ROOT}")


if __name__ == "__main__":
    main()
