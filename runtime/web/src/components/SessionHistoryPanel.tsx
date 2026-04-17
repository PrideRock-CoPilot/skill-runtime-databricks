import { useEffect, useMemo, useState } from "react";

import { EmptyState, SectionHeading } from "../dashboardUi";
import type { ProjectRecord, SessionHistoryResponse, SessionRecord } from "../types";

function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

function trimPrompt(value: string): string {
  const cleaned = value.trim();
  if (!cleaned) {
    return "No routed prompt captured for this session yet.";
  }
  return cleaned.length > 120 ? `${cleaned.slice(0, 117)}...` : cleaned;
}

interface SessionHistoryPanelProps {
  activeProject: ProjectRecord | null;
  currentSessionId: string;
  userSessions: SessionRecord[];
  selectedSessionId: string;
  sessionHistory: SessionHistoryResponse | null;
  isLoading: boolean;
  onSelectSession: (sessionId: string) => void;
}

export function SessionHistoryPanel({
  activeProject,
  currentSessionId,
  userSessions,
  selectedSessionId,
  sessionHistory,
  isLoading,
  onSelectSession
}: SessionHistoryPanelProps) {
  const [selectedEntryId, setSelectedEntryId] = useState("");

  const projectSessions = userSessions.filter((session) => session.history_scope === "project").length;
  const workspaceSessions = userSessions.filter((session) => session.history_scope === "workspace").length;
  const selectedEntry = useMemo(
    () => sessionHistory?.timeline.find((entry) => entry.entry_id === selectedEntryId) ?? null,
    [sessionHistory, selectedEntryId]
  );

  useEffect(() => {
    setSelectedEntryId("");
  }, [selectedSessionId]);

  useEffect(() => {
    if (!sessionHistory || !selectedEntryId) {
      return;
    }
    if (!sessionHistory.timeline.some((entry) => entry.entry_id === selectedEntryId)) {
      setSelectedEntryId("");
    }
  }, [sessionHistory, selectedEntryId]);

  return (
    <section className="panel session-history-panel">
      <SectionHeading
        kicker="History"
        title="Connected sessions"
        subtitle={
          activeProject
            ? `Showing sessions tied to ${activeProject.name} and the end user's recent workspace requests. Project-linked sessions retain longer history; workspace sessions roll after 30 days.`
            : "Project-linked sessions retain longer history. Workspace-only sessions are shown for the last 30 days."
        }
        meta={<span className="count-chip">{userSessions.length} visible sessions</span>}
      />

      <div className="session-summary-row">
        <span className="pill">Project sessions: {projectSessions}</span>
        <span className="pill">Workspace sessions: {workspaceSessions}</span>
      </div>

      <div className="session-history-layout">
        <div className="session-list">
          {userSessions.length === 0 ? (
            <EmptyState compact title="No sessions yet" detail="Once routing starts, connected sessions for this user will appear here." />
          ) : (
            userSessions.map((session) => {
              const isSelected = session.session_id === selectedSessionId;
              const isCurrent = session.session_id === currentSessionId;
              return (
                <button
                  key={session.session_id}
                  className={`session-list-item ${isSelected ? "selected" : ""}`}
                  onClick={() => onSelectSession(session.session_id)}
                  type="button"
                >
                  <div className="session-list-header">
                    <strong>{session.project_name || "Workspace session"}</strong>
                    <span className="pill">{session.history_scope === "project" ? "project" : "30-day workspace"}</span>
                  </div>
                  <p>{trimPrompt(session.last_route_prompt)}</p>
                  <div className="session-list-meta">
                    <span>{session.client_type}</span>
                    <span>{session.route_count} routes</span>
                    <span>{session.event_count} events</span>
                    {isCurrent ? <span className="pill">current</span> : null}
                  </div>
                  <small>{formatTime(session.last_used_at)}</small>
                </button>
              );
            })
          )}
        </div>

        <div className="session-history-detail">
          {!selectedSessionId ? (
            <EmptyState compact title="Select a session" detail="Pick a connected session to inspect its routing and worker history." />
          ) : isLoading ? (
            <EmptyState compact title="Loading history" detail="Pulling the session timeline from the runtime store." />
          ) : !sessionHistory ? (
            <EmptyState compact title="History unavailable" detail="This session may have rolled out of retention or has not captured any timeline entries yet." />
          ) : (
            <>
              <div className="session-detail-header">
                <div>
                  <span className="micro-pill">Selected session</span>
                  <h3>{sessionHistory.session.project_name || "Workspace session"}</h3>
                  <p>{trimPrompt(sessionHistory.session.last_route_prompt)}</p>
                </div>
                <div className="session-detail-meta">
                  <span className="pill">{sessionHistory.session.client_type}</span>
                  <span className="pill">{sessionHistory.session.status || "active"}</span>
                </div>
              </div>

              <div className="session-timeline">
                {sessionHistory.timeline.length === 0 ? (
                  <EmptyState compact title="No timeline entries" detail="Routes, worker events, and alignment checks will show up here for this session." />
                ) : (
                  sessionHistory.timeline.map((entry) => (
                    <button
                      key={entry.entry_id}
                      type="button"
                      className={`session-timeline-entry session-timeline-entry-button ${selectedEntryId === entry.entry_id ? "selected" : ""}`}
                      onClick={() => setSelectedEntryId(entry.entry_id)}
                    >
                      <div>
                        <strong>{entry.title}</strong>
                        <p>{entry.detail}</p>
                      </div>
                      <div className="session-timeline-meta">
                        <span className="pill">{entry.entry_type}</span>
                        <small>{formatTime(entry.created_at)}</small>
                      </div>
                    </button>
                  ))
                )}
              </div>

              <aside className={`event-drawer ${selectedEntry ? "open" : ""}`}>
                {selectedEntry ? (
                  <>
                    <div className="event-drawer-header">
                      <div>
                        <span className="micro-pill">Event detail</span>
                        <h4>{selectedEntry.title}</h4>
                      </div>
                      <button type="button" className="ghost-button" onClick={() => setSelectedEntryId("")}>
                        Close
                      </button>
                    </div>
                    <div className="event-drawer-body">
                      <div className="event-drawer-row">
                        <span>Type</span>
                        <strong>{selectedEntry.entry_type}</strong>
                      </div>
                      <div className="event-drawer-row">
                        <span>Time</span>
                        <strong>{formatTime(selectedEntry.created_at)}</strong>
                      </div>
                      <div className="event-drawer-row">
                        <span>Skill</span>
                        <strong>{selectedEntry.skill_id || "(none)"}</strong>
                      </div>
                      <div className="event-drawer-row">
                        <span>Event ID</span>
                        <strong>{selectedEntry.entry_id}</strong>
                      </div>
                      <div className="event-drawer-detail">
                        <span>Detail</span>
                        <p>{selectedEntry.detail}</p>
                      </div>
                    </div>
                  </>
                ) : (
                  <EmptyState compact title="Select an event" detail="Click a timeline entry to inspect its full details in this drawer." />
                )}
              </aside>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
