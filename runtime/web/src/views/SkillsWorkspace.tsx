import { BriefingPanel } from "../components/BriefingPanel";
import { SkillRosterPanel } from "../components/SkillRosterPanel";
import { WorkerAuditPanel } from "../components/WorkerAuditPanel";
import type { RuntimeAppModel } from "../hooks/useRuntimeApp";

interface SkillsWorkspaceProps {
  runtime: RuntimeAppModel;
  showRetroSkills: boolean;
  favoriteSkillIds: string[];
  downvotedSkillIds: string[];
  onToggleFavorite: (skillId: string) => void;
  onToggleDownvote: (skillId: string) => void;
  onFeedback: (rating: "correct" | "wrong") => Promise<void>;
}

export function SkillsWorkspace({ runtime, showRetroSkills, favoriteSkillIds, downvotedSkillIds, onToggleFavorite, onToggleDownvote, onFeedback }: SkillsWorkspaceProps) {
  const selectedSkill = runtime.skills.find((skill) => skill.skill_id === runtime.selectedSkillId) ?? null;

  return (
    <div className={`skills-workspace ${showRetroSkills ? "retro-on" : "retro-off"}`}>
      <section className="panel skills-intro-panel">
        <div className="skills-intro-copy">
          <p className="panel-kicker">MySkills</p>
          <h2>Your crew. Your wall. Your rules.</h2>
          <p>
            Scan the roster, star your favorites, read the packet, and deploy. Every specialist has a face, a file, and a job.
          </p>
        </div>
        <div className="skills-intro-stats">
          <span className="pill">Active: {selectedSkill?.display_name ?? "—"}</span>
          <span className="pill">{runtime.skills.length} loaded</span>
          <span className="pill">{runtime.parkingLot.length} benched</span>
        </div>
      </section>

      <div className="skills-page-grid">
        <SkillRosterPanel
          skills={runtime.skills}
          skillQuery={runtime.skillQuery}
          selectedSkillId={runtime.selectedSkillId}
          isSkillsLoading={runtime.isSkillsLoading}
          selectedSkill={selectedSkill}
          showRetroSkills={showRetroSkills}
          favoriteSkillIds={favoriteSkillIds}
          downvotedSkillIds={downvotedSkillIds}
          onSkillQueryChange={runtime.setSkillQuery}
          onSelectSkill={runtime.setSelectedSkillId}
          onToggleFavorite={onToggleFavorite}
          onToggleDownvote={onToggleDownvote}
        />

        <BriefingPanel
          skillDetail={runtime.skillDetail}
          selectedGate={runtime.selectedGate}
          isDetailLoading={runtime.isDetailLoading}
          busy={runtime.busy}
          onSelectGate={runtime.setSelectedGate}
          onActivate={runtime.handleActivateSelectedSkill}
          onPark={runtime.handleParkSelectedSkill}
          onScoreAlignment={runtime.handleScoreAlignment}
          onFeedback={onFeedback}
        />
      </div>

      <WorkerAuditPanel
        activeSkill={runtime.activeSkill}
        latestAlignment={runtime.latestAlignment}
        recentEvents={runtime.recentEvents}
        sessionStory={runtime.sessionStory}
      />
    </div>
  );
}
