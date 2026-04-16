import { BoardPanel } from "../components/BoardPanel";
import type { RuntimeAppModel } from "../hooks/useRuntimeApp";

interface BoardWorkspaceProps {
  runtime: RuntimeAppModel;
  onFeedback: (rating: "correct" | "wrong") => Promise<void>;
}

export function BoardWorkspace({ runtime }: BoardWorkspaceProps) {
  return (
    <div className="board-workspace">
      <BoardPanel
        activeProject={runtime.activeProject}
        completionRate={runtime.completionRate}
        newWorkTitle={runtime.newWorkTitle}
        newWorkSummary={runtime.newWorkSummary}
        newWorkStage={runtime.newWorkStage}
        groupedWorkItems={runtime.groupedWorkItems}
        busy={runtime.busy}
        onNewWorkTitleChange={runtime.setNewWorkTitle}
        onNewWorkSummaryChange={runtime.setNewWorkSummary}
        onNewWorkStageChange={runtime.setNewWorkStage}
        onCreateWorkItem={runtime.handleCreateWorkItem}
        onShiftWorkItem={runtime.shiftWorkItem}
      />
    </div>
  );
}
