import { startTransition } from "react";

import {
  activateSkill,
  archiveMemory,
  compileRuntime,
  createMemory,
  createTemplateDocument,
  createWorkItem,
  getSkill,
  getSkills,
  getTemplateDocumentDownloadUrl,
  getTemplateDownloadUrl,
  parkSkill,
  recordFeedback,
  resumeSkill,
  routePrompt,
  scoreAlignment,
  updateMemory,
  updateWorkItem,
  uploadTemplate
} from "../api";
import { STAGES } from "../constants";
import type {
  ClientType,
  Complexity,
  MemoryRecord,
  MemoryScope,
  ParkedSkillRecord,
  RouteResponse,
  SkillDetailResponse,
  WorkItemRecord,
  WorkItemStage
} from "../types";

interface RuntimeActionFactoryArgs {
  sessionId: string;
  userId: string;
  clientType: ClientType;
  activeProjectId: string;
  activeProjectName: string;
  selectedSkillId: string;
  selectedGate: number;
  skillDetail: SkillDetailResponse | null;
  routeText: string;
  routeComplexity: Complexity | "";
  newWorkTitle: string;
  newWorkSummary: string;
  newWorkStage: WorkItemStage;
  deferredSkillQuery: string;
  deferredKnowledgeQuery: string;
  knowledgeScope: MemoryScope | "all";
  knowledgeCategory: string;
  setBusy: (value: boolean) => void;
  setStatus: (value: string) => void;
  setSkills: (value: any) => void;
  setSkillDetail: (value: SkillDetailResponse | null) => void;
  setSelectedSkillId: (value: string) => void;
  setSelectedGate: (value: number) => void;
  setRouteResult: (value: RouteResponse | null) => void;
  setNewWorkTitle: (value: string) => void;
  setNewWorkSummary: (value: string) => void;
  setNewWorkStage: (value: WorkItemStage) => void;
  refreshDashboard: () => Promise<void>;
  refreshTemplateLibrary: () => Promise<void>;
  refreshKnowledgeBase: () => Promise<void>;
}

export function createRuntimeActions(args: RuntimeActionFactoryArgs) {
  const {
    sessionId,
    userId,
    clientType,
    activeProjectId,
    activeProjectName,
    selectedSkillId,
    selectedGate,
    skillDetail,
    routeText,
    routeComplexity,
    newWorkTitle,
    newWorkSummary,
    newWorkStage,
    deferredSkillQuery,
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
    refreshTemplateLibrary,
    refreshKnowledgeBase
  } = args;

  return {
    async handleCompile() {
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
    },

    async handleRoute() {
      setBusy(true);
      try {
        const result = await routePrompt(routeText, routeComplexity || undefined, sessionId, userId, activeProjectId, clientType);
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
    },

    async handleActivateSelectedSkill() {
      if (!skillDetail) {
        return;
      }
      setBusy(true);
      try {
        await activateSkill(skillDetail.skill.skill_id, {
          session_id: sessionId,
          user_id: userId,
          project_id: activeProjectId,
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
    },

    async handleScoreAlignment() {
      if (!skillDetail) {
        return;
      }
      setBusy(true);
      try {
        await scoreAlignment({
          session_id: sessionId,
          user_id: userId,
          project_id: activeProjectId,
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
    },

    async handleParkSelectedSkill() {
      if (!skillDetail) {
        return;
      }
      setBusy(true);
      try {
        await parkSkill(skillDetail.skill.skill_id, sessionId, userId, activeProjectId, clientType, selectedGate, routeText);
        await refreshDashboard();
        setStatus(`Parked ${skillDetail.skill.display_name} at gate ${selectedGate}.`);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Parking failed");
      } finally {
        setBusy(false);
      }
    },

    async handleResume(item: ParkedSkillRecord) {
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
    },

    async handleFeedback(rating: "correct" | "wrong") {
      if (!skillDetail) {
        return;
      }
      setBusy(true);
      try {
        await recordFeedback({
          session_id: sessionId,
          user_id: userId,
          project_id: activeProjectId,
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
    },

    async handleCreateWorkItem() {
      if (!activeProjectId || !newWorkTitle.trim()) {
        return;
      }
      setBusy(true);
      try {
        await createWorkItem({
          project_id: activeProjectId,
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
    },

    async shiftWorkItem(item: WorkItemRecord, direction: -1 | 1) {
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
    },

    async handleUploadTemplate(file: File, name: string, category: string, description: string) {
      if (!activeProjectId) {
        setStatus("Create or select a project before uploading templates.");
        return;
      }
      setBusy(true);
      try {
        await uploadTemplate(activeProjectId, { userId, name, category, description, file });
        await refreshTemplateLibrary();
        setStatus(`Uploaded template "${name || file.name}" to ${activeProjectName}.`);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Template upload failed");
      } finally {
        setBusy(false);
      }
    },

    async handleCreateDocumentFromTemplate(templateId: string, name: string, description: string) {
      if (!activeProjectId) {
        setStatus("Create or select a project before generating documents.");
        return;
      }
      setBusy(true);
      try {
        await createTemplateDocument(activeProjectId, templateId, { user_id: userId, name, description });
        await refreshTemplateLibrary();
        setStatus(`Created "${name}" from the selected template.`);
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Document generation failed");
      } finally {
        setBusy(false);
      }
    },

    async handleCreateKnowledgeEntry(payload: {
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
          project_id: payload.scope === "project" ? payload.projectId ?? activeProjectId : "",
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
    },

    async handleArchiveKnowledgeEntry(memoryId: string) {
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
    },

    async handleToggleKnowledgePin(entry: MemoryRecord) {
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
    },

    getTemplateDownloadHref(templateId: string) {
      return getTemplateDownloadUrl(templateId, userId);
    },

    getGeneratedDocumentDownloadHref(documentId: string) {
      return getTemplateDocumentDownloadUrl(documentId, userId);
    }
  };
}