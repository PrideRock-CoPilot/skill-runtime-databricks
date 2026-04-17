import { useEffect, useState } from "react";

import { EmptyState, SectionHeading } from "../dashboardUi";
import type { RuntimeAppModel } from "../hooks/useRuntimeApp";
import type { MemoryScope } from "../types";

interface KnowledgeWorkspaceProps {
  runtime: RuntimeAppModel;
}

const KNOWLEDGE_CATEGORIES = ["all", "requirement", "decision", "constraint", "preference", "lesson", "convention", "note"];

export function KnowledgeWorkspace({ runtime }: KnowledgeWorkspaceProps) {
  const [draftScope, setDraftScope] = useState<MemoryScope>(runtime.activeProject ? "project" : "user");
  const [draftCategory, setDraftCategory] = useState("note");
  const [draftSubject, setDraftSubject] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [draftTags, setDraftTags] = useState("");
  const [draftPinned, setDraftPinned] = useState(false);

  useEffect(() => {
    if (!runtime.activeProject && draftScope === "project") {
      setDraftScope("user");
    }
  }, [draftScope, runtime.activeProject]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draftSubject.trim() || !draftContent.trim()) {
      return;
    }
    await runtime.handleCreateKnowledgeEntry({
      scope: draftScope,
      subject: draftSubject.trim(),
      content: draftContent.trim(),
      category: draftCategory,
      tags: draftTags,
      pinned: draftPinned,
      projectId: runtime.activeProject?.project_id
    });
    setDraftSubject("");
    setDraftContent("");
    setDraftTags("");
    setDraftPinned(false);
  }

  return (
    <div className="knowledge-workspace">
      <section className="panel knowledge-intro-panel">
        <div className="knowledge-intro-copy">
          <p className="panel-kicker">Knowledge Base</p>
          <h2>Capture the facts your runtime should stop relearning.</h2>
          <p>
            Store reusable requirements, decisions, constraints, and project context. The MCP tools already write to this store; this workspace makes it visible and editable.
          </p>
        </div>
      </section>

      <div className="knowledge-grid">
        <div className="knowledge-rail">
          <section className="panel">
            <SectionHeading
              kicker="Browse"
              title="Find stored context"
              subtitle="Search across your accessible memory scopes, or narrow to the current project."
            />
            <div className="knowledge-form">
              <div className="knowledge-filter-row">
                <input
                  className="text-input"
                  placeholder="Search subject, tags, or content"
                  value={runtime.knowledgeQuery}
                  onChange={(event) => runtime.setKnowledgeQuery(event.target.value)}
                />
                <select
                  className="select-input"
                  aria-label="Knowledge scope filter"
                  value={runtime.knowledgeScope}
                  onChange={(event) => runtime.setKnowledgeScope(event.target.value as MemoryScope | "all")}
                >
                  <option value="all">All scopes</option>
                  <option value="project">Project</option>
                  <option value="user">User</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <select
                  className="select-input"
                  aria-label="Knowledge category filter"
                  value={runtime.knowledgeCategory}
                  onChange={(event) => runtime.setKnowledgeCategory(event.target.value)}
                >
                  {KNOWLEDGE_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category === "all" ? "All categories" : category}
                    </option>
                  ))}
                </select>
              </div>
              <div className="knowledge-note">
                Active project: {runtime.activeProject?.name ?? "None selected"}
              </div>
            </div>
          </section>

          <section className="panel">
            <SectionHeading
              kicker="Create"
              title="Add knowledge"
              subtitle="Use project scope for delivery facts, user scope for operator preferences, and enterprise scope for shared rules."
            />
            <form className="knowledge-form" onSubmit={(event) => void handleSubmit(event)}>
              <div className="knowledge-form-grid">
                <select
                  className="select-input"
                  aria-label="New knowledge entry scope"
                  value={draftScope}
                  onChange={(event) => setDraftScope(event.target.value as MemoryScope)}
                >
                  <option value="project">Project</option>
                  <option value="user">User</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <select
                  className="select-input"
                  aria-label="New knowledge entry category"
                  value={draftCategory}
                  onChange={(event) => setDraftCategory(event.target.value)}
                >
                  {KNOWLEDGE_CATEGORIES.filter((category) => category !== "all").map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>
              <input
                className="text-input"
                placeholder="Subject"
                value={draftSubject}
                onChange={(event) => setDraftSubject(event.target.value)}
              />
              <textarea
                placeholder="What should the runtime remember?"
                value={draftContent}
                onChange={(event) => setDraftContent(event.target.value)}
              />
              <input
                className="text-input"
                placeholder="Tags, comma separated"
                value={draftTags}
                onChange={(event) => setDraftTags(event.target.value)}
              />
              <label className="toggle-row">
                <input type="checkbox" checked={draftPinned} onChange={(event) => setDraftPinned(event.target.checked)} />
                <span>Pin this entry near the top</span>
              </label>
              <button
                className="primary-button"
                type="submit"
                disabled={runtime.busy || !draftSubject.trim() || !draftContent.trim() || (draftScope === "project" && !runtime.activeProject)}
              >
                Store knowledge
              </button>
            </form>
          </section>
        </div>

        <section className="panel knowledge-stack">
          <SectionHeading
            kicker="Results"
            title="Knowledge entries"
            subtitle="Pinned and higher-signal entries float to the top. Search terms switch the backend into relevance mode."
            meta={<span className="count-chip">{runtime.knowledgeEntries.length} entries</span>}
          />
          {runtime.isKnowledgeLoading ? (
            <EmptyState compact title="Loading knowledge base" detail="Reading the memory store for visible project, user, and enterprise entries." />
          ) : runtime.knowledgeEntries.length === 0 ? (
            <EmptyState compact title="No knowledge stored yet" detail="Add a requirement, decision, or constraint and it will appear here for future routing and recall." />
          ) : (
            runtime.knowledgeEntries.map((entry) => (
              <article key={entry.memory_id} className={`knowledge-card ${entry.pinned ? "pinned" : ""}`.trim()}>
                <div className="knowledge-card-header">
                  <div>
                    <h3>{entry.subject}</h3>
                    <p>Updated {new Date(entry.updated_at).toLocaleString()}</p>
                  </div>
                  <div className="knowledge-card-actions">
                    <button className="secondary-button" type="button" onClick={() => void runtime.handleToggleKnowledgePin(entry)}>
                      {entry.pinned ? "Unpin" : "Pin"}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => void runtime.handleArchiveKnowledgeEntry(entry.memory_id)}>
                      Archive
                    </button>
                  </div>
                </div>
                <div className="knowledge-badges">
                  <span className="pill">{entry.scope}</span>
                  <span className="pill">{entry.category}</span>
                  <span className="pill">{entry.status || "confirmed"}</span>
                  {entry.relevance_score ? <span className="pill">score {entry.relevance_score.toFixed(1)}</span> : null}
                </div>
                <p className="knowledge-content">{entry.content}</p>
                {entry.tags ? (
                  <div className="knowledge-tags">
                    {entry.tags.split(",").filter(Boolean).map((tag) => (
                      <span key={`${entry.memory_id}-${tag}`} className="micro-pill">
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : null}
                <div className="knowledge-card-footer">
                  <span className="knowledge-note">accessed {entry.access_count} times</span>
                  {entry.project_id ? <span className="knowledge-note">project: {entry.project_id}</span> : null}
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </div>
  );
}