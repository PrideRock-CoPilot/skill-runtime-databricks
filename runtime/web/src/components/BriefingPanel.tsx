import { GATES } from "../constants";
import { EmptyState, SectionHeading } from "../dashboardUi";
import type { SkillDetailResponse } from "../types";

interface BriefingPanelProps {
  skillDetail: SkillDetailResponse | null;
  selectedGate: number;
  isDetailLoading: boolean;
  busy: boolean;
  onSelectGate: (gate: number) => void;
  onActivate: () => Promise<void>;
  onPark: () => Promise<void>;
  onScoreAlignment: () => Promise<void>;
  onFeedback: (rating: "correct" | "wrong") => Promise<void>;
}

export function BriefingPanel({
  skillDetail,
  selectedGate,
  isDetailLoading,
  busy,
  onSelectGate,
  onActivate,
  onPark,
  onScoreAlignment,
  onFeedback
}: BriefingPanelProps) {
  return (
    <section className="panel detail-panel workspace-detail-panel">
      <SectionHeading
        kicker="Briefing"
        title={skillDetail?.skill.display_name ?? "Choose a skill"}
        subtitle="Load the gate bundle, then activate the worker contract you want controlling the turn."
        actions={
          <div className="inline-controls">
            <button className="secondary-button" onClick={() => void onActivate()} disabled={!skillDetail || busy}>
              Activate
            </button>
            <button className="secondary-button" onClick={() => void onScoreAlignment()} disabled={!skillDetail || busy}>
              Score
            </button>
            <button className="secondary-button" onClick={() => void onPark()} disabled={!skillDetail || busy}>
              Park
            </button>
          </div>
        }
      />

      <div className="gate-strip">
        {GATES.map((gate) => (
          <button
            key={gate.level}
            className={`gate-chip ${selectedGate === gate.level ? "active" : ""}`}
            onClick={() => onSelectGate(gate.level)}
          >
            <span>{gate.label}</span>
            <small>{gate.detail}</small>
          </button>
        ))}
      </div>

      {isDetailLoading ? (
        <EmptyState compact title="Loading gate bundle" detail="Fetching the current skill context for this gate." />
      ) : skillDetail ? (
        <>
          <div className="skill-meta">
            <span className="pill">{skillDetail.skill.slug}</span>
            <span className="pill">{skillDetail.skill.source_dir}</span>
            <span className="pill">Gates loaded: {skillDetail.loaded_gates.join(", ")}</span>
          </div>
          <div className="feedback-row">
            <button className="secondary-button" onClick={() => void onFeedback("correct")} disabled={busy}>
              Yes, correct
            </button>
            <button className="secondary-button warning" onClick={() => void onFeedback("wrong")} disabled={busy}>
              No, wrong
            </button>
          </div>
          {skillDetail.bundles.length === 0 ? (
            <EmptyState compact title="No bundles at this gate" detail="Try a deeper gate or recompile the runtime." />
          ) : (
            <div className="bundle-list">
              {skillDetail.bundles.map((bundle) => (
                <article key={bundle.bundle_id} className="bundle-card">
                  <div className="bundle-header">
                    <div>
                      <span className="micro-pill">Gate {bundle.gate_level}</span>
                      <h3>{bundle.title}</h3>
                    </div>
                    <small>{bundle.source_file}</small>
                  </div>
                  <div className="bundle-content">{bundle.content}</div>
                </article>
              ))}
            </div>
          )}
        </>
      ) : (
        <EmptyState title="Select a skill to inspect" detail="Choose a packet from the library or from a routing result to load its gated runtime context." />
      )}
    </section>
  );
}
