import { AppHeader } from "./components/AppHeader";
import { AppTabs } from "./components/AppTabs";
import { useRuntimeApp } from "./hooks/useRuntimeApp";
import { useUserPreferences } from "./hooks/useUserPreferences";
import { BoardWorkspace } from "./views/BoardWorkspace";
import { KnowledgeWorkspace } from "./views/KnowledgeWorkspace";
import { PreferencesWorkspace } from "./views/PreferencesWorkspace";
import { SessionsWorkspace } from "./views/SessionsWorkspace";
import { SkillsWorkspace } from "./views/SkillsWorkspace";

export default function App() {
  const { activeTab, setActiveTab, preferences, updatePreference, toggleFavorite, toggleDownvote } = useUserPreferences();
  const runtime = useRuntimeApp(preferences.userId, preferences.clientType);

  async function handleFeedback(rating: "correct" | "wrong") {
    await runtime.handleFeedback(rating);
    if (preferences.autoParkAfterFeedback && runtime.skillDetail) {
      await runtime.handleParkSelectedSkill();
    }
  }

  return (
    <div className={`app-shell mode-${preferences.workspaceMode} ${preferences.compactBoard ? "compact-board" : ""}`}>
      <AppHeader
        sessionId={runtime.sessionId}
        operatorName={runtime.authContext?.display_name ?? preferences.operatorName}
        userId={runtime.authContext?.email ?? preferences.userId}
        clientType={preferences.clientType}
        authProvider={runtime.authContext?.provider ?? "local"}
        authenticated={runtime.authContext?.authenticated ?? false}
        workspaceHost={runtime.authContext?.workspace_host ?? ""}
        isSkillsLoading={runtime.isSkillsLoading}
        skillsCount={runtime.skills.length}
        inFlightWorkCount={runtime.inFlightWorkCount}
        benchCount={runtime.parkingLot.length}
        activeSkill={runtime.activeSkill}
        latestAlignment={runtime.latestAlignment}
        sessionStory={runtime.sessionStory}
        recentEvents={runtime.recentEvents}
        workItems={runtime.workItems}
        activeProjectName={runtime.activeProject?.name ?? null}
        activeProjectOwner={runtime.activeProject?.owner_name ?? null}
        busy={runtime.busy}
        status={runtime.status}
        statusTone={runtime.statusTone}
        isDashboardLoading={runtime.isDashboardLoading}
        isDashboardStreaming={runtime.isDashboardStreaming}
        lastRefreshedAt={runtime.lastRefreshedAt}
        onCompile={runtime.handleCompile}
      />

      <AppTabs activeTab={activeTab} onChange={setActiveTab} />

      <main className="app-main">
        {activeTab === "board" ? <BoardWorkspace runtime={runtime} onFeedback={handleFeedback} /> : null}
        {activeTab === "skills" ? (
          <SkillsWorkspace
            runtime={runtime}
            showRetroSkills={preferences.showRetroSkills}
            favoriteSkillIds={preferences.favoriteSkillIds}
            downvotedSkillIds={preferences.downvotedSkillIds}
            onToggleFavorite={toggleFavorite}
            onToggleDownvote={toggleDownvote}
            onFeedback={handleFeedback}
          />
        ) : null}
        {activeTab === "knowledge" ? <KnowledgeWorkspace runtime={runtime} /> : null}
        {activeTab === "sessions" ? <SessionsWorkspace runtime={runtime} /> : null}
        {activeTab === "preferences" ? (
          <PreferencesWorkspace runtime={runtime} preferences={preferences} onPreferenceChange={updatePreference} />
        ) : null}
      </main>
    </div>
  );
}
