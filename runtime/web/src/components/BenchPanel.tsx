import { EmptyState, SectionHeading } from "../dashboardUi";
import type { ParkedSkillRecord } from "../types";

function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

interface BenchPanelProps {
  parkingLot: ParkedSkillRecord[];
  busy: boolean;
  onResume: (item: ParkedSkillRecord) => Promise<void>;
}

export function BenchPanel({ parkingLot, busy, onResume }: BenchPanelProps) {
  return (
    <section className="panel parking-panel">
      <SectionHeading
        kicker="Standby"
        title="Bench"
        subtitle="Keep likely follow-up specialists warm so users can keep moving instead of reloading context every step."
        meta={<span className="count-chip">{parkingLot.length} parked</span>}
      />
      <div className="parking-list">
        {parkingLot.length === 0 ? (
          <EmptyState title="No skills parked yet" detail="Park a loaded specialist to simulate context caching and faster follow-up retrieval." />
        ) : (
          parkingLot.map((item) => (
            <article key={item.parking_id} className="parking-card">
              <div>
                <strong>{item.display_name}</strong>
                <p>{item.note || "No note captured"}</p>
              </div>
              <div className="parking-meta">
                <span className="pill">Gate {item.gate_level}</span>
                <small>Parked {formatTime(item.parked_at)}</small>
                <button className="secondary-button" onClick={() => void onResume(item)} disabled={busy}>
                  Resume
                </button>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}