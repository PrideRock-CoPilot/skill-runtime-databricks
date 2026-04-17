import type {
  AuthContext,
  ClientType,
  Complexity,
  DashboardResponse,
  GeneratedDocumentRecord,
  MemoryRecord,
  MemoryScope,
  RouteResponse,
  SessionHistoryResponse,
  SkillDetailResponse,
  SkillSummary,
  TemplateRecord
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers ?? {});
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export interface CreateProjectPayload {
  user_id: string;
  name: string;
  summary?: string;
  owner_name?: string;
  visibility?: "private" | "shared";
  stage?: string;
}

export interface CreateWorkItemPayload {
  project_id: string;
  user_id: string;
  title: string;
  summary: string;
  stage: string;
  owner_skill_id: string;
  owner_display_name: string;
  priority: string;
}

export interface UpdateWorkItemPayload {
  title?: string;
  summary?: string;
  stage?: string;
  owner_skill_id?: string;
  owner_display_name?: string;
  priority?: string;
}

export interface FeedbackPayload {
  session_id: string;
  user_id: string;
  project_id?: string;
  client_type: ClientType;
  skill_id: string;
  rating: "correct" | "wrong";
  prompt: string;
  response_excerpt?: string;
  note?: string;
  work_item_id?: string;
}

export interface ActivateSkillPayload {
  session_id: string;
  user_id: string;
  project_id?: string;
  client_type: ClientType;
  gate_level: number;
  prompt?: string;
  activation_reason?: string;
}

export interface AlignmentPayload {
  session_id: string;
  user_id: string;
  project_id?: string;
  skill_id?: string;
  prompt: string;
  response_excerpt: string;
  gate_level?: number;
  note?: string;
}

export interface UploadTemplatePayload {
  userId: string;
  name: string;
  category: string;
  description: string;
  file: File;
}

export interface CreateTemplateDocumentPayload {
  user_id: string;
  name: string;
  description?: string;
}

export interface CreateMemoryPayload {
  scope: MemoryScope;
  subject: string;
  content: string;
  category?: string;
  project_id?: string;
  skill_id?: string;
  tags?: string;
  status?: string;
  importance?: number;
  confidence?: number;
  source?: string;
  owner?: string;
  decision_scope?: string;
  pinned?: boolean;
  supersedes_memory_id?: string;
  expires_at?: string;
}

export interface UpdateMemoryPayload {
  subject?: string;
  content?: string;
  category?: string;
  tags?: string;
  status?: string;
  importance?: number;
  confidence?: number;
  source?: string;
  owner?: string;
  decision_scope?: string;
  pinned?: boolean;
  supersedes_memory_id?: string;
  expires_at?: string;
}

export interface ListMemoriesParams {
  userId: string;
  projectId?: string;
  query?: string;
  scope?: MemoryScope | "all";
  category?: string;
  limit?: number;
}

export function getDashboard(sessionId: string, userId: string): Promise<DashboardResponse> {
  const query = new URLSearchParams({
    session_id: sessionId,
    user_id: userId
  });
  return request<DashboardResponse>(`/api/dashboard?${query.toString()}`);
}

export function getDashboardStreamUrl(sessionId: string, userId: string): string {
  const query = new URLSearchParams({
    session_id: sessionId,
    user_id: userId
  });
  return `${API_BASE_URL}/api/dashboard/stream?${query.toString()}`;
}

export function getAuthContext(): Promise<AuthContext> {
  return request<AuthContext>("/api/auth/context");
}

export function getSessionHistory(sessionId: string, userId: string, limit = 60): Promise<SessionHistoryResponse> {
  const query = new URLSearchParams({
    user_id: userId,
    limit: String(limit)
  });
  return request<SessionHistoryResponse>(`/api/sessions/${sessionId}/history?${query.toString()}`);
}

export function listMemories(params: ListMemoriesParams): Promise<MemoryRecord[]> {
  const query = new URLSearchParams({
    user_id: params.userId,
    limit: String(params.limit ?? 24)
  });
  if (params.projectId) {
    query.set("project_id", params.projectId);
  }
  if (params.query) {
    query.set("query", params.query);
  }
  if (params.scope && params.scope !== "all") {
    query.set("scope", params.scope);
  }
  if (params.category && params.category !== "all") {
    query.set("category", params.category);
  }
  return request<MemoryRecord[]>(`/api/memories?${query.toString()}`);
}

export function createMemory(userId: string, sessionId: string, payload: CreateMemoryPayload): Promise<unknown> {
  const query = new URLSearchParams({ user_id: userId, session_id: sessionId });
  return request(`/api/memories?${query.toString()}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateMemory(memoryId: string, userId: string, payload: UpdateMemoryPayload): Promise<unknown> {
  const query = new URLSearchParams({ user_id: userId });
  return request(`/api/memories/${memoryId}?${query.toString()}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function archiveMemory(memoryId: string, userId: string): Promise<unknown> {
  const query = new URLSearchParams({ user_id: userId });
  return request(`/api/memories/${memoryId}?${query.toString()}`, {
    method: "DELETE"
  });
}

export function getSkills(query = ""): Promise<SkillSummary[]> {
  return request<SkillSummary[]>(`/api/skills?query=${encodeURIComponent(query)}`);
}

export function getSkill(skillId: string, gate: number): Promise<SkillDetailResponse> {
  return request<SkillDetailResponse>(`/api/skills/${skillId}?gate=${gate}`);
}

export function routePrompt(
  prompt: string,
  complexity: Complexity | undefined,
  sessionId: string,
  userId: string,
  projectId: string,
  clientType: ClientType
): Promise<RouteResponse> {
  return request<RouteResponse>("/api/router/route", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      complexity,
      session_id: sessionId,
      user_id: userId,
      project_id: projectId,
      client_type: clientType
    })
  });
}

export function compileRuntime(): Promise<{ skills: number; bundles: number }> {
  return request<{ skills: number; bundles: number }>("/api/runtime/compile", {
    method: "POST"
  });
}

export function parkSkill(
  skillId: string,
  sessionId: string,
  userId: string,
  projectId: string,
  clientType: ClientType,
  gateLevel: number,
  note: string
): Promise<unknown> {
  return request(`/api/skills/${skillId}/park`, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId,
      project_id: projectId,
      client_type: clientType,
      gate_level: gateLevel,
      note
    })
  });
}

export function resumeSkill(skillId: string, sessionId: string, userId: string): Promise<unknown> {
  return request(`/api/skills/${skillId}/resume`, {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId
    })
  });
}

export function activateSkill(skillId: string, payload: ActivateSkillPayload): Promise<unknown> {
  return request(`/api/skills/${skillId}/activate`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function scoreAlignment(payload: AlignmentPayload): Promise<unknown> {
  return request("/api/alignment/score", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createProject(payload: CreateProjectPayload): Promise<unknown> {
  return request("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createWorkItem(payload: CreateWorkItemPayload): Promise<unknown> {
  return request("/api/work-items", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateWorkItem(workItemId: string, payload: UpdateWorkItemPayload): Promise<unknown> {
  return request(`/api/work-items/${workItemId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function recordFeedback(payload: FeedbackPayload): Promise<unknown> {
  return request("/api/feedback", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listTemplates(projectId: string, userId: string): Promise<TemplateRecord[]> {
  const query = new URLSearchParams({ user_id: userId });
  return request<TemplateRecord[]>(`/api/projects/${projectId}/templates?${query.toString()}`);
}

export function uploadTemplate(projectId: string, payload: UploadTemplatePayload): Promise<TemplateRecord> {
  const formData = new FormData();
  formData.set("user_id", payload.userId);
  formData.set("name", payload.name);
  formData.set("category", payload.category);
  formData.set("description", payload.description);
  formData.set("file", payload.file);
  return request<TemplateRecord>(`/api/projects/${projectId}/templates`, {
    method: "POST",
    body: formData
  });
}

export function listTemplateDocuments(projectId: string, userId: string): Promise<GeneratedDocumentRecord[]> {
  const query = new URLSearchParams({ user_id: userId });
  return request<GeneratedDocumentRecord[]>(`/api/projects/${projectId}/template-documents?${query.toString()}`);
}

export function createTemplateDocument(
  projectId: string,
  templateId: string,
  payload: CreateTemplateDocumentPayload
): Promise<GeneratedDocumentRecord> {
  return request<GeneratedDocumentRecord>(`/api/projects/${projectId}/templates/${templateId}/generate`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getTemplateDownloadUrl(templateId: string, userId: string): string {
  const query = new URLSearchParams({ user_id: userId });
  return `${API_BASE_URL}/api/templates/${templateId}/download?${query.toString()}`;
}

export function getTemplateDocumentDownloadUrl(documentId: string, userId: string): string {
  const query = new URLSearchParams({ user_id: userId });
  return `${API_BASE_URL}/api/template-documents/${documentId}/download?${query.toString()}`;
}
