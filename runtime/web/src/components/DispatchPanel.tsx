import { QUICK_PROMPTS } from "../constants";
import { EmptyState, SectionHeading } from "../dashboardUi";
import type { Complexity, RouteResponse } from "../types";

interface DispatchPanelProps {
  routeText: string;
  routeComplexity: Complexity | "";
  routeResult: RouteResponse | null;
  selectedSkillId: string;
  busy: boolean;
  onRouteTextChange: (value: string) => void;
  onComplexityChange: (value: Complexity | "") => void;
  onRoute: () => Promise<void>;
  onSelectSkill: (skillId: string, gate: number) => void;
}

export function DispatchPanel({
  routeText,
  routeComplexity,
  routeResult,
  selectedSkillId,
  busy,
  onRouteTextChange,
  onComplexityChange,
  onRoute,
  onSelectSkill
}: DispatchPanelProps) {
  return (
    <section className="panel router-panel">
      <SectionHeading
        kicker="Dispatch"
        title="Step 1: Describe what you want to build"
        subtitle="The orchestrator reads this, picks the best specialist skill, and tells you what happens next."
      />
      <textarea
        value={routeText}
        onChange={(event) => onRouteTextChange(event.target.value)}
        rows={5}
        className="input-area"
        placeholder="Describe the task, user path, or review request you want the router to classify"
        title="Prompt to route"
        aria-label="Prompt to route"
      />
      <div className="inline-controls">
        <select
          value={routeComplexity}
          onChange={(event) => onComplexityChange(event.target.value as Complexity | "")}
          className="select-input"
          title="Complexity override"
          aria-label="Complexity override"
        >
          <option value="">Auto-detect complexity</option>
          <option value="simple">Simple</option>
          <option value="standard">Standard</option>
          <option value="deep">Deep</option>
          <option value="expert">Expert</option>
        </select>
        <button className="primary-button" onClick={() => void onRoute()} disabled={busy}>
          Start Guided Routing
        </button>
      </div>
      <div className="suggestion-row">
        {QUICK_PROMPTS.map((prompt) => (
          <button key={prompt} className="suggestion-chip" onClick={() => onRouteTextChange(prompt)}>
            {prompt}
          </button>
        ))}
      </div>

      {routeResult ? (
        <div className="route-result">
          <div className="route-summary">
            <span className="pill">Complexity: {routeResult.complexity}</span>
            <span className="pill">Depth level: {routeResult.recommended_gate}</span>
          </div>
          <div className="match-list">
            {routeResult.matches.map((match) => (
              <button
                key={match.skill_id}
                className={`match-card ${selectedSkillId === match.skill_id ? "selected" : ""}`}
                onClick={() => onSelectSkill(match.skill_id, routeResult.recommended_gate)}
              >
                <strong>{match.display_name}</strong>
                <span>{match.description}</span>
                <small>score {match.search_score.toFixed(1)}</small>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState compact title="No routing result yet" detail="Route a prompt to see recommended skills, complexity, and the best gate to load." />
      )}
    </section>
  );
}