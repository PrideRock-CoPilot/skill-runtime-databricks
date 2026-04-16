import { useEffect, useMemo, useState } from "react";

import { EmptyState, SectionHeading } from "../dashboardUi";
import type { RuntimeAppModel } from "../hooks/useRuntimeApp";
import type { UserPreferences } from "../types";

interface PreferencesWorkspaceProps {
  runtime: RuntimeAppModel;
  preferences: UserPreferences;
  onPreferenceChange: <Key extends keyof UserPreferences>(key: Key, value: UserPreferences[Key]) => void;
}

function formatBytes(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(timestamp: string) {
  return timestamp ? new Date(timestamp).toLocaleString() : "just now";
}

export function PreferencesWorkspace({ runtime, preferences, onPreferenceChange }: PreferencesWorkspaceProps) {
  const [uploadName, setUploadName] = useState("");
  const [uploadCategory, setUploadCategory] = useState("sttm");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [documentName, setDocumentName] = useState("");
  const [documentDescription, setDocumentDescription] = useState("");

  const selectedTemplate = useMemo(
    () => runtime.templateLibrary.find((template) => template.template_id === selectedTemplateId) ?? null,
    [runtime.templateLibrary, selectedTemplateId]
  );

  useEffect(() => {
    if (runtime.templateLibrary.length === 0) {
      setSelectedTemplateId("");
      return;
    }
    if (!selectedTemplateId || !runtime.templateLibrary.some((template) => template.template_id === selectedTemplateId)) {
      const firstTemplate = runtime.templateLibrary[0];
      setSelectedTemplateId(firstTemplate.template_id);
      setDocumentName(`${firstTemplate.name} working copy`);
    }
  }, [runtime.templateLibrary, selectedTemplateId]);

  useEffect(() => {
    if (!selectedTemplate) {
      return;
    }
    if (!documentName.trim()) {
      setDocumentName(`${selectedTemplate.name} working copy`);
    }
  }, [selectedTemplate, documentName]);

  async function handleUploadSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!uploadFile) {
      return;
    }
    await runtime.handleUploadTemplate(uploadFile, uploadName.trim(), uploadCategory.trim(), uploadDescription.trim());
    setUploadName("");
    setUploadDescription("");
    setUploadFile(null);
    const input = event.currentTarget.querySelector<HTMLInputElement>('input[type="file"]');
    if (input) {
      input.value = "";
    }
  }

  async function handleCreateDocumentSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTemplateId || !documentName.trim()) {
      return;
    }
    await runtime.handleCreateDocumentFromTemplate(selectedTemplateId, documentName.trim(), documentDescription.trim());
    setDocumentDescription("");
  }

  return (
    <div className="preferences-grid">
      <section className="panel preferences-panel">
        <SectionHeading
          kicker="Operator"
          title="User preferences"
          subtitle="Separate the operator setup from the execution board so people can tune the shell without digging through workflow surfaces."
        />
        <div className="settings-grid">
          <label className="settings-field">
            <span>Operator name</span>
            <input className="text-input" value={preferences.operatorName} onChange={(event) => onPreferenceChange("operatorName", event.target.value)} />
          </label>

          <label className="settings-field">
            <span>User ID</span>
            <input className="text-input" value={preferences.userId} onChange={(event) => onPreferenceChange("userId", event.target.value)} />
          </label>

          <label className="settings-field">
            <span>Client type</span>
            <select className="select-input" value={preferences.clientType} onChange={(event) => onPreferenceChange("clientType", event.target.value as UserPreferences["clientType"])}>
              <option value="web">Web app</option>
              <option value="genie-code">Genie Code</option>
              <option value="ide">IDE</option>
              <option value="api">API</option>
            </select>
          </label>

          <label className="settings-field">
            <span>Workspace mode</span>
            <select className="select-input" value={preferences.workspaceMode} onChange={(event) => onPreferenceChange("workspaceMode", event.target.value as UserPreferences["workspaceMode"])}>
              <option value="focus">Focus</option>
              <option value="loud">Loud</option>
            </select>
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={preferences.showRetroSkills} onChange={(event) => onPreferenceChange("showRetroSkills", event.target.checked)} />
            <div>
              <strong>Retro skills page</strong>
              <p>Keep the MySpace-inspired roster treatment active in the skills area.</p>
            </div>
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={preferences.autoParkAfterFeedback} onChange={(event) => onPreferenceChange("autoParkAfterFeedback", event.target.checked)} />
            <div>
              <strong>Auto-park after feedback</strong>
              <p>After rating a packet, automatically send it to the bench for quick reuse.</p>
            </div>
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={preferences.compactBoard} onChange={(event) => onPreferenceChange("compactBoard", event.target.checked)} />
            <div>
              <strong>Compact board density</strong>
              <p>Reduce vertical breathing room when you want a tighter operator view.</p>
            </div>
          </label>
        </div>
      </section>

      <section className="panel preferences-panel">
        <SectionHeading
          kicker="Template Library"
          title="Upload reusable source files"
          subtitle="Keep approved STTM, branding, and delivery templates with the active project so generated working copies start from the right structure."
          meta={
            runtime.activeProject ? (
              <span className="count-chip">{runtime.activeProject.name}</span>
            ) : (
              <span className="count-chip">No active project</span>
            )
          }
        />

        {!runtime.activeProject ? (
          <EmptyState title="No project selected" detail="Create a project first so templates have a home and generated documents can be tracked." />
        ) : (
          <form className="template-form" onSubmit={(event) => void handleUploadSubmit(event)}>
            <div className="template-form-grid">
              <label className="settings-field">
                <span>Template name</span>
                <input
                  className="text-input"
                  placeholder="STTM master workbook"
                  value={uploadName}
                  onChange={(event) => setUploadName(event.target.value)}
                />
              </label>

              <label className="settings-field">
                <span>Category</span>
                <input
                  className="text-input"
                  placeholder="sttm, branding, checklist"
                  value={uploadCategory}
                  onChange={(event) => setUploadCategory(event.target.value)}
                />
              </label>
            </div>

            <label className="settings-field">
              <span>Description</span>
              <textarea
                placeholder="What this template is for and when operators should use it."
                value={uploadDescription}
                onChange={(event) => setUploadDescription(event.target.value)}
              />
            </label>

            <label className="settings-field">
              <span>File</span>
              <input
                className="file-input"
                type="file"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              />
            </label>

            <div className="template-form-actions">
              <button className="primary-button" type="submit" disabled={runtime.busy || !uploadFile}>
                Upload template
              </button>
              <span className="muted-label">
                Stored files stay attached to this project and can be reused to create downloadable working copies.
              </span>
            </div>
          </form>
        )}

        <div className="template-library-list">
          {runtime.isTemplateLibraryLoading ? (
            <EmptyState compact title="Loading template library" detail="Reading project templates and generated documents." />
          ) : runtime.templateLibrary.length === 0 ? (
            <EmptyState compact title="No templates uploaded yet" detail="Upload your STTM, branding, or workbook templates here and the library will keep them ready." />
          ) : (
            runtime.templateLibrary.map((template) => (
              <article key={template.template_id} className="template-card">
                <div className="template-card-header">
                  <div>
                    <strong>{template.name}</strong>
                    <p>{template.description || "Reusable project template"}</p>
                  </div>
                  <div className="template-card-meta">
                    <span className="pill">{template.category}</span>
                    <span className="pill">{formatBytes(template.size_bytes)}</span>
                  </div>
                </div>
                <div className="template-card-footer">
                  <div className="template-card-file">
                    <span>{template.original_file_name}</span>
                    <small>Updated {formatDate(template.updated_at)}</small>
                  </div>
                  <div className="template-card-actions">
                    <a className="secondary-button button-link" href={runtime.getTemplateDownloadHref(template.template_id)}>
                      Download template
                    </a>
                    <button className="secondary-button" type="button" onClick={() => {
                      setSelectedTemplateId(template.template_id);
                      setDocumentName(`${template.name} working copy`);
                    }}>
                      Use for new doc
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="panel preferences-panel secondary">
        <SectionHeading
          kicker="Generated Docs"
          title="Create a downloadable working copy"
          subtitle="Pick a stored template, create a project-specific copy, and hand the file back to the end user as a real download."
        />

        {!runtime.activeProject ? (
          <EmptyState title="No project selected" detail="Generated documents are created inside a project so the source template and downloads stay traceable." />
        ) : (
          <form className="template-form" onSubmit={(event) => void handleCreateDocumentSubmit(event)}>
            <div className="template-form-grid">
              <label className="settings-field">
                <span>Source template</span>
                <select
                  className="select-input"
                  value={selectedTemplateId}
                  onChange={(event) => {
                    const nextId = event.target.value;
                    setSelectedTemplateId(nextId);
                    const nextTemplate = runtime.templateLibrary.find((template) => template.template_id === nextId);
                    if (nextTemplate) {
                      setDocumentName(`${nextTemplate.name} working copy`);
                    }
                  }}
                  disabled={runtime.templateLibrary.length === 0}
                >
                  {runtime.templateLibrary.length === 0 ? <option value="">No templates available</option> : null}
                  {runtime.templateLibrary.map((template) => (
                    <option key={template.template_id} value={template.template_id}>
                      {template.name} ({template.category})
                    </option>
                  ))}
                </select>
              </label>

              <label className="settings-field">
                <span>Generated file name</span>
                <input
                  className="text-input"
                  placeholder="Petrovs Blooms STTM - working copy"
                  value={documentName}
                  onChange={(event) => setDocumentName(event.target.value)}
                />
              </label>
            </div>

            <label className="settings-field">
              <span>Notes</span>
              <textarea
                placeholder="Optional note for what this generated copy is for."
                value={documentDescription}
                onChange={(event) => setDocumentDescription(event.target.value)}
              />
            </label>

            <div className="template-form-actions">
              <button className="primary-button" type="submit" disabled={runtime.busy || !selectedTemplateId || !documentName.trim()}>
                Create downloadable copy
              </button>
              {selectedTemplate ? (
                <span className="muted-label">
                  New copies inherit the original {selectedTemplate.original_file_name} structure so Excel and brand files follow the approved template.
                </span>
              ) : null}
            </div>
          </form>
        )}

        <div className="template-library-list">
          {runtime.isTemplateLibraryLoading ? (
            <EmptyState compact title="Loading generated documents" detail="Reading the latest working copies for this project." />
          ) : runtime.generatedDocuments.length === 0 ? (
            <EmptyState compact title="No generated documents yet" detail="Create a working copy from any stored template and it will appear here for download." />
          ) : (
            runtime.generatedDocuments.map((document) => (
              <article key={document.document_id} className="template-card generated">
                <div className="template-card-header">
                  <div>
                    <strong>{document.name}</strong>
                    <p>{document.description || `Created from ${document.source_template_name}`}</p>
                  </div>
                  <div className="template-card-meta">
                    <span className="pill">from {document.source_template_name}</span>
                    <span className="pill">{formatBytes(document.size_bytes)}</span>
                  </div>
                </div>
                <div className="template-card-footer">
                  <div className="template-card-file">
                    <span>{document.file_name}</span>
                    <small>Generated {formatDate(document.created_at)}</small>
                  </div>
                  <div className="template-card-actions">
                    <a className="primary-button button-link" href={runtime.getGeneratedDocumentDownloadHref(document.document_id)}>
                      Download document
                    </a>
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
