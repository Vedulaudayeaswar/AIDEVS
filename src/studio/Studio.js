import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, apiFetch } from "../lib/api";
import Canvas, { DEVICES } from "./Canvas";
import LayersPanel from "./LayersPanel";
import Inspector from "./Inspector";
import AssistantPanel from "./AssistantPanel";
import BottomPanel from "./BottomPanel";
import { AddPanel, AssetsPanel, DataPanel, DesignPanel, PagesPanel, VersionsPanel, absAsset } from "./Panels";
import useHistory from "./useHistory";
import {
  CONTAINER_TYPES, duplicateNode, findNode, groupNode, insertNode, moveNode, parentOf, pathTo, removeNode,
  replaceNode, ungroupNode, updateNode, updateProps, updateStyles,
} from "./treeOps";
import "./Studio.css";

// Local safety net for unsaved edits (per page). Cleared once the server confirms a save.
const draftKey = (pageId) => `aidevs_draft_${pageId}`;
function readDraft(pageId) {
  try { const raw = localStorage.getItem(draftKey(pageId)); return raw ? JSON.parse(raw) : null; } catch { return null; }
}
function writeDraft(pageId, base, tree) {
  if (!pageId) return;
  try { localStorage.setItem(draftKey(pageId), JSON.stringify({ base, tree, at: Date.now() })); } catch { /* quota */ }
}
function clearDraft(pageId) {
  try { localStorage.removeItem(draftKey(pageId)); } catch { /* ignore */ }
}

const LEFT_TABS = [["pages", "Pages"], ["layers", "Layers"], ["add", "Add"], ["design", "Design"],
  ["assets", "Assets"], ["data", "Data & API"], ["versions", "Versions"]];
const ACTIVE = new Set(["queued", "running"]);

export default function Studio() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [pageId, setPageId] = useState(null);
  const history = useHistory(null);
  const tree = history.value;
  const [selectedId, setSelectedId] = useState(null);
  const [hoveredId, setHoveredId] = useState(null);
  const [device, setDevice] = useState("desktop");
  const [zoom, setZoom] = useState("fit");
  const [mode, setMode] = useState("edit");
  const [leftTab, setLeftTab] = useState("layers");
  const [rightTab, setRightTab] = useState("inspect");
  const [bottomTab, setBottomTab] = useState(null);
  const [saveState, setSaveState] = useState("saved");
  const [conflict, setConflict] = useState(false);
  const [toast, setToast] = useState("");
  const [fatal, setFatal] = useState("");
  const [consoleLines, setConsoleLines] = useState([]);
  const [checks, setChecks] = useState(null);
  const [checking, setChecking] = useState(false);
  const [runs, setRuns] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assets, setAssets] = useState([]);
  const [renderKey, setRenderKey] = useState(0);
  const [codeVersion, setCodeVersion] = useState(0);

  const revisionRef = useRef(null);
  const savedTreeRef = useRef(null);
  const saveTimer = useRef(null);
  const savingRef = useRef(Promise.resolve());
  const treeRef = useRef(tree);
  treeRef.current = tree;

  const breakpoint = DEVICES[device].breakpoint;
  const selected = useMemo(() => (tree && selectedId ? findNode(tree, selectedId) : null), [tree, selectedId]);
  const selectedParent = useMemo(() => (tree && selectedId ? parentOf(tree, selectedId) : null), [tree, selectedId]);
  const showError = useCallback((msg) => setToast(String(msg || "Something went wrong")), []);
  const log = useCallback((level, message) => setConsoleLines((lines) => [...lines.slice(-299),
    { level, message, time: new Date().toLocaleTimeString() }]), []);

  // ------------------------------------------------------------ loading
  const loadProject = useCallback(async () => {
    const data = await api.get(`/api/projects/${projectId}`);
    setProject(data.project);
    return data.project;
  }, [projectId]);

  const loadPage = useCallback(async (id) => {
    const data = await api.get(`/api/projects/${projectId}/pages/${id}`);
    revisionRef.current = data.page.revision;
    savedTreeRef.current = data.page.tree;
    history.reset(data.page.tree);
    setSaveState("saved");
    setConflict(false);
    // Unsaved edits from a previous session (tab closed, server restarted while asleep):
    const draft = readDraft(id);
    if (draft) {
      if (draft.base === data.page.revision) {
        history.commit(draft.tree);
        setToast("Restored your unsaved changes from the last session. They will be saved now.");
      } else {
        clearDraft(id);
        setToast("A local unsaved draft was discarded because this page changed since then.");
      }
    }
  }, [projectId, history.reset, history.commit]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadSide = useCallback(() => Promise.all([
    api.get(`/api/projects/${projectId}/messages`).then((d) => setMessages(d.messages)),
    api.get(`/api/projects/${projectId}/runs`).then((d) => setRuns(d.runs)),
    api.get(`/api/projects/${projectId}/assets`).then((d) => setAssets(d.assets.map(absAsset))),
  ]).catch((e) => showError(e.message)), [projectId, showError]);

  useEffect(() => {
    let alive = true;
    loadProject().then((p) => {
      if (!alive) return;
      if (p.latestRun && ACTIVE.has(p.latestRun.status)) setActiveRun(p.latestRun);
      if (p.pages.length) {
        setPageId(p.pages[0].id);
        loadPage(p.pages[0].id).catch((e) => showError(e.message));
      }
    }).catch((e) => setFatal(e.status === 404 ? "Project not found (or it belongs to another account)." : e.message));
    loadSide();
    return () => { alive = false; };
  }, [loadProject, loadPage, loadSide, showError]);

  // -------------------------------------------------------------- saving
  const save = useCallback(async () => {
    const current = treeRef.current;
    if (!current || current === savedTreeRef.current || !pageId) return;
    setSaveState("saving");
    try {
      const res = await api.put(`/api/projects/${projectId}/pages/${pageId}`, { tree: current, baseRevision: revisionRef.current });
      revisionRef.current = res.revision;
      savedTreeRef.current = current;
      if (treeRef.current === current) clearDraft(pageId);
      setSaveState(treeRef.current === current ? "saved" : "unsaved");
      setCodeVersion((v) => v + 1);
      if (res.warnings && res.warnings.length) res.warnings.forEach((w) => log("warn", `Sanitized: ${w}`));
    } catch (err) {
      if (err.status === 409) setConflict(true);
      setSaveState("error");
      if ([0, 502, 503, 504].includes(err.status)) {
        // Server asleep/restarting: changes are kept locally; retry automatically.
        showError("Server is starting up — your changes are kept and will be saved automatically.");
        clearTimeout(saveTimer.current);
        saveTimer.current = setTimeout(() => { savingRef.current = savingRef.current.then(save); }, 8000);
      } else {
        showError(err.message);
      }
    }
  }, [projectId, pageId, log, showError]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!tree || tree === savedTreeRef.current) return undefined;
    setSaveState("unsaved");
    writeDraft(pageId, revisionRef.current, tree);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => { savingRef.current = savingRef.current.then(save); }, 900);
    return () => clearTimeout(saveTimer.current);
  }, [tree, save, pageId]);

  const flushSave = useCallback(async () => {
    clearTimeout(saveTimer.current);
    savingRef.current = savingRef.current.then(save);
    await savingRef.current;
  }, [save]);

  useEffect(() => {
    const warn = (e) => { if (treeRef.current !== savedTreeRef.current) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  const openPage = useCallback(async (id) => {
    if (id === pageId) return;
    await flushSave();
    setSelectedId(null);
    setPageId(id);
    try { await loadPage(id); } catch (e) { showError(e.message); }
  }, [pageId, flushSave, loadPage, showError]);

  // ------------------------------------------------------------- editing
  const edit = useCallback((fn, coalesce) => history.commit((t) => (t ? fn(t) : t), coalesce ? { coalesce } : undefined),
    [history.commit]); // eslint-disable-line react-hooks/exhaustive-deps

  const actions = useMemo(() => ({
    remove(id) {
      const t = treeRef.current;
      const node = id && findNode(t, id);
      if (!node || id === t.id) return;
      if (node.shared) { showError("The shared header/footer can't be deleted — edit or empty it instead."); return; }
      const parent = parentOf(t, id);
      edit((tr) => removeNode(tr, id));
      setSelectedId(parent ? parent.id : null);
    },
    duplicate(id) {
      const { tree: next, newId } = duplicateNode(treeRef.current, id);
      if (newId) { history.commit(next); setSelectedId(newId); }
    },
    group(id) {
      const { tree: next, newId } = groupNode(treeRef.current, id);
      if (newId) { history.commit(next); setSelectedId(newId); }
    },
    ungroup(id) {
      const { tree: next, newId } = ungroupNode(treeRef.current, id);
      if (newId) { history.commit(next); setSelectedId(newId); } else showError("Only containers can be ungrouped.");
    },
    move(id, targetId, position) {
      const next = moveNode(treeRef.current, id, targetId, position);
      if (!next) { showError("That element can't be moved there."); return; }
      history.commit(next);
      setSelectedId(id);
    },
  }), [edit, history, showError]);

  const onCanvasMessage = useCallback((msg, post) => {
    const t = treeRef.current;
    switch (msg.type) {
      case "select": if (typeof msg.id === "string" && findNode(t, msg.id)) setSelectedId(msg.id); break;
      case "hover": setHoveredId(typeof msg.id === "string" ? msg.id : null); break;
      case "text-edit":
        if (findNode(t, msg.id) && typeof msg.text === "string") edit((tr) => updateProps(tr, msg.id, { text: msg.text.slice(0, 5000) }));
        break;
      case "resize": {
        const patch = {};
        if (/^\d{1,5}px$/.test(msg.width || "")) patch.width = msg.width;
        if (/^\d{1,5}px$/.test(msg.height || "")) patch.height = msg.height;
        if (findNode(t, msg.id) && Object.keys(patch).length) edit((tr) => updateStyles(tr, msg.id, breakpoint, patch));
        break;
      }
      case "move": actions.move(msg.id, msg.targetId, ["before", "after", "inside"].includes(msg.position) ? msg.position : "after"); break;
      case "rerender": setRenderKey((k) => k + 1); break;
      case "console": log(["error", "warn", "info"].includes(msg.level) ? msg.level : "info", `[canvas] ${String(msg.message).slice(0, 2000)}`); break;
      case "navigate": {
        const href = String(msg.href || "");
        const page = project && project.pages.find((p) => p.route === href.split("#")[0].split("?")[0]);
        if (page) openPage(page.id);
        else log("info", `Link to ${href} (external links open in the exported site).`);
        break;
      }
      case "submit": {
        const entity = String(msg.entity || "");
        const data = msg.data && typeof msg.data === "object" ? msg.data : {};
        api.post(`/api/projects/${projectId}/data/${encodeURIComponent(entity)}`, data)
          .then(() => {
            log("info", `POST ${entity} → 201 Created (preview API)`);
            post({ type: "form-result", formSeq: msg.formSeq, ok: true });
            setTimeout(() => setRenderKey((k) => k + 1), 1500); // refresh bound collections
          })
          .catch((err) => {
            log("error", `POST ${entity} → ${err.status || "error"}: ${err.message}`);
            post({ type: "form-result", formSeq: msg.formSeq, ok: false, message: err.message });
          });
        break;
      }
      case "key": handleKey(msg); break;
      default:
    }
  }, [actions, breakpoint, edit, log, openPage, project, projectId, selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleKey({ key, ctrl, shift }) {
    const k = key.toLowerCase();
    if (ctrl && k === "z" && !shift) history.undo();
    else if (ctrl && (k === "y" || (k === "z" && shift))) history.redo();
    else if (ctrl && k === "d") actions.duplicate(selectedId);
    else if (ctrl && k === "g") (shift ? actions.ungroup : actions.group)(selectedId);
    else if (ctrl && k === "s") flushSave();
    else if ((key === "Delete" || key === "Backspace") && !ctrl) actions.remove(selectedId);
    else if (key === "Escape") setSelectedId(null);
  }

  useEffect(() => {
    const onKey = (e) => {
      const el = e.target;
      const tag = (el.tagName || "").toLowerCase();
      if (["input", "textarea", "select"].includes(tag) || el.isContentEditable) return;
      const ctrl = e.ctrlKey || e.metaKey;
      if ((ctrl && /^[zydgs]$/i.test(e.key)) || ((e.key === "Delete" || e.key === "Backspace") && selectedId)) e.preventDefault();
      handleKey({ key: e.key, ctrl, shift: e.shiftKey });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const insert = useCallback((node, kind) => {
    const t = treeRef.current;
    let next;
    const sel = selectedId && findNode(t, selectedId);
    if (kind === "section") {
      const path = sel ? pathTo(t, sel.id) : null;
      const top = path && path.length > 1 ? path[1] : null;
      const footer = t.children.find((c) => c.shared === "footer");
      if (top && top.shared !== "footer") next = insertNode(t, top.id, "after", node);
      else if (footer) next = insertNode(t, footer.id, "before", node);
      else next = insertNode(t, t.id, "inside", node);
    } else if (sel && CONTAINER_TYPES.has(sel.type) && sel.type !== "collection" && sel.type !== "page") {
      next = insertNode(t, sel.id, "inside", node);
    } else if (sel && sel.id !== t.id && !(parentOf(t, sel.id) || {}).type?.includes("collection")) {
      next = insertNode(t, sel.id, "after", node);
    } else {
      const firstOwn = t.children.find((c) => !c.shared);
      next = firstOwn ? insertNode(t, firstOwn.id, "inside", node) : insertNode(t, t.id, "inside", node);
    }
    history.commit(next);
    setSelectedId(node.id);
    if (node.type === "form") loadProject();
  }, [selectedId, history, loadProject]);

  // ---------------------------------------------------------- agent runs
  const afterServerChange = useCallback(async () => {
    const p = await loadProject();
    const keep = p.pages.find((pg) => pg.id === pageId) ? pageId : p.pages[0] && p.pages[0].id;
    setPageId(keep);
    if (keep) await loadPage(keep);
    setRenderKey((k) => k + 1);
    setCodeVersion((v) => v + 1);
    loadSide();
  }, [loadProject, loadPage, loadSide, pageId]);

  useEffect(() => {
    if (!activeRun || !ACTIVE.has(activeRun.status)) return undefined;
    const timer = setInterval(async () => {
      try {
        const { run } = await api.get(`/api/runs/${activeRun.id}`);
        setActiveRun(run);
        if (!ACTIVE.has(run.status)) {
          clearInterval(timer);
          setAssistantBusy(false);
          if (run.status === "failed") showError(run.error || "The AI task failed. Your project was not changed.");
          await afterServerChange();
          setActiveRun(null);
        }
      } catch (e) { showError(e.message); }
    }, 1500);
    return () => clearInterval(timer);
  }, [activeRun, afterServerChange, showError]);

  const sendToAssistant = async (message, target) => {
    setAssistantBusy(true);
    setMessages((m) => [...m, { id: `local-${Date.now()}`, role: "user", content: message }]);
    try {
      if (target) {
        const node = findNode(treeRef.current, target.id);
        const res = await api.post(`/api/projects/${projectId}/assistant`, {
          message, selection: { pageId, nodeId: target.id, node },
        });
        if (res.mode === "edit" && findNode(treeRef.current, target.id)) {
          history.commit((t) => replaceNode(t, target.id, res.node));
        }
        setAssistantBusy(false);
        loadSide();
      } else {
        await flushSave();
        const res = await api.post(`/api/projects/${projectId}/assistant`, { message });
        setActiveRun(res.run);
      }
    } catch (err) {
      setAssistantBusy(false);
      setMessages((m) => [...m, { id: `err-${Date.now()}`, role: "assistant", content: `⚠ ${err.message}` }]);
    }
  };

  const continueGeneration = async () => {
    try {
      await flushSave();
      const res = await api.post(`/api/projects/${projectId}/generate`, { resume: true });
      setActiveRun(res.run);
    } catch (err) { showError(err.message); }
  };

  const cancelRun = async () => {
    if (!activeRun) return;
    try {
      const res = await api.post(`/api/runs/${activeRun.id}/cancel`);
      setActiveRun((r) => (r ? { ...r, message: res.status === "cancelled" ? "Cancelled" : "Cancelling…" } : r));
    } catch (err) { showError(err.message); }
  };

  const autoRepair = async () => {
    try {
      await flushSave();
      const res = await api.post(`/api/projects/${projectId}/repair`);
      setActiveRun(res.run);
      setRightTab("ai");
    } catch (err) { showError(err.message); }
  };

  const runChecks = async () => {
    setChecking(true);
    try {
      await flushSave();
      const { report } = await api.post(`/api/projects/${projectId}/checks`);
      setChecks(report);
      setBottomTab("checks");
    } catch (e) { showError(e.message); } finally { setChecking(false); }
  };

  const selectIssue = async (issue) => {
    if (issue.route && issue.route.startsWith("/")) {
      const page = project.pages.find((p) => p.route === issue.route);
      if (page && page.id !== pageId) await openPage(page.id);
    }
    if (issue.nodeId) { setSelectedId(issue.nodeId); setRightTab("inspect"); }
  };

  const exportZip = async () => {
    try {
      await flushSave();
      const res = await apiFetch(`/api/projects/${projectId}/export`, { raw: true });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(project.name || "aidevs-app").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { showError(e.message); }
  };

  const rename = async (name) => {
    if (!name.trim() || name === project.name) return;
    try { const d = await api.patch(`/api/projects/${projectId}`, { name }); setProject(d.project); } catch (e) { showError(e.message); }
  };

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(""), 6000);
    return () => clearTimeout(t);
  }, [toast]);

  // --------------------------------------------------------------- render
  if (fatal) return <div className="aid-fullscreen-msg"><p>{fatal}</p><Link className="aid-btn" to="/projects">Back to projects</Link></div>;
  if (!project) return <div className="aid-fullscreen-msg"><div className="aid-spinner" />Opening project…</div>;
  const generating = activeRun && activeRun.kind === "generate" && ACTIVE.has(activeRun.status);
  const saveLabel = { saved: "All changes saved", saving: "Saving…", unsaved: "Unsaved changes", error: "Save failed" }[saveState];

  return (
    <div className="st-root">
      <div className="st-top" role="toolbar" aria-label="Studio toolbar">
        <Link to="/projects" className="aid-icon-btn" title="All projects" aria-label="All projects"
          onClick={async (e) => {
            if (treeRef.current !== savedTreeRef.current) { e.preventDefault(); await flushSave(); navigate("/projects"); }
          }}>←</Link>
        <input className="st-project-name" defaultValue={project.name} key={project.name} aria-label="Project name"
          onBlur={(e) => rename(e.target.value)} onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()} />
        <span className={`st-save ${saveState}`} role="status">{saveLabel}</span>
        <div className="st-top-group">
          <button className="aid-icon-btn" title="Undo (Ctrl+Z)" aria-label="Undo" disabled={!history.canUndo} onClick={history.undo}>↶</button>
          <button className="aid-icon-btn" title="Redo (Ctrl+Y)" aria-label="Redo" disabled={!history.canRedo} onClick={history.redo}>↷</button>
        </div>
        <div className="st-top-group" role="group" aria-label="Device">
          {Object.entries(DEVICES).map(([key, d]) => (
            <button key={key} className={`aid-icon-btn ${device === key ? "active" : ""}`} title={`${d.label} (${d.width}px)`}
              aria-pressed={device === key} onClick={() => setDevice(key)}>{d.icon}</button>
          ))}
          <select className="aid-select st-zoom" value={zoom} aria-label="Zoom"
            onChange={(e) => setZoom(e.target.value === "fit" ? "fit" : Number(e.target.value))}>
            <option value="fit">Fit</option><option value={0.5}>50%</option><option value={0.75}>75%</option><option value={1}>100%</option>
          </select>
        </div>
        <div className="st-top-group" role="group" aria-label="Mode">
          <button className={`aid-btn aid-btn-sm ${mode === "edit" ? "aid-btn-primary" : ""}`} onClick={() => setMode("edit")}>Design</button>
          <button className={`aid-btn aid-btn-sm ${mode === "interact" ? "aid-btn-primary" : ""}`} onClick={() => setMode("interact")}
            title="Click links and submit forms against the preview API">Preview</button>
        </div>
        <div className="st-top-right">
          <button className="aid-btn aid-btn-sm" onClick={() => setBottomTab(bottomTab === "code" ? null : "code")}>{"</>"} Code</button>
          <button className="aid-btn aid-btn-sm" onClick={runChecks} disabled={checking}>Test</button>
          <button className="aid-btn aid-btn-sm aid-btn-primary" onClick={exportZip}>Export</button>
        </div>
      </div>

      {!activeRun && ["partial", "failed"].includes(project.status) && (
        <div className="aid-alert aid-alert-info st-banner" role="status">
          {(() => {
            const empty = project.pages.filter((p) => p.sectionCount === 0).length;
            return empty > 0
              ? `${project.pages.length - empty} of ${project.pages.length} pages are built. The rest were not generated because the free AI capacity ran out.`
              : "The last AI generation did not finish.";
          })()}
          <button className="aid-btn aid-btn-sm aid-btn-primary" onClick={continueGeneration}>Continue generation</button>
          <span className="st-note">Only empty pages are built; your finished pages and edits are kept.</span>
        </div>
      )}
      {conflict && (
        <div className="aid-alert aid-alert-error st-banner">This page changed elsewhere (another tab or an AI task).
          <button className="aid-btn aid-btn-sm" onClick={() => loadPage(pageId)}>Reload latest</button></div>
      )}

      <div className="st-body">
        <aside className="st-left" aria-label="Project navigator">
          <div className="st-tabs st-tabs-wrap" role="tablist">
            {LEFT_TABS.map(([key, label]) => (
              <button key={key} role="tab" aria-selected={leftTab === key} className={leftTab === key ? "on" : ""} onClick={() => setLeftTab(key)}>{label}</button>
            ))}
          </div>
          <div className="st-left-body">
            {leftTab === "pages" && <PagesPanel project={project} pageId={pageId} onOpen={openPage} onChanged={afterServerChange} onError={showError} />}
            {leftTab === "layers" && (
              <LayersPanel tree={tree} selectedId={selectedId} hoveredId={hoveredId} onSelect={setSelectedId} onHover={setHoveredId}
                onRename={(id, name) => edit((t) => updateNode(t, id, { name }))} onMove={actions.move}
                onDuplicate={() => actions.duplicate(selectedId)} onDelete={() => actions.remove(selectedId)}
                onGroup={() => actions.group(selectedId)} onUngroup={() => actions.ungroup(selectedId)} />
            )}
            {leftTab === "add" && <AddPanel projectId={projectId} entities={project.entities} onInsert={insert} onError={showError} />}
            {leftTab === "design" && <DesignPanel project={project} onSaved={async () => { await loadProject(); setRenderKey((k) => k + 1); }} onError={showError} />}
            {leftTab === "assets" && (
              <AssetsPanel projectId={projectId} assets={assets} onError={showError}
                reload={() => api.get(`/api/projects/${projectId}/assets`).then((d) => setAssets(d.assets.map(absAsset)))}
                canUse={Boolean(selected && selected.type === "image")}
                onUse={(a) => edit((t) => updateProps(t, selectedId, { src: a.url }))} />
            )}
            {leftTab === "data" && <DataPanel project={project} onChanged={afterServerChange} onError={showError} />}
            {leftTab === "versions" && <VersionsPanel projectId={projectId} onRestored={afterServerChange} onError={showError} beforeRestore={flushSave} />}
          </div>
        </aside>

        <div className="st-center" role="main">
          <Canvas projectId={projectId} pageId={pageId} tree={tree} device={device} zoom={zoom} mode={mode}
            selectedId={selectedId} hoveredId={hoveredId} renderKey={renderKey} onMessage={onCanvasMessage} onError={showError} />
          {generating && (
            <div className="st-generating" role="status">
              <h2>Building your application…</h2>
              <div className="st-progress"><span style={{ width: `${activeRun.progress}%` }} /></div>
              <ol>{(activeRun.steps || []).slice(-6).map((s, i) => <li key={i} className={s.level}>{s.message}</li>)}</ol>
              <button className="aid-btn" onClick={cancelRun}>Cancel generation</button>
            </div>
          )}
          <BottomPanel projectId={projectId} consoleLines={consoleLines} onClearConsole={() => setConsoleLines([])}
            checks={checks} onRunChecks={runChecks} checking={checking} runs={runs} onSelectIssue={selectIssue}
            onAutoRepair={autoRepair} repairBusy={Boolean(activeRun)}
            selectedId={selectedId} codeVersion={codeVersion} tab={bottomTab} setTab={setBottomTab} />
        </div>

        <aside className="st-right" aria-label="Inspector and assistant">
          <div className="st-tabs" role="tablist">
            <button role="tab" aria-selected={rightTab === "inspect"} className={rightTab === "inspect" ? "on" : ""} onClick={() => setRightTab("inspect")}>Properties</button>
            <button role="tab" aria-selected={rightTab === "ai"} className={rightTab === "ai" ? "on" : ""} onClick={() => setRightTab("ai")}>AI Assistant</button>
          </div>
          <div className="st-right-body">
            {rightTab === "inspect" ? (
              <Inspector node={selected} parent={selectedParent} breakpoint={breakpoint} tokens={project.tokens}
                entities={project.entities} assets={assets}
                onProps={(patch, key) => edit((t) => updateProps(t, selectedId, patch), key && `${selectedId}:p:${key}`)}
                onStyles={(patch, key) => edit((t) => updateStyles(t, selectedId, breakpoint, patch), key && `${selectedId}:${breakpoint}:${key}`)}
                onNode={(patch, key) => edit((t) => updateNode(t, selectedId, patch), key && `${selectedId}:n:${key}`)} />
            ) : (
              <AssistantPanel messages={messages} onSend={sendToAssistant} busy={assistantBusy || Boolean(activeRun)}
                onCancel={cancelRun}
                activeRun={activeRun && !generating ? activeRun : null}
                selection={selected && selected.id !== tree.id ? { id: selected.id, name: selected.name } : null}
                onClearSelection={() => setSelectedId(null)} />
            )}
          </div>
        </aside>
      </div>
      {toast && <div className="st-toast" role="alert" onClick={() => setToast("")}>{toast}</div>}
    </div>
  );
}
