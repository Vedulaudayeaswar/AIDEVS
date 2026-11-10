import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

function CodeView({ projectId, selectedId, version }) {
  const [files, setFiles] = useState(null);
  const [current, setCurrent] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    setError("");
    api.get(`/api/projects/${projectId}/export/files`)
      .then((d) => { if (alive) setFiles(d.files); })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [projectId, version]);
  const sourcemap = useMemo(() => {
    try { return files ? JSON.parse(files["aidevs.sourcemap.json"]) : {}; } catch { return {}; }
  }, [files]);
  // Jump to the component file that renders the selected element.
  useEffect(() => {
    if (selectedId && sourcemap[selectedId]) setCurrent(sourcemap[selectedId].file);
  }, [selectedId, sourcemap]);
  if (error) return <div className="aid-alert aid-alert-error">{error}</div>;
  if (!files) return <div className="aid-spinner" />;
  const paths = Object.keys(files);
  const file = current && files[current] ? current : paths.find((p) => p.endsWith("App.jsx")) || paths[0];
  const mapped = selectedId && sourcemap[selectedId];
  return (
    <div className="st-code">
      <ul className="st-code-tree">
        {paths.map((p) => <li key={p}><button type="button" className={p === file ? "on" : ""} onClick={() => setCurrent(p)}>{p}</button></li>)}
      </ul>
      <div className="st-code-body">
        <div className="st-code-head">{file}{mapped && mapped.file === file && <span> · selected element → <code>.{mapped.className}</code></span>}
          <span className="st-note"> (read-only, generated from the visual design)</span></div>
        <pre><code>{files[file]}</code></pre>
      </div>
    </div>
  );
}

export default function BottomPanel({ projectId, consoleLines, onClearConsole, checks, onRunChecks, checking, runs,
  onSelectIssue, selectedId, codeVersion, tab, setTab, onAutoRepair, repairBusy }) {
  const counts = checks ? checks.summary : null;
  return (
    <div className="st-bottom">
      <div className="st-tabs" role="tablist">
        {[["console", `Console${consoleLines.length ? ` (${consoleLines.length})` : ""}`],
          ["checks", `Tests & checks${counts ? ` (${counts.error}E/${counts.warning}W)` : ""}`],
          ["activity", "Agent activity"], ["code", "Code"]].map(([key, label]) => (
          <button key={key} role="tab" aria-selected={tab === key} className={tab === key ? "on" : ""} onClick={() => setTab(tab === key ? null : key)}>{label}</button>
        ))}
      </div>
      {tab && (
        <div className="st-bottom-body" role="tabpanel">
          {tab === "console" && (
            <div>
              <button className="aid-btn aid-btn-sm" onClick={onClearConsole}>Clear</button>
              {consoleLines.length === 0 && <p className="st-note">Logs from the canvas and the preview API appear here.</p>}
              {consoleLines.map((l, i) => <div key={i} className={`st-log ${l.level}`}><span>{l.time}</span> {l.message}</div>)}
            </div>
          )}
          {tab === "checks" && (
            <div>
              <div className="st-row">
                <button className="aid-btn aid-btn-sm aid-btn-primary" onClick={onRunChecks} disabled={checking}>{checking ? "Running…" : "Run checks"}</button>
                {checks && <span className={`aid-badge ${checks.passed ? "ok" : "err"}`}>{checks.passed ? "No blocking errors" : "Errors found"}</span>}
                {checks && !checks.passed && (
                  <button className="aid-btn aid-btn-sm" onClick={onAutoRepair} disabled={repairBusy}
                    title="Fixes exact problems automatically, then asks the AI for targeted fixes. A version is saved first.">
                    Auto-fix errors</button>
                )}
                <span className="st-note">API contracts, links, accessibility, SEO, responsive layout, permissions, backend compile.</span>
              </div>
              {checks && checks.issues.map((i, k) => (
                <button key={k} type="button" className={`st-issue ${i.severity}`} onClick={() => onSelectIssue(i)}>
                  <span className={`aid-badge ${i.severity === "error" ? "err" : i.severity === "warning" ? "warn" : ""}`}>{i.severity}</span>
                  <span className="st-issue-cat">{i.category}</span> {i.message} {i.route && <code>{i.route}</code>}
                </button>
              ))}
            </div>
          )}
          {tab === "activity" && (
            <div>
              {runs.length === 0 && <p className="st-note">No agent runs yet.</p>}
              {runs.map((r) => (
                <details key={r.id} className="st-run">
                  <summary><span className={`aid-badge ${r.status === "succeeded" ? "ok" : r.status === "failed" ? "err" : "run"}`}>{r.status}</span>
                    {" "}<strong>{r.kind}</strong> · {r.message} · {new Date(r.createdAt).toLocaleTimeString()}</summary>
                  {r.steps.map((s, i) => <div key={i} className={`st-log ${s.level}`}><span>{new Date(s.at).toLocaleTimeString()}</span> {s.message}</div>)}
                </details>
              ))}
            </div>
          )}
          {tab === "code" && <CodeView projectId={projectId} selectedId={selectedId} version={codeVersion} />}
        </div>
      )}
    </div>
  );
}
