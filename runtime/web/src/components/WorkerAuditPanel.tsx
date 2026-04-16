import { EmptyState, SectionHeading } from "../dashboardUi";
import type { ActiveSkillRecord, AlignmentRecord, SessionStory, SkillEventRecord } from "../types";

function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

interface WorkerAuditPanelProps {
  activeSkill: ActiveSkillRecord | null;
  latestAlignment: AlignmentRecord | null;
  recentEvents: SkillEventRecord[];
  sessionStory: SessionStory | null;
}

export function WorkerAuditPanel({ activeSkill, latestAlignment, recentEvents, sessionStory }: WorkerAuditPanelProps) {
  const timeline = sessionStory?.timeline ?? [];
  return (
    <section className="panel parking-panel">
      <SectionHeading
        kicker="Proof"
        title="Active worker and audit"
        subtitle="Show the current worker, the latest alignment score, and the recent event trail for this user session."
        meta={<span className="count-chip">{recentEvents.length} events</span>}
      />

      <div className="bundle-list">
        <article className="bundle-card">
          <div className="bundle-header">
            <div>
              <span className="micro-pill">Active worker</span>
              <h3>{activeSkill?.display_name ?? "No worker active"}</h3>
            </div>
            <small>{activeSkill ? `Gate ${activeSkill.gate_level}` : "Pending activation"}</small>
          </div>
          <div className="bundle-content">
            {activeSkill
              ? `${activeSkill.activation_reason}\n\nPrompt: ${activeSkill.route_prompt || "No activation prompt captured."}`
              : "The runtime has not activated a worker for this session yet."}
          </div>
        </article>

        <article className="bundle-card">
          <div className="bundle-header">
            <div>
              <span className="micro-pill">Latest alignment</span>
              <h3>{latestAlignment ? `${latestAlignment.score}/100 ${latestAlignment.status}` : "No alignment scored"}</h3>
            </div>
            <small>{latestAlignment ? formatTime(latestAlignment.created_at) : "Pending"}</small>
          </div>
          <div className="bundle-content">
            {latestAlignment?.summary ??
              "Run alignment scoring after activation so the user can see whether the active worker is really driving the turn."}
          </div>
        </article>
      </div>

      <div className="parking-list">
        {timeline.length === 0 && recentEvents.length === 0 ? (
          <EmptyState
            title="No events yet"
            detail="Routing, activation, feedback, handoffs, and alignment scores will appear here for the current session."
          />
        ) : (
          (timeline.length > 0
            ? timeline.map((item, index) => (
                <article key={`${item.title}-${item.time}-${index}`} className="parking-card">
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </div>
                  <div className="parking-meta">
                    <span className="pill">flow step</span>
                    <small>{formatTime(item.time)}</small>
                  </div>
                </article>
              ))
            : recentEvents.map((event) => (
                <article key={event.event_id} className="parking-card">
                  <div>
                    <strong>{event.event_type}</strong>
                    <p>{event.summary}</p>
                  </div>
                  <div className="parking-meta">
                    <span className="pill">{event.skill_id || "no-skill"}</span>
                    <small>{formatTime(event.created_at)}</small>
                  </div>
                </article>
              )))
        )}
      </div>
    </section>
  );
}
