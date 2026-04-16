import { OverviewCard } from "../dashboardUi";
import { getWorkSummary } from "../utils";
import type { ActiveSkillRecord, AlignmentRecord, ClientType, SessionStory, SkillEventRecord, WorkItemRecord } from "../types";

interface AppHeaderProps {
  sessionId: string;
  operatorName: string;
  userId: string;
  clientType: ClientType;
  isSkillsLoading: boolean;
  skillsCount: number;
  inFlightWorkCount: number;
  benchCount: number;
  activeSkill: ActiveSkillRecord | null;
  latestAlignment: AlignmentRecord | null;
  sessionStory: SessionStory | null;
  recentEvents: SkillEventRecord[];
  workItems: WorkItemRecord[];
  activeProjectName: string | null;
  activeProjectOwner: string | null;
  busy: boolean;
  status: string;
  statusTone: "ready" | "working" | "error";
  isDashboardLoading: boolean;
  lastRefreshedAt: string;
  onCompile: () => Promise<void>;
}

function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

export function AppHeader({
  sessionId,
  operatorName,
  userId,
  clientType,
  isSkillsLoading,
  skillsCount,
  inFlightWorkCount,
  benchCount,
  activeSkill,
  latestAlignment,
  sessionStory,
  recentEvents,
  workItems,
  activeProjectName,
  activeProjectOwner,
  busy,
  status,
  statusTone,
  isDashboardLoading,
  lastRefreshedAt,
  onCompile
}: AppHeaderProps) {
  const latestEvent = recentEvents[0] ?? null;

  function feedbackTitle(eventType: string): string {
    if (eventType === "hiring_process_started") {
      return "Hiring process started";
    }
    if (eventType === "skill_activated") {
      return "Worker activated";
    }
    if (eventType === "alignment_scored") {
      return "Quality check updated";
    }
    if (eventType === "feedback_recorded") {
      return "Feedback captured";
    }
    return "MCP update";
  }

  const showGeneralEventBanner = latestEvent && latestEvent.event_type !== "hiring_process_started";
  const ledClass = busy ? "busy" : "online";

  return (
    <>
      {sessionStory?.hiring_in_progress || showGeneralEventBanner ? (
        <section className="feedback-banner-rail" aria-label="MCP feedback banners">
          {sessionStory?.hiring_in_progress ? (
            <section className="hiring-banner" role="status" aria-live="polite">
              <strong>Hiring process started</strong>
              <p>
                No strong specialist found. TalentDirector is building coverage — a hiring task has been added to your board.
              </p>
            </section>
          ) : null}

          {showGeneralEventBanner ? (
            <section className="server-feedback-banner" role="status" aria-live="polite">
              <strong>{feedbackTitle(latestEvent.event_type)}</strong>
              <p>{latestEvent.summary}</p>
            </section>
          ) : null}
        </section>
      ) : null}

      <header className="hero">
        <div className="hero-copy-block">
          <p className="eyebrow">Skill Runtime</p>
          <h1>Control Room</h1>
          <div className="hero-badges">
            <span className="hero-badge"><span className={`status-led ${ledClass}`} />{operatorName}</span>
            <span className="hero-badge">{userId}</span>
            <span className="hero-badge">{clientType}</span>
          </div>
        </div>
        <div className="hero-panel">
          <div className="hero-panel-header">
            <span className="status-chip hero-status-chip">
              <span>Session</span>
              <strong>{sessionId.slice(0, 20)}...</strong>
            </span>
            <button className="primary-button" onClick={() => void onCompile()} disabled={busy}>
              Recompile
            </button>
          </div>
        </div>
      </header>

      <section className="overview-strip" aria-label="Runtime overview">
        <OverviewCard
          label="Dispatch queue"
          value={isSkillsLoading ? "..." : String(skillsCount)}
          detail="Specialists in the runtime"
          tone="accent"
        />
        <OverviewCard
          label="Standby bench"
          value={String(benchCount)}
          detail={benchCount === 0 ? "No follow-ups warmed" : "Ready for reassignment"}
          tone="calm"
        />
        <OverviewCard label="Board pressure" value={String(workItems.length)} detail={getWorkSummary(workItems)} tone="strong" />
        <OverviewCard
          label="Active worker"
          value={activeSkill?.display_name ?? "None"}
          detail={
            latestAlignment
              ? `Alignment ${latestAlignment.score}/100`
              : activeProjectName
                ? `${activeProjectName}`
                : "Waiting for activation"
          }
          tone="accent"
        />
      </section>

      <section className={`status-bar ${statusTone}`}>
        <div>
          <span className="muted-label">System status</span>
          <strong className="status-text"><span className={`status-led ${ledClass}`} />{status}</strong>
        </div>
        <div className="status-meta">
          <span className="pill">{busy ? "Working" : isDashboardLoading ? "Refreshing" : "Idle"}</span>
          <span className="pill">{formatTime(lastRefreshedAt)}</span>
        </div>
      </section>
    </>
  );
}
