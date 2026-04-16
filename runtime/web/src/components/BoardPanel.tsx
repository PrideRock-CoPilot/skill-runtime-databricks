import { SectionHeading, EmptyState } from "../dashboardUi";
import { STAGES } from "../constants";
import { stageLabel } from "../utils";
import type { ProjectRecord, WorkItemRecord, WorkItemStage } from "../types";

function formatTime(value: string): string {
  if (!value) {
    return "not yet";
  }
  return new Date(value).toLocaleString();
}

interface BoardPanelProps {
  activeProject: ProjectRecord | null;
  completionRate: number;
  newWorkTitle: string;
  newWorkSummary: string;
  newWorkStage: WorkItemStage;
  groupedWorkItems: Array<{ stage: WorkItemStage; items: WorkItemRecord[] }>;
  busy: boolean;
  onNewWorkTitleChange: (value: string) => void;
  onNewWorkSummaryChange: (value: string) => void;
  onNewWorkStageChange: (value: WorkItemStage) => void;
  onCreateWorkItem: () => Promise<void>;
  onShiftWorkItem: (item: WorkItemRecord, direction: -1 | 1) => Promise<void>;
}

export function BoardPanel({
  activeProject,
  completionRate,
  newWorkTitle,
  newWorkSummary,
  newWorkStage,
  groupedWorkItems,
  busy,
  onNewWorkTitleChange,
  onNewWorkSummaryChange,
  onNewWorkStageChange,
  onCreateWorkItem,
  onShiftWorkItem
}: BoardPanelProps) {
  return (
    <section className="panel board-panel">
      <SectionHeading
        kicker="Execution board"
        title={activeProject?.name ?? "No active project"}
        subtitle={activeProject?.summary ?? "This is the operational center of the app. The board will populate once the dashboard API returns an active project."}
      />

      <div className="board-toolbar">
        <span className="pill">Owner: {activeProject?.owner_name ?? "Unassigned"}</span>
        <span className="pill">Stage: {activeProject?.stage ?? "Pending"}</span>
        <span className="pill">Visibility: {activeProject?.visibility ?? "unknown"}</span>
        <span className="pill">Completion: {completionRate}%</span>
      </div>

      <div className="new-work-form">
        <input className="text-input" placeholder="New work item title" value={newWorkTitle} onChange={(event) => onNewWorkTitleChange(event.target.value)} />
        <input className="text-input" placeholder="Summary" value={newWorkSummary} onChange={(event) => onNewWorkSummaryChange(event.target.value)} />
        <select
          className="select-input"
          value={newWorkStage}
          onChange={(event) => onNewWorkStageChange(event.target.value as WorkItemStage)}
          title="New work item stage"
          aria-label="New work item stage"
        >
          {STAGES.map((stage) => (
            <option key={stage} value={stage}>
              {stageLabel(stage)}
            </option>
          ))}
        </select>
        <button className="primary-button" onClick={() => void onCreateWorkItem()} disabled={busy || !activeProject}>
          Add Work Item
        </button>
      </div>

      <div className="board-grid">
        {groupedWorkItems.map((column) => (
          <section key={column.stage} className={`stage-column stage-${column.stage}`}>
            <header>
              <h3>{stageLabel(column.stage)}</h3>
              <span>{column.items.length}</span>
            </header>
            <div className="stage-stack">
              {column.items.length === 0 ? (
                <EmptyState compact title="No items" detail={`Nothing is currently in ${stageLabel(column.stage)}.`} />
              ) : (
                column.items.map((item) => (
                  <article key={item.work_item_id} className="work-card">
                    <div className="work-card-header">
                      <strong>{item.title}</strong>
                      <span className={`priority-badge ${item.priority}`}>{item.priority}</span>
                    </div>
                    <p>{item.summary}</p>
                    <div className="work-meta">
                      <span>{item.owner_display_name}</span>
                      <small>{formatTime(item.updated_at)}</small>
                    </div>
                    <div className="card-actions">
                      <button className="secondary-button" onClick={() => void onShiftWorkItem(item, -1)} disabled={busy || item.stage === "backlog"}>
                        Move left
                      </button>
                      <button className="secondary-button" onClick={() => void onShiftWorkItem(item, 1)} disabled={busy || item.stage === "done"}>
                        Move right
                      </button>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
