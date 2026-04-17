import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { getSkill, getSkills } from "../api";
import { STAGES } from "../constants";
import { createRuntimeActions } from "./runtimeActions";
import {
  loadSessionHistoryData,
  refreshDashboardData,
  refreshKnowledgeBaseData,
  refreshTemplateLibraryData
} from "./runtimeLoaders";
import type {
  ActiveSkillRecord,
  AlignmentRecord,
  ClientType,
  Complexity,
  DashboardResponse,
  GeneratedDocumentRecord,
  MemoryRecord,
  MemoryScope,
  ParkedSkillRecord,
  RouteResponse,
  SessionHistoryResponse,
  SessionRecord,
  SessionStory,
  SkillDetailResponse,
  SkillEventRecord,
  SkillSummary,
  TemplateRecord,
  WorkItemRecord,
  WorkItemStage
} from "../types";
import { getSessionId, getStatusTone } from "../utils";

export interface RuntimeAppModel {
  sessionId: string;
  userId: string;
  clientType: ClientType;
  dashboard: DashboardResponse | null;
  skills: SkillSummary[];
  deferredSkillQuery: string;
  skillQuery: string;
  selectedSkillId: string;
  selectedGate: number;
  skillDetail: SkillDetailResponse | null;
  routeText: string;
  routeComplexity: Complexity | "";
  routeResult: RouteResponse | null;
  newWorkTitle: string;
  newWorkSummary: string;
  newWorkStage: WorkItemStage;
  status: string;
  busy: boolean;
  isDashboardLoading: boolean;
  isSkillsLoading: boolean;
  isDetailLoading: boolean;
  lastRefreshedAt: string;
  activeProject: DashboardResponse["projects"][number] | null;
  activeSkill: ActiveSkillRecord | null;
  latestAlignment: AlignmentRecord | null;
  recentEvents: SkillEventRecord[];
  sessionStory: SessionStory | null;
  userSessions: SessionRecord[];
  selectedHistorySessionId: string;
  sessionHistory: SessionHistoryResponse | null;
  workItems: WorkItemRecord[];
  parkingLot: ParkedSkillRecord[];
  templateLibrary: TemplateRecord[];
  generatedDocuments: GeneratedDocumentRecord[];
  knowledgeEntries: MemoryRecord[];
  knowledgeQuery: string;
  knowledgeScope: MemoryScope | "all";
  knowledgeCategory: string;
  groupedWorkItems: Array<{ stage: WorkItemStage; items: WorkItemRecord[] }>;
  completedWorkCount: number;
  completionRate: number;
  statusTone: "ready" | "working" | "error";
  inFlightWorkCount: number;
  isTemplateLibraryLoading: boolean;
  isSessionHistoryLoading: boolean;
  isKnowledgeLoading: boolean;
  setSkillQuery: (value: string) => void;
  setSelectedSkillId: (value: string) => void;
  setSelectedGate: (value: number) => void;
  setSelectedHistorySessionId: (value: string) => void;
  setRouteText: (value: string) => void;
  setRouteComplexity: (value: Complexity | "") => void;
  setNewWorkTitle: (value: string) => void;
  setNewWorkSummary: (value: string) => void;
  setNewWorkStage: (value: WorkItemStage) => void;
  setKnowledgeQuery: (value: string) => void;
  setKnowledgeScope: (value: MemoryScope | "all") => void;
  setKnowledgeCategory: (value: string) => void;
  handleCompile: () => Promise<void>;
  handleRoute: () => Promise<void>;
  handleActivateSelectedSkill: () => Promise<void>;
  handleScoreAlignment: () => Promise<void>;
  handleParkSelectedSkill: () => Promise<void>;
  handleResume: (item: ParkedSkillRecord) => Promise<void>;
  handleFeedback: (rating: "correct" | "wrong") => Promise<void>;
  handleCreateWorkItem: () => Promise<void>;
  shiftWorkItem: (item: WorkItemRecord, direction: -1 | 1) => Promise<void>;
  refreshTemplateLibrary: () => Promise<void>;
  refreshKnowledgeBase: () => Promise<void>;
  handleCreateKnowledgeEntry: (payload: {
    scope: MemoryScope;
    subject: string;
    content: string;
    category: string;
    tags: string;
    pinned: boolean;
    projectId?: string;
  }) => Promise<void>;
  handleArchiveKnowledgeEntry: (memoryId: string) => Promise<void>;
  handleToggleKnowledgePin: (entry: MemoryRecord) => Promise<void>;
  handleUploadTemplate: (file: File, name: string, category: string, description: string) => Promise<void>;
  handleCreateDocumentFromTemplate: (templateId: string, name: string, description: string) => Promise<void>;
  getTemplateDownloadHref: (templateId: string) => string;
  getGeneratedDocumentDownloadHref: (documentId: string) => string;
}

export function useRuntimeApp(userId: string, clientType: ClientType): RuntimeAppModel {
  const [sessionId] = useState(getSessionId);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const deferredSkillQuery = useDeferredValue(skillQuery);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const deferredKnowledgeQuery = useDeferredValue(knowledgeQuery);
  const [knowledgeScope, setKnowledgeScope] = useState<MemoryScope | "all">("all");
  const [knowledgeCategory, setKnowledgeCategory] = useState("all");
  const [selectedSkillId, setSelectedSkillId] = useState("");
  const [selectedGate, setSelectedGate] = useState(1);
  const [skillDetail, setSkillDetail] = useState<SkillDetailResponse | null>(null);
  const [routeText, setRouteText] = useState("Build me an app that does gated skill loading with Kanban tracking.");
  const [routeComplexity, setRouteComplexity] = useState<Complexity | "">("");
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);
  const [newWorkTitle, setNewWorkTitle] = useState("");
  const [newWorkSummary, setNewWorkSummary] = useState("");
  const [newWorkStage, setNewWorkStage] = useState<WorkItemStage>("backlog");
  const [status, setStatus] = useState("Ready");
  const [busy, setBusy] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(true);
  const [isSkillsLoading, setIsSkillsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isTemplateLibraryLoading, setIsTemplateLibraryLoading] = useState(false);
  const [isSessionHistoryLoading, setIsSessionHistoryLoading] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState("");
  const [templateLibrary, setTemplateLibrary] = useState<TemplateRecord[]>([]);
  const [generatedDocuments, setGeneratedDocuments] = useState<GeneratedDocumentRecord[]>([]);
  const [knowledgeEntries, setKnowledgeEntries] = useState<MemoryRecord[]>([]);
  const [selectedHistorySessionId, setSelectedHistorySessionId] = useState("");
  const [sessionHistory, setSessionHistory] = useState<SessionHistoryResponse | null>(null);
  const [isKnowledgeLoading, setIsKnowledgeLoading] = useState(false);

  const activeProject =
    dashboard?.projects.find((project) => project.user_id === userId && project.visibility === "private") ??
    dashboard?.projects.find((project) => project.visibility === "shared") ??
    dashboard?.projects[0] ??
    null;
  const activeSkill = dashboard?.active_skill ?? null;
  const latestAlignment = dashboard?.latest_alignment ?? null;
  const recentEvents = dashboard?.recent_events ?? [];
  const sessionStory = dashboard?.session_story ?? null;
  const userSessions = dashboard?.user_sessions ?? [];
  const workItems = dashboard?.work_items ?? [];
  const parkingLot = dashboard?.parking_lot ?? [];

  const groupedWorkItems = useMemo(() => {
    return STAGES.map((stage) => ({
      stage,
      items: workItems.filter((item) => item.stage === stage)
    }));
  }, [workItems]);

  const completedWorkCount = workItems.filter((item) => item.stage === "done").length;
  const completionRate = workItems.length === 0 ? 0 : Math.round((completedWorkCount / workItems.length) * 100);
  const statusTone = getStatusTone(status, busy);
  const inFlightWorkCount = workItems.filter((item) => item.stage === "build" || item.stage === "review").length;

  useEffect(() => {
    void refreshDashboard().catch((error: Error) => setStatus(error.message));
  }, [userId]);

  // Auto-refresh dashboard every 5 seconds for live data
  useEffect(() => {
    const refreshInterval = setInterval(() => {
      void refreshDashboard().catch((error: Error) => setStatus(error.message));
    }, 5000);

    return () => clearInterval(refreshInterval);
  }, []);

  useEffect(() => {
    if (!activeProject?.project_id) {
      setTemplateLibrary([]);
      setGeneratedDocuments([]);
      return;
    }
    void refreshTemplateLibrary(activeProject.project_id).catch((error: Error) => {
      if (!error.message.includes("Not Found")) {
        setStatus(error.message);
      }
    });
  }, [userId, activeProject?.project_id]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await refreshKnowledgeBaseData({
          userId,
          projectId: activeProject?.project_id ?? "",
          query: deferredKnowledgeQuery,
          scope: knowledgeScope,
          category: knowledgeCategory,
          setKnowledgeEntries,
          setIsKnowledgeLoading
        });
        if (!cancelled) {
          return;
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error instanceof Error ? error.message : "Loading knowledge base failed");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [userId, activeProject?.project_id, deferredKnowledgeQuery, knowledgeScope, knowledgeCategory]);

  useEffect(() => {
    if (userSessions.length === 0) {
      setSelectedHistorySessionId("");
      setSessionHistory(null);
      return;
    }

    const preferredSessionId = userSessions.some((session) => session.session_id === sessionId)
      ? sessionId
      : userSessions[0].session_id;

    setSelectedHistorySessionId((current) => {
      if (current && userSessions.some((session) => session.session_id === current)) {
        return current;
      }
      return preferredSessionId;
    });
  }, [sessionId, userSessions]);

  useEffect(() => {
    if (!selectedHistorySessionId) {
      setSessionHistory(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        await loadSessionHistoryData({
          sessionId: selectedHistorySessionId,
          userId,
          setSessionHistory,
          setIsSessionHistoryLoading
        });
        if (!cancelled) {
          return;
        }
      } catch (error) {
        if (!cancelled) {
          setSessionHistory(null);
          setStatus(error instanceof Error ? error.message : "Loading session history failed");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedHistorySessionId, userId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setIsSkillsLoading(true);
      try {
        const nextSkills = await getSkills(deferredSkillQuery);
        if (cancelled) {
          return;
        }
        setSkills(nextSkills);
        if (nextSkills.length === 0) {
          setSelectedSkillId("");
          setSkillDetail(null);
          return;
        }

        setSelectedSkillId((currentSelectedSkillId) => {
          const stillExists = nextSkills.some((skill) => skill.skill_id === currentSelectedSkillId);
          if (stillExists) {
            return currentSelectedSkillId;
          }

          startTransition(() => {
            setSelectedGate(1);
          });
          return nextSkills[0].skill_id;
        });
        if (status === "{\"detail\":\"Not Found\"}") {
          setStatus("Ready");
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error instanceof Error ? error.message : "Loading skills failed");
        }
      } finally {
        if (!cancelled) {
          setIsSkillsLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [deferredSkillQuery]);

  useEffect(() => {
    if (!selectedSkillId) {
      return;
    }
    let cancelled = false;
    void (async () => {
      setIsDetailLoading(true);
      try {
        const detail = await getSkill(selectedSkillId, selectedGate);
        if (!cancelled) {
          setSkillDetail(detail);
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error instanceof Error ? error.message : "Loading detail failed");
        }
      } finally {
        if (!cancelled) {
          setIsDetailLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedSkillId, selectedGate]);

  async function refreshDashboard() {
    await refreshDashboardData({ sessionId, userId, setDashboard, setLastRefreshedAt, setIsDashboardLoading });
  }

  async function refreshTemplateLibrary(projectId = activeProject?.project_id ?? "") {
    await refreshTemplateLibraryData({
      projectId,
      userId,
      setTemplateLibrary,
      setGeneratedDocuments,
      setIsTemplateLibraryLoading
    });
  }

  async function refreshKnowledgeBase() {
    await refreshKnowledgeBaseData({
      userId,
      projectId: activeProject?.project_id ?? "",
      query: deferredKnowledgeQuery,
      scope: knowledgeScope,
      category: knowledgeCategory,
      setKnowledgeEntries,
      setIsKnowledgeLoading
    });
  }

  const actions = createRuntimeActions({
    sessionId,
    userId,
    clientType,
    activeProjectId: activeProject?.project_id ?? "",
    activeProjectName: activeProject?.name ?? "",
    selectedSkillId,
    selectedGate,
    skillDetail,
    routeText,
    routeComplexity,
    newWorkTitle,
    newWorkSummary,
    newWorkStage,
    deferredSkillQuery,
    deferredKnowledgeQuery,
    knowledgeScope,
    knowledgeCategory,
    setBusy,
    setStatus,
    setSkills,
    setSkillDetail,
    setSelectedSkillId,
    setSelectedGate,
    setRouteResult,
    setNewWorkTitle,
    setNewWorkSummary,
    setNewWorkStage,
    refreshDashboard,
    refreshTemplateLibrary: () => refreshTemplateLibrary(activeProject?.project_id ?? ""),
    refreshKnowledgeBase
  });

  return {
    sessionId,
    userId,
    clientType,
    dashboard,
    skills,
    deferredSkillQuery,
    skillQuery,
    selectedSkillId,
    selectedGate,
    skillDetail,
    routeText,
    routeComplexity,
    routeResult,
    newWorkTitle,
    newWorkSummary,
    newWorkStage,
    status,
    busy,
    isDashboardLoading,
    isSkillsLoading,
    isDetailLoading,
    lastRefreshedAt,
    activeProject,
    activeSkill,
    latestAlignment,
    recentEvents,
    sessionStory,
    userSessions,
    selectedHistorySessionId,
    sessionHistory,
    workItems,
    parkingLot,
    templateLibrary,
    generatedDocuments,
    knowledgeEntries,
    knowledgeQuery,
    knowledgeScope,
    knowledgeCategory,
    groupedWorkItems,
    completedWorkCount,
    completionRate,
    statusTone,
    inFlightWorkCount,
    isTemplateLibraryLoading,
    isSessionHistoryLoading,
    isKnowledgeLoading,
    setSkillQuery,
    setSelectedSkillId,
    setSelectedGate,
    setSelectedHistorySessionId,
    setRouteText,
    setRouteComplexity,
    setNewWorkTitle,
    setNewWorkSummary,
    setNewWorkStage,
    setKnowledgeQuery,
    setKnowledgeScope,
    setKnowledgeCategory,
    handleCompile: actions.handleCompile,
    handleRoute: actions.handleRoute,
    handleActivateSelectedSkill: actions.handleActivateSelectedSkill,
    handleScoreAlignment: actions.handleScoreAlignment,
    handleParkSelectedSkill: actions.handleParkSelectedSkill,
    handleResume: actions.handleResume,
    handleFeedback: actions.handleFeedback,
    handleCreateWorkItem: actions.handleCreateWorkItem,
    shiftWorkItem: actions.shiftWorkItem,
    refreshTemplateLibrary,
    refreshKnowledgeBase,
    handleCreateKnowledgeEntry: actions.handleCreateKnowledgeEntry,
    handleArchiveKnowledgeEntry: actions.handleArchiveKnowledgeEntry,
    handleToggleKnowledgePin: actions.handleToggleKnowledgePin,
    handleUploadTemplate: actions.handleUploadTemplate,
    handleCreateDocumentFromTemplate: actions.handleCreateDocumentFromTemplate,
    getTemplateDownloadHref: actions.getTemplateDownloadHref,
    getGeneratedDocumentDownloadHref: actions.getGeneratedDocumentDownloadHref
  };
}
