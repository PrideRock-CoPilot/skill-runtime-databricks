import { SessionHistoryPanel } from "../components/SessionHistoryPanel";
import type { RuntimeAppModel } from "../hooks/useRuntimeApp";

interface SessionsWorkspaceProps {
  runtime: RuntimeAppModel;
}

export function SessionsWorkspace({ runtime }: SessionsWorkspaceProps) {
  return (
    <div className="sessions-workspace">
      <section className="panel sessions-intro-panel">
        <div className="sessions-intro-copy">
          <p className="panel-kicker">Connected Sessions</p>
          <h2>Track your usage and routing history</h2>
          <p>
            View sessions tied to your projects and workspace requests. Project-linked sessions retain longer history; workspace sessions roll after 30 days.
          </p>
        </div>
      </section>

      <SessionHistoryPanel
        activeProject={runtime.activeProject}
        currentSessionId={runtime.sessionId}
        userSessions={runtime.userSessions}
        selectedSessionId={runtime.selectedHistorySessionId}
        sessionHistory={runtime.sessionHistory}
        isLoading={runtime.isSessionHistoryLoading}
        onSelectSession={runtime.setSelectedHistorySessionId}
      />
    </div>
  );
}
