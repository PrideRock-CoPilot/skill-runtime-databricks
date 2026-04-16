import { useEffect, useState } from "react";

import type { AppTab, UserPreferences } from "../types";

const DEFAULT_PREFERENCES: UserPreferences = {
  operatorName: "Shift Lead",
  userId: "local.user@company.test",
  clientType: "web",
  workspaceMode: "loud",
  showRetroSkills: true,
  autoParkAfterFeedback: false,
  compactBoard: false,
  favoriteSkillIds: [],
  downvotedSkillIds: []
};

function readStoredPreferences(): UserPreferences {
  const raw = window.localStorage.getItem("skill-runtime-preferences");
  if (!raw) {
    return DEFAULT_PREFERENCES;
  }
  try {
    return { ...DEFAULT_PREFERENCES, ...(JSON.parse(raw) as Partial<UserPreferences>) };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function readStoredTab(): AppTab {
  const raw = window.localStorage.getItem("skill-runtime-active-tab");
  if (raw === "board" || raw === "skills" || raw === "preferences") {
    return raw;
  }
  return "board";
}

export function useUserPreferences() {
  const [activeTab, setActiveTab] = useState<AppTab>(readStoredTab);
  const [preferences, setPreferences] = useState<UserPreferences>(readStoredPreferences);

  useEffect(() => {
    window.localStorage.setItem("skill-runtime-active-tab", activeTab);
  }, [activeTab]);

  useEffect(() => {
    window.localStorage.setItem("skill-runtime-preferences", JSON.stringify(preferences));
  }, [preferences]);

  function updatePreference<Key extends keyof UserPreferences>(key: Key, value: UserPreferences[Key]) {
    setPreferences((current) => ({ ...current, [key]: value }));
  }

  function toggleFavorite(skillId: string) {
    setPreferences((current) => {
      const favs = current.favoriteSkillIds;
      const next = favs.includes(skillId) ? favs.filter((id) => id !== skillId) : [...favs, skillId];
      return { ...current, favoriteSkillIds: next };
    });
  }

  function toggleDownvote(skillId: string) {
    setPreferences((current) => {
      const dvs = current.downvotedSkillIds;
      const next = dvs.includes(skillId) ? dvs.filter((id) => id !== skillId) : [...dvs, skillId];
      return { ...current, downvotedSkillIds: next };
    });
  }

  return {
    activeTab,
    setActiveTab,
    preferences,
    updatePreference,
    toggleFavorite,
    toggleDownvote
  };
}
