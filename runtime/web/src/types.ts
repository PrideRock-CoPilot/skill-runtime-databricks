export type Complexity = "simple" | "standard" | "deep" | "expert";
export type WorkItemStage = "backlog" | "discovery" | "design" | "build" | "review" | "done";
export type ClientType = "genie-code" | "ide" | "web" | "api";
export type ProjectVisibility = "private" | "shared";
export type AppTab = "board" | "skills" | "sessions" | "preferences";

export interface UserPreferences {
  operatorName: string;
  userId: string;
  clientType: ClientType;
  workspaceMode: "focus" | "loud";
  showRetroSkills: boolean;
  autoParkAfterFeedback: boolean;
  compactBoard: boolean;
  favoriteSkillIds: string[];
  downvotedSkillIds: string[];
}

export interface SkillSummary {
  skill_id: string;
  slug: string;
  name: string;
  display_name: string;
  description: string;
  packet_level: string;
  source_dir: string;
  search_score: number;
}

export interface SkillBundle {
  bundle_id: string;
  skill_id: string;
  gate_level: number;
  gate_name: string;
  title: string;
  content: string;
  source_file: string;
  sort_order: number;
}

export interface SkillDetailResponse {
  skill: SkillSummary;
  requested_gate: number;
  loaded_gates: number[];
  bundles: SkillBundle[];
}

export interface RouteMatch {
  skill_id: string;
  display_name: string;
  description: string;
  search_score: number;
}

export interface RouteResponse {
  prompt: string;
  complexity: Complexity;
  recommended_gate: number;
  matches: RouteMatch[];
}

export interface ProjectRecord {
  project_id: string;
  user_id: string;
  name: string;
  summary: string;
  owner_name: string;
  stage: string;
  visibility: ProjectVisibility;
  updated_at: string;
}

export interface WorkItemRecord {
  work_item_id: string;
  project_id: string;
  user_id: string;
  title: string;
  summary: string;
  stage: WorkItemStage;
  owner_skill_id: string;
  owner_display_name: string;
  priority: string;
  updated_at: string;
}

export interface ParkedSkillRecord {
  parking_id: string;
  session_id: string;
  user_id: string;
  project_id: string;
  client_type: ClientType;
  skill_id: string;
  display_name: string;
  gate_level: number;
  status: string;
  note: string;
  parked_at: string;
  resumed_at: string;
}

export interface ActiveSkillRecord {
  activation_id: string;
  session_id: string;
  user_id: string;
  project_id: string;
  client_type: ClientType;
  skill_id: string;
  display_name: string;
  gate_level: number;
  status: string;
  route_prompt: string;
  activation_reason: string;
  activated_at: string;
  deactivated_at: string;
}

export interface SkillEventRecord {
  event_id: string;
  activation_id: string;
  session_id: string;
  user_id: string;
  project_id: string;
  skill_id: string;
  event_type: string;
  status: string;
  summary: string;
  payload_json: string;
  created_at: string;
}

export interface AlignmentRecord {
  alignment_id: string;
  activation_id: string;
  session_id: string;
  user_id: string;
  project_id: string;
  skill_id: string;
  display_name: string;
  gate_level: number;
  score: number;
  status: string;
  summary: string;
  checks_json: string;
  created_at: string;
}

export interface SessionStoryStep {
  title: string;
  detail: string;
  time: string;
}

export interface SessionStory {
  headline: string;
  current_step: string;
  next_step: string;
  active_worker: string;
  hiring_in_progress: boolean;
  timeline: SessionStoryStep[];
}

export interface SessionRecord {
  session_id: string;
  user_id: string;
  project_id: string;
  project_name: string;
  client_type: ClientType;
  status: string;
  top_skill_id: string;
  active_skill_id: string;
  last_used_at: string;
  last_route_prompt: string;
  route_count: number;
  event_count: number;
  history_scope: "project" | "workspace";
  retention_days: number | null;
}

export interface SessionHistoryEntry {
  entry_id: string;
  entry_type: string;
  title: string;
  detail: string;
  created_at: string;
  skill_id: string;
}

export interface SessionHistoryResponse {
  session: SessionRecord;
  timeline: SessionHistoryEntry[];
}

export interface DashboardResponse {
  user_id: string;
  projects: ProjectRecord[];
  user_sessions: SessionRecord[];
  work_items: WorkItemRecord[];
  parking_lot: ParkedSkillRecord[];
  active_skill: ActiveSkillRecord | null;
  recent_events: SkillEventRecord[];
  latest_alignment: AlignmentRecord | null;
  session_story: SessionStory | null;
}

export interface TemplateRecord {
  template_id: string;
  project_id: string;
  user_id: string;
  name: string;
  category: string;
  description: string;
  original_file_name: string;
  stored_relative_path: string;
  file_extension: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
  archived: boolean;
}

export interface GeneratedDocumentRecord {
  document_id: string;
  template_id: string;
  project_id: string;
  user_id: string;
  name: string;
  description: string;
  file_name: string;
  stored_relative_path: string;
  file_extension: string;
  mime_type: string;
  size_bytes: number;
  source_template_name: string;
  created_at: string;
  updated_at: string;
  archived: boolean;
}
