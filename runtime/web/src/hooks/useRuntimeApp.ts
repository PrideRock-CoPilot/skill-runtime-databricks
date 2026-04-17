import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import {
  activateSkill,
  archiveMemory,
  compileRuntime,
  createMemory,
  createTemplateDocument,
  createWorkItem,
  getDashboard,
  getSessionHistory,
  getTemplateDocumentDownloadUrl,
  getTemplateDownloadUrl,
  getSkill,
  getSkills,
  listMemories,
  listTemplateDocuments,
  listTemplates,
  parkSkill,
  recordFeedback,
  resumeSkill,
  routePrompt,
  scoreAlignment,
  uploadTemplate,
  updateMemory,
  updateWorkItem
} from "../api";
import { STAGES } from "../constants";
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
      setIsKnowledgeLoading(true);
      try {
        const entries = await listMemories({
          userId,
          projectId: activeProject?.project_id ?? "",
          query: deferredKnowledgeQuery,
          scope: knowledgeScope,
          category: knowledgeCategory,
          limit: 24
        });
        if (!cancelled) {
          setKnowledgeEntries(entries);
        }
      } catch (error) {
        if (!cancelled) {
          setStatus(error instanceof Error ? error.message : "Loading knowledge base failed");
        }
      } finally {
        if (!cancelled) {
          setIsKnowledgeLoading(false);
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
      setIsSessionHistoryLoading(true);
      try {
        const history = await getSessionHistory(selectedHistorySessionId, userId);
        if (!cancelled) {
          setSessionHistory(history);
        }
      } catch (error) {
        if (!cancelled) {
          setSessionHistory(null);
          setStatus(error instanceof Error ? error.message : "Loading session history failed");
        }
      } finally {
        if (!cancelled) {
          setIsSessionHistoryLoading(false);
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
    setIsDashboardLoading(true);
    try {
      const nextDashboard = await getDashboard(sessionId, userId);
      setDashboard(nextDashboard);
      setLastRefreshedAt(new Date().toISOString());
    } finally {
      setIsDashboardLoading(false);
    }
  }

  async function refreshTemplateLibrary(projectId = activeProject?.project_id ?? "") {
    if (!projectId) {
      setTemplateLibrary([]);
      setGeneratedDocuments([]);
      return;
    }
    setIsTemplateLibraryLoading(true);
    try {
      const [templates, documents] = await Promise.all([
        listTemplates(projectId, userId),
        listTemplateDocuments(projectId, userId)
      ]);
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

  async function refreshKnowledgeBase() {
    setIsKnowledgeLoading(true);
    try {
      const entries = await listMemories({
        userId,
        projectId: activeProject?.project_id ?? "",
        query: deferredKnowledgeQuery,
        scope: knowledgeScope,
        category: knowledgeCategory,
        limit: 24
      });
      setKnowledgeEntries(entries);
    } finally {
      setIsKnowledgeLoading(false);
    }
  }

  async function handleCompile() {
    setBusy(true);
    try {
      const result = await compileRuntime();
      setStatus(`Recompiled ${result.skills} skills into ${result.bundles} gated bundles.`);
      const nextSkills = await getSkills(deferredSkillQuery);
      setSkills(nextSkills);
      await refreshDashboard();
      if (selectedSkillId) {
        setSkillDetail(await getSkill(selectedSkillId, selectedGate));
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Compile failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRoute() {
    setBusy(true);
    try {
      const result = await routePrompt(
        routeText,
        routeComplexity || undefined,
        sessionId,
        userId,
        activeProject?.project_id ?? "",
        clientType
      );
      setRouteResult(result);
      if (result.matches.length > 0) {
        startTransition(() => {
          setSelectedSkillId(result.matches[0].skill_id);
          setSelectedGate(result.recommended_gate);
        });
      }
      await refreshDashboard();
      setStatus(`Routed prompt at ${result.complexity} complexity.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Routing failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleActivateSelectedSkill() {
    if (!skillDetail) {
      return;
    }
    setBusy(true);
    try {
      await activateSkill(skillDetail.skill.skill_id, {
        session_id: sessionId,
        user_id: userId,
        project_id: activeProject?.project_id ?? "",
        client_type: clientType,
        gate_level: selectedGate,
        prompt: routeText,
        activation_reason: "Activated from the runtime dashboard."
      });
      await refreshDashboard();
      setStatus(`Activated ${skillDetail.skill.display_name} at gate ${selectedGate}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Activation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleScoreAlignment() {
    if (!skillDetail) {
      return;
    }
    setBusy(true);
    try {
      await scoreAlignment({
        session_id: sessionId,
        user_id: userId,
        project_id: activeProject?.project_id ?? "",
        skill_id: skillDetail.skill.skill_id,
        prompt: routeText || skillDetail.skill.description,
        response_excerpt: skillDetail.bundles[0]?.content.slice(0, 400) ?? skillDetail.skill.description,
        gate_level: selectedGate,
        note: "Dashboard alignment check"
      });
      await refreshDashboard();
      setStatus(`Scored alignment for ${skillDetail.skill.display_name}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Alignment scoring failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleParkSelectedSkill() {
    if (!skillDetail) {
      return;
    }
    setBusy(true);
    try {
      await parkSkill(
        skillDetail.skill.skill_id,
        sessionId,
        userId,
        activeProject?.project_id ?? "",
        clientType,
        selectedGate,
        routeText
      );
      await refreshDashboard();
      setStatus(`Parked ${skillDetail.skill.display_name} at gate ${selectedGate}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Parking failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleResume(item: ParkedSkillRecord) {
    setBusy(true);
    try {
      await resumeSkill(item.skill_id, sessionId, userId);
      setSelectedSkillId(item.skill_id);
      setSelectedGate(item.gate_level);
      setSkillDetail(await getSkill(item.skill_id, item.gate_level));
      await refreshDashboard();
      setStatus(`Resumed ${item.display_name} from the parking lot.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Resume failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleFeedback(rating: "correct" | "wrong") {
    if (!skillDetail) {
      return;
    }
    setBusy(true);
    try {
      await recordFeedback({
        session_id: sessionId,
        user_id: userId,
        project_id: activeProject?.project_id ?? "",
        client_type: clientType,
        skill_id: skillDetail.skill.skill_id,
        rating,
        prompt: routeText || skillDetail.skill.description,
        response_excerpt: skillDetail.bundles[0]?.content.slice(0, 300) ?? "",
        note: `Feedback captured at gate ${selectedGate}`
      });
      await refreshDashboard();
      setStatus(`Stored ${rating} feedback for ${skillDetail.skill.display_name}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Feedback failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateWorkItem() {
    if (!activeProject || !newWorkTitle.trim()) {
      return;
    }
    setBusy(true);
    try {
      await createWorkItem({
        project_id: activeProject.project_id,
        user_id: userId,
        title: newWorkTitle.trim(),
        summary: newWorkSummary.trim(),
        stage: newWorkStage,
        owner_skill_id: selectedSkillId,
        owner_display_name: skillDetail?.skill.display_name ?? "Unassigned",
        priority: "medium"
      });
      setNewWorkTitle("");
      setNewWorkSummary("");
      setNewWorkStage("backlog");
      await refreshDashboard();
      setStatus("Created a new AI work item.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Create work item failed");
    } finally {
      setBusy(false);
    }
  }

  async function shiftWorkItem(item: WorkItemRecord, direction: -1 | 1) {
    const currentIndex = STAGES.indexOf(item.stage);
    const nextStage = STAGES[currentIndex + direction];
    if (!nextStage) {
      return;
    }
    setBusy(true);
    try {
      await updateWorkItem(item.work_item_id, { stage: nextStage });
      await refreshDashboard();
      setStatus(`Moved "${item.title}" to ${nextStage}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Move failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleUploadTemplate(file: File, name: string, category: string, description: string) {
    if (!activeProject?.project_id) {
      setStatus("Create or select a project before uploading templates.");
      return;
    }
    setBusy(true);
    try {
      await uploadTemplate(activeProject.project_id, {
        userId,
        name,
        category,
        description,
        file
      });
      await refreshTemplateLibrary(activeProject.project_id);
      setStatus(`Uploaded template "${name || file.name}" to ${activeProject.name}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Template upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateDocumentFromTemplate(templateId: string, name: string, description: string) {
    if (!activeProject?.project_id) {
      setStatus("Create or select a project before generating documents.");
      return;
    }
    setBusy(true);
    try {
      await createTemplateDocument(activeProject.project_id, templateId, {
        user_id: userId,
        name,
        description
      });
      await refreshTemplateLibrary(activeProject.project_id);
      setStatus(`Created "${name}" from the selected template.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Document generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateKnowledgeEntry(payload: {
    scope: MemoryScope;
    subject: string;
    content: string;
    category: string;
    tags: string;
    pinned: boolean;
    projectId?: string;
  }) {
    setBusy(true);
    try {
      await createMemory(userId, sessionId, {
        scope: payload.scope,
        subject: payload.subject,
        content: payload.content,
        category: payload.category,
        project_id: payload.scope === "project" ? payload.projectId ?? activeProject?.project_id ?? "" : "",
        tags: payload.tags,
        pinned: payload.pinned,
        source: "user",
        owner: "end-user"
      });
      await refreshKnowledgeBase();
      setStatus(`Stored knowledge entry "${payload.subject}".`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Knowledge entry save failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleArchiveKnowledgeEntry(memoryId: string) {
    setBusy(true);
    try {
      await archiveMemory(memoryId, userId);
      await refreshKnowledgeBase();
      setStatus("Archived knowledge entry.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Knowledge archive failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleKnowledgePin(entry: MemoryRecord) {
    setBusy(true);
    try {
      await updateMemory(entry.memory_id, userId, { pinned: !entry.pinned });
      await refreshKnowledgeBase();
      setStatus(`${entry.pinned ? "Unpinned" : "Pinned"} knowledge entry "${entry.subject}".`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Knowledge update failed");
    } finally {
      setBusy(false);
    }
  }

  function getTemplateDownloadHref(templateId: string) {
    return getTemplateDownloadUrl(templateId, userId);
  }

  function getGeneratedDocumentDownloadHref(documentId: string) {
    return getTemplateDocumentDownloadUrl(documentId, userId);
  }

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
    handleCompile,
    handleRoute,
    handleActivateSelectedSkill,
    handleScoreAlignment,
    handleParkSelectedSkill,
    handleResume,
    handleFeedback,
    handleCreateWorkItem,
    shiftWorkItem,
    refreshTemplateLibrary,
    refreshKnowledgeBase,
    handleCreateKnowledgeEntry,
    handleArchiveKnowledgeEntry,
    handleToggleKnowledgePin,
    handleUploadTemplate,
    handleCreateDocumentFromTemplate,
    getTemplateDownloadHref,
    getGeneratedDocumentDownloadHref
  };
}
