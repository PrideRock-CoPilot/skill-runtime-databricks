import { APP_TABS } from "../constants";
import type { AppTab } from "../types";

interface AppTabsProps {
  activeTab: AppTab;
  onChange: (tab: AppTab) => void;
}

export function AppTabs({ activeTab, onChange }: AppTabsProps) {
  return (
    <nav className="app-tabs" aria-label="Primary workspace tabs">
      {APP_TABS.map((tab) => (
        <button
          key={tab.id}
          className={`app-tab ${activeTab === tab.id ? "active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          <strong>{tab.label}</strong>
          <span>{tab.detail}</span>
        </button>
      ))}
    </nav>
  );
}