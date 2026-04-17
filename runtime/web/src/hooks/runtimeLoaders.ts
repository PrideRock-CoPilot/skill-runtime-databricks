import type { Dispatch, SetStateAction } from "react";

import { getDashboard, getSessionHistory, listMemories, listTemplateDocuments, listTemplates } from "../api";
import type {
  DashboardResponse,
  GeneratedDocumentRecord,
  MemoryRecord,
  MemoryScope,
  SessionHistoryResponse,
  TemplateRecord
} from "../types";

interface RefreshDashboardParams {
  sessionId: string;
  userId: string;
  setDashboard: Dispatch<SetStateAction<DashboardResponse | null>>;
  setLastRefreshedAt: Dispatch<SetStateAction<string>>;
  setIsDashboardLoading: Dispatch<SetStateAction<boolean>>;
}

export async function refreshDashboardData({
  sessionId,
  userId,
  setDashboard,
  setLastRefreshedAt,
  setIsDashboardLoading
}: RefreshDashboardParams) {
  setIsDashboardLoading(true);
  try {
    const nextDashboard = await getDashboard(sessionId, userId);
    setDashboard(nextDashboard);
    setLastRefreshedAt(new Date().toISOString());
  } finally {
    setIsDashboardLoading(false);
  }
}

interface RefreshTemplateLibraryParams {
  projectId: string;
  userId: string;
  setTemplateLibrary: Dispatch<SetStateAction<TemplateRecord[]>>;
  setGeneratedDocuments: Dispatch<SetStateAction<GeneratedDocumentRecord[]>>;
  setIsTemplateLibraryLoading: Dispatch<SetStateAction<boolean>>;
}

export async function refreshTemplateLibraryData({
  projectId,
  userId,
  setTemplateLibrary,
  setGeneratedDocuments,
  setIsTemplateLibraryLoading
}: RefreshTemplateLibraryParams) {
  if (!projectId) {
    setTemplateLibrary([]);
    setGeneratedDocuments([]);
    return;
  }

  setIsTemplateLibraryLoading(true);
  try {
    const [templates, documents] = await Promise.all([listTemplates(projectId, userId), listTemplateDocuments(projectId, userId)]);
    setTemplateLibrary(templates);
    setGeneratedDocuments(documents);
  } catch (error) {
    if (error instanceof Error && error.message.includes("Not Found")) {
      setTemplateLibrary([]);
      setGeneratedDocuments([]);
      return;
    }
    throw error;
  } finally {
    setIsTemplateLibraryLoading(false);
  }
}

interface RefreshKnowledgeBaseParams {
  userId: string;
  projectId: string;
  query: string;
  scope: MemoryScope | "all";
  category: string;
  setKnowledgeEntries: Dispatch<SetStateAction<MemoryRecord[]>>;
  setIsKnowledgeLoading: Dispatch<SetStateAction<boolean>>;
}

export async function refreshKnowledgeBaseData({
  userId,
  projectId,
  query,
  scope,
  category,
  setKnowledgeEntries,
  setIsKnowledgeLoading
}: RefreshKnowledgeBaseParams) {
  setIsKnowledgeLoading(true);
  try {
    const entries = await listMemories({
      userId,
      projectId,
      query,
      scope,
      category,
      limit: 24
    });
    setKnowledgeEntries(entries);
  } finally {
    setIsKnowledgeLoading(false);
  }
}

interface LoadSessionHistoryParams {
  sessionId: string;
  userId: string;
  setSessionHistory: Dispatch<SetStateAction<SessionHistoryResponse | null>>;
  setIsSessionHistoryLoading: Dispatch<SetStateAction<boolean>>;
}

export async function loadSessionHistoryData({
  sessionId,
  userId,
  setSessionHistory,
  setIsSessionHistoryLoading
}: LoadSessionHistoryParams) {
  setIsSessionHistoryLoading(true);
  try {
    const history = await getSessionHistory(sessionId, userId);
    setSessionHistory(history);
  } finally {
    setIsSessionHistoryLoading(false);
  }
}