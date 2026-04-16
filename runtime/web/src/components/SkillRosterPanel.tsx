import { EmptyState, SectionHeading } from "../dashboardUi";
import type { SkillSummary } from "../types";

const SKILL_AVATARS: Record<string, string> = {
  architect: "🏗️",
  builder: "🔨",
  reviewer: "👁️",
  qa: "✅",
  planner: "📋",
  storyteller: "📖",
  documentation: "📝",
  analyst: "📊",
  governance: "⚖️",
  release: "🚀",
  ops: "🔧",
  data: "💾",
  talent: "🎭",
};

function getSkillAvatar(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, emoji] of Object.entries(SKILL_AVATARS)) {
    if (lower.includes(key)) return emoji;
  }
  return "⚡";
}

interface SkillRosterPanelProps {
  skills: SkillSummary[];
  skillQuery: string;
  selectedSkillId: string;
  isSkillsLoading: boolean;
  selectedSkill: SkillSummary | null;
  showRetroSkills: boolean;
  favoriteSkillIds: string[];
  downvotedSkillIds: string[];
  onSkillQueryChange: (value: string) => void;
  onSelectSkill: (skillId: string) => void;
  onToggleFavorite: (skillId: string) => void;
  onToggleDownvote: (skillId: string) => void;
}

export function SkillRosterPanel({
  skills,
  skillQuery,
  selectedSkillId,
  isSkillsLoading,
  selectedSkill,
  favoriteSkillIds,
  downvotedSkillIds,
  onSkillQueryChange,
  onSelectSkill,
  onToggleFavorite,
  onToggleDownvote
}: SkillRosterPanelProps) {
  const favoriteSkills = skills.filter((s) => favoriteSkillIds.includes(s.skill_id));
  const nonFavoriteSkills = skills.filter((s) => !favoriteSkillIds.includes(s.skill_id));

  return (
    <aside className="skill-roster-sidebar" aria-label="Skill roster sidebar">
      <div className="sidebar-header">
        <p className="sidebar-kicker">MySkills</p>
        <h3>Your Crew</h3>
        <span className="count-chip">{isSkillsLoading ? "Loading..." : `${skills.length} loaded`}</span>
      </div>

      <input
        className="text-input skill-search-input"
        value={skillQuery}
        onChange={(event) => onSkillQueryChange(event.target.value)}
        placeholder="Search skills..."
      />

      <div className="sidebar-skill-list">
        {isSkillsLoading ? (
          <EmptyState compact title="Loading skills" detail="Reading the compiled skill index." />
        ) : skills.length === 0 ? (
          <EmptyState compact title="No matches" detail="Try a broader search term or recompile." />
        ) : (
          <>
            {/* Favorites section at top */}
            {favoriteSkills.length > 0 && (
              <div className="sidebar-section">
                <div className="sidebar-section-header">⭐ Pinned</div>
                {favoriteSkills.map((skill) => {
                  const isDown = downvotedSkillIds.includes(skill.skill_id);
                  return (
                    <div key={skill.skill_id} className={`selector-row ${selectedSkillId === skill.skill_id ? "selected" : ""}`}>
                      <button className="selector-button" onClick={() => onSelectSkill(skill.skill_id)}>
                        <span className="skill-avatar">{getSkillAvatar(skill.display_name)}</span>
                        <strong>{skill.display_name}</strong>
                      </button>
                      <div className="selector-actions">
                        <button
                          className={`icon-button active`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleFavorite(skill.skill_id);
                          }}
                          title="Remove from favorites"
                          aria-label="Remove from favorites"
                        >
                          ★
                        </button>
                        <button
                          className={`icon-button ${true ? "upvoted" : ""}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleFavorite(skill.skill_id);
                          }}
                          title="Quick upvote"
                          aria-label="Quick upvote"
                        >
                          👍
                        </button>
                        <button
                          className={`icon-button ${isDown ? "downvoted" : ""}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleDownvote(skill.skill_id);
                          }}
                          title={isDown ? "Remove downvote" : "Downvote this skill"}
                          aria-label={isDown ? "Remove downvote" : "Downvote this skill"}
                        >
                          👎
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* All skills section */}
            <div className="sidebar-section">
              {favoriteSkills.length > 0 && <div className="sidebar-section-header">All Skills</div>}
              {nonFavoriteSkills.map((skill) => {
                const isDown = downvotedSkillIds.includes(skill.skill_id);
                return (
                  <div key={skill.skill_id} className={`selector-row ${selectedSkillId === skill.skill_id ? "selected" : ""}`}>
                    <button className="selector-button" onClick={() => onSelectSkill(skill.skill_id)}>
                      <span className="skill-avatar">{getSkillAvatar(skill.display_name)}</span>
                      <strong>{skill.display_name}</strong>
                    </button>
                    <div className="selector-actions">
                      <button
                        className={`icon-button`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleFavorite(skill.skill_id);
                        }}
                        title="Add to favorites"
                        aria-label="Add to favorites"
                      >
                        ☆
                      </button>
                      <button
                        className={`icon-button`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleFavorite(skill.skill_id);
                        }}
                        title="Quick upvote"
                        aria-label="Quick upvote"
                      >
                        👍
                      </button>
                      <button
                        className={`icon-button ${isDown ? "downvoted" : ""}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleDownvote(skill.skill_id);
                        }}
                        title={isDown ? "Remove downvote" : "Downvote this skill"}
                        aria-label={isDown ? "Remove downvote" : "Downvote this skill"}
                      >
                        👎
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}