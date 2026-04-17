import type { AppTab, WorkItemStage } from "./types";

export const STAGES: WorkItemStage[] = ["backlog", "discovery", "design", "build", "review", "done"];

export const GATES = [
  { level: 0, label: "Gate 0", detail: "Router" },
  { level: 1, label: "Gate 1", detail: "Definition" },
  { level: 2, label: "Gate 2", detail: "Execution" },
  { level: 3, label: "Gate 3", detail: "Specialist" },
  { level: 4, label: "Gate 4", detail: "Full" }
] as const;

export const QUICK_PROMPTS = [
  "Route a request to audit overlap and stale routing across the skill library.",
  "Find the best skill packet to build a frontend flow with stronger empty states.",
  "Recommend the right gate for reviewing a risky app change before release."
];

export const APP_TABS: Array<{ id: AppTab; label: string; detail: string }> = [
  { id: "board", label: "Board", detail: "Run delivery" },
  { id: "skills", label: "Skills", detail: "Roster and packets" },
  { id: "knowledge", label: "Knowledge", detail: "Memory base" },
  { id: "sessions", label: "Sessions", detail: "Connected activity" },
  { id: "preferences", label: "Preferences", detail: "Operator setup" }
];