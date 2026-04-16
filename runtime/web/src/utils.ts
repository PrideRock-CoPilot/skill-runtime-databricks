import type { WorkItemRecord, WorkItemStage } from "./types";

export function getSessionId(): string {
  const key = "skill-runtime-session";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const created = `session-${crypto.randomUUID()}`;
  window.localStorage.setItem(key, created);
  return created;
}

export function stageLabel(stage: WorkItemStage): string {
  return stage.charAt(0).toUpperCase() + stage.slice(1);
}

export function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

export function getStatusTone(status: string, busy: boolean): "ready" | "working" | "error" {
  if (busy) {
    return "working";
  }
  if (/failed|error/i.test(status)) {
    return "error";
  }
  return "ready";
}

export function getWorkSummary(workItems: WorkItemRecord[]): string {
  if (workItems.length === 0) {
    return "No work items yet";
  }
  const activeCount = workItems.filter((item) => item.stage !== "done").length;
  return `${activeCount} active across ${workItems.length} total items`;
}