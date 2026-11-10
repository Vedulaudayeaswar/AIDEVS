import React, { useCallback, useEffect, useState } from "react";
import API_URL from "../config";
import { api, apiFetch } from "../lib/api";

export function plural(name) {
  if (/[^aeiou]y$/.test(name)) return `${name.slice(0, -1)}ies`;
  if (/(s|x|ch|sh)$/.test(name)) return `${name}es`;
  return `${name}s`;
}

// ------------------------------------------------------------------ Pages
export function PagesPanel({ project, pageId, onOpen, onChanged, onError }) {
  const [name, setName] = useState("");
  const [route, setRoute] = useState("");
  const [busy, setBusy] = useState(false);
  const page = project.pages.find((p) => p.id === pageId);
  const [seo, setSeo] = useState(page ? page.seo : {});
  useEffect(() => setSeo(page ? page.seo || {} : {}), [page]);

  const add = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = route.startsWith("/") ? route : `/${route}`;
      const data = await api.post(`/api/projects/${project.id}/pages`, { name, route: r.toLowerCase() });
      setName(""); setRoute("");
      await onChanged();
      onOpen(data.page.id);
    } catch (err) { onError(err.message); } finally { setBusy(false); }
  };
  const remove = async (p) => {
    if (!window.confirm(`Delete page ${p.route}? A version is saved first so you can restore it.`)) return;
    try { await api.del(`/api/projects/${project.id}/pages/${p.id}`); await onChanged(); } catch (err) { onError(err.message); }
  };
  const saveSeo = async () => {
    try { await api.patch(`/api/projects/${project.id}/pages/${pageId}`, { seo }); await onChanged(); } catch (err) { onError(err.message); }
  };

  return (
    <div className="st-panel-pad">
      <ul className="st-list">
        {project.pages.map((p) => (
          <li key={p.id} className={p.id === pageId ? "active" : ""}>
            <button type="button" onClick={() => onOpen(p.id)}><strong>{p.name}</strong> <code>{p.route}</code></button>
            {project.pages.length > 1 && <button type="button" className="aid-icon-btn" title="Delete page" onClick={() => remove(p)}>🗑</button>}
          </li>
        ))}
      </ul>
      <form className="st-mini-form" onSubmit={add}>
        <span className="aid-label">New page</span>
        <input className="aid-input" placeholder="Name (e.g. About)" value={name} onChange={(e) => {
          setName(e.target.value);
          setRoute(`/${e.target.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`);
        }} required />
        <input className="aid-input" placeholder="/route" value={route} onChange={(e) => setRoute(e.target.value)} required />
        <button className="aid-btn aid-btn-sm" disabled={busy || !name}>Add page</button>
      </form>
      {page && (
        <div className="st-mini-form">
          <span className="aid-label">SEO · {page.route}</span>
          <input className="aid-input" placeholder="Title" maxLength={70} value={seo.title || ""} onChange={(e) => setSeo({ ...seo, title: e.target.value })} />
          <textarea className="aid-textarea" rows={3} maxLength={170} placeholder="Meta description" value={seo.description || ""} onChange={(e) => setSeo({ ...seo, description: e.target.value })} />
          <button className="aid-btn aid-btn-sm" onClick={saveSeo}>Save SEO</button>
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------------- Add
export function AddPanel({ projectId, entities, onInsert, onError }) {
  const [palette, setPalette] = useState(null);
  const [entity, setEntity] = useState("");
  useEffect(() => { api.get("/api/studio/palette").then(setPalette).catch((e) => onError(e.message)); }, [onError]);
  const build = async (kind, key) => {
    try {
      const data = await api.post(`/api/projects/${projectId}/build-node`, { kind, key, entity: entity || undefined });
      onInsert(data.node, kind);
    } catch (err) { onError(err.message); }
  };
  if (!palette) return <div className="st-panel-pad"><div className="aid-spinner" /></div>;
  return (
    <div className="st-panel-pad">
      <span className="aid-label">Sections</span>
      {entities.length > 0 && (
        <select className="aid-select" value={entity} onChange={(e) => setEntity(e.target.value)} aria-label="Data model for collection grid">
          <option value="">Collection grid data: {entities[0].label}</option>
          {entities.map((e) => <option key={e.name} value={e.name}>{e.label}</option>)}
        </select>
      )}
      <div className="st-palette">
        {palette.sections.map((s) => <button key={s.key} type="button" onClick={() => build("section", s.key)}>{s.label}</button>)}
      </div>
      <span className="aid-label">Elements</span>
      <div className="st-palette">
        {palette.elements.map((s) => <button key={s.key} type="button" onClick={() => build("element", s.key)}>{s.label}</button>)}
      </div>
      <p className="st-note">Elements are inserted into the selected container (or after the selected element). Sections go after the selected section.</p>
    </div>
  );
}

// ---------------------------------------------------------------- Design
export function DesignPanel({ project, onSaved, onError }) {
  const [tokens, setTokens] = useState(project.tokens);
  useEffect(() => setTokens(project.tokens), [project.tokens]);
  const save = async () => {
    try { await api.patch(`/api/projects/${project.id}`, { tokens }); await onSaved(); } catch (err) { onError(err.message); }
  };
  const setColor = (k, v) => setTokens({ ...tokens, colors: { ...tokens.colors, [k]: v } });
  return (
    <div className="st-panel-pad">
      <span className="aid-label">Colour tokens</span>
      {Object.entries(tokens.colors || {}).map(([k, v]) => (
        <div className="st-token" key={k}>
          <input type="color" value={/^#[0-9a-f]{6}$/i.test(v) ? v : "#000000"} onChange={(e) => setColor(k, e.target.value)} aria-label={`${k} colour`} />
          <span>{k}</span>
          <input className="aid-input" value={v} onChange={(e) => setColor(k, e.target.value)} aria-label={`${k} value`} />
        </div>
      ))}
      <span className="aid-label">Fonts (Google Fonts)</span>
      {["heading", "body"].map((k) => (
        <div className="st-token" key={k}><span>{k}</span>
          <input className="aid-input" value={(tokens.fonts || {})[k] || ""} onChange={(e) => setTokens({ ...tokens, fonts: { ...tokens.fonts, [k]: e.target.value } })} /></div>
      ))}
      <div className="st-token"><span>radius</span><input className="aid-input" value={tokens.radius || ""} onChange={(e) => setTokens({ ...tokens, radius: e.target.value })} /></div>
      <div className="st-token"><span>max width</span><input className="aid-input" value={tokens.maxWidth || ""} onChange={(e) => setTokens({ ...tokens, maxWidth: e.target.value })} /></div>
      <button className="aid-btn aid-btn-primary aid-btn-sm" onClick={save}>Apply design tokens</button>
      <p className="st-note">Tokens are global: every element using var(--color-…) updates on every page and in the export.</p>
    </div>
  );
}

// ---------------------------------------------------------------- Assets
export function AssetsPanel({ projectId, assets, reload, onUse, canUse, onError }) {
  const [busy, setBusy] = useState(false);
  const upload = async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    try { await apiFetch(`/api/projects/${projectId}/assets`, { method: "POST", form }); await reload(); }
    catch (err) { onError(err.message); } finally { setBusy(false); }
  };
  const remove = async (a) => {
    if (!window.confirm(`Delete ${a.filename}? Images using it will break.`)) return;
    try { await api.del(`/api/projects/${projectId}/assets/${a.id}`); await reload(); } catch (err) { onError(err.message); }
  };
  return (
    <div className="st-panel-pad">
      <label className="aid-btn aid-btn-sm st-upload">
        {busy ? "Uploading…" : "Upload image"}
        <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={upload} hidden />
      </label>
      <p className="st-note">PNG, JPEG, GIF or WebP up to 3 MB. Select an image element, then click an asset to use it.</p>
      <div className="st-assets">
        {assets.map((a) => (
          <figure key={a.id}>
            <button type="button" disabled={!canUse} onClick={() => onUse(a)} title={canUse ? "Use for selected image" : a.filename}>
              <img src={a.absUrl} alt={a.filename} />
            </button>
            <figcaption>{a.filename}<button type="button" className="st-link" onClick={() => remove(a)}>delete</button></figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------- Data & API
const FIELD_TYPES = ["string", "text", "integer", "number", "boolean", "date", "datetime", "email", "url", "image"];
const LEVELS = ["public", "auth", "owner", "admin"];

function EntityEditor({ projectId, entity, onDone, onError }) {
  const [draft, setDraft] = useState(() => entity ? JSON.parse(JSON.stringify(entity)) : {
    name: "", label: "", fields: [{ name: "title", type: "string", required: true }],
    permissions: { read: "public", create: "admin", update: "admin", delete: "admin" },
  });
  const setField = (i, patch) => setDraft({ ...draft, fields: draft.fields.map((f, j) => (j === i ? { ...f, ...patch } : f)) });
  const save = async () => {
    try {
      if (entity) await api.put(`/api/projects/${projectId}/entities/${entity.id}`, draft);
      else await api.post(`/api/projects/${projectId}/entities`, draft);
      onDone();
    } catch (err) { onError(err.message); }
  };
  return (
    <div className="st-entity-editor">
      {!entity && <input className="aid-input" placeholder="name (snake_case, e.g. booking)" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />}
      <input className="aid-input" placeholder="Label" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
      {draft.fields.map((f, i) => (
        <div className="st-field-row" key={i}>
          <input className="aid-input" value={f.name} aria-label="Field name" onChange={(e) => setField(i, { name: e.target.value })} />
          <select className="aid-select" value={f.type} aria-label="Field type" onChange={(e) => setField(i, { type: e.target.value })}>
            {FIELD_TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
          <label title="Required"><input type="checkbox" checked={f.required} onChange={(e) => setField(i, { required: e.target.checked })} />req</label>
          <button type="button" className="aid-icon-btn" aria-label="Remove field" onClick={() => setDraft({ ...draft, fields: draft.fields.filter((_, j) => j !== i) })}>×</button>
        </div>
      ))}
      <button type="button" className="st-link" onClick={() => setDraft({ ...draft, fields: [...draft.fields, { name: "", type: "string", required: false }] })}>+ add field</button>
      <div className="st-perm-grid">
        {Object.keys(draft.permissions).map((action) => (
          <label key={action}>{action}
            <select className="aid-select" value={draft.permissions[action]} onChange={(e) => setDraft({ ...draft, permissions: { ...draft.permissions, [action]: e.target.value } })}>
              {LEVELS.map((l) => <option key={l}>{l}</option>)}
            </select>
          </label>
        ))}
      </div>
      <div className="st-row"><button className="aid-btn aid-btn-primary aid-btn-sm" onClick={save}>Save model</button>
        <button className="aid-btn aid-btn-sm" onClick={onDone}>Cancel</button></div>
    </div>
  );
}

export function DataPanel({ project, onChanged, onError }) {
  const [editing, setEditing] = useState(null);
  const [records, setRecords] = useState({});
  const load = useCallback(async (name) => {
    try {
      const data = await api.get(`/api/projects/${project.id}/data/${name}`);
      setRecords((r) => ({ ...r, [name]: data.items }));
    } catch (err) { onError(err.message); }
  }, [project.id, onError]);
  const remove = async (e) => {
    if (!window.confirm(`Delete data model ${e.label}? Bound forms/collections will show check errors.`)) return;
    try { await api.del(`/api/projects/${project.id}/entities/${e.id}`); await onChanged(); } catch (err) { onError(err.message); }
  };
  const done = async () => { setEditing(null); await onChanged(); };
  return (
    <div className="st-panel-pad">
      <p className="st-note">Each model becomes a database table and a REST API in the exported backend. Preview forms write to a sandboxed copy of that API.</p>
      {project.entities.map((e) => (
        <div key={e.id} className="st-entity">
          <div className="st-row"><strong>{e.label}</strong><code>{e.name}</code></div>
          {editing === e.id ? <EntityEditor projectId={project.id} entity={e} onDone={done} onError={onError} /> : (
            <>
              <div className="st-note">{e.fields.map((f) => `${f.name}${f.required ? "*" : ""}:${f.type}`).join(" · ")}</div>
              <table className="st-api">
                <tbody>
                  <tr><td>GET</td><td>/api/{plural(e.name)}</td><td>{e.permissions.read}</td></tr>
                  <tr><td>POST</td><td>/api/{plural(e.name)}</td><td>{e.permissions.create}</td></tr>
                  <tr><td>PATCH</td><td>/api/{plural(e.name)}/:id</td><td>{e.permissions.update}</td></tr>
                  <tr><td>DELETE</td><td>/api/{plural(e.name)}/:id</td><td>{e.permissions.delete}</td></tr>
                </tbody>
              </table>
              <div className="st-row">
                <button className="aid-btn aid-btn-sm" onClick={() => setEditing(e.id)}>Edit</button>
                <button className="aid-btn aid-btn-sm" onClick={() => load(e.name)}>Preview data</button>
                <button className="aid-btn aid-btn-sm aid-btn-danger" onClick={() => remove(e)}>Delete</button>
              </div>
              {records[e.name] && (
                <div className="st-records">
                  {records[e.name].length === 0 ? <p className="st-note">No submissions yet (sample rows come from the spec).</p> :
                    records[e.name].map((r) => <pre key={r.id}>{JSON.stringify(r, null, 1)}</pre>)}
                </div>
              )}
            </>
          )}
        </div>
      ))}
      {editing === "new" ? <EntityEditor projectId={project.id} onDone={done} onError={onError} /> :
        <button className="aid-btn aid-btn-sm" onClick={() => setEditing("new")}>+ New data model</button>}
    </div>
  );
}

// -------------------------------------------------------------- Versions
export function VersionsPanel({ projectId, onRestored, onError, beforeRestore }) {
  const [versions, setVersions] = useState([]);
  const [diff, setDiff] = useState({});
  const [label, setLabel] = useState("");
  const load = useCallback(() => api.get(`/api/projects/${projectId}/versions`).then((d) => setVersions(d.versions))
    .catch((e) => onError(e.message)), [projectId, onError]);
  useEffect(() => { load(); }, [load]);
  const create = async (e) => {
    e.preventDefault();
    await beforeRestore();
    try { await api.post(`/api/projects/${projectId}/versions`, { label: label || "Checkpoint" }); setLabel(""); load(); }
    catch (err) { onError(err.message); }
  };
  const showDiff = async (v) => {
    try { const d = await api.get(`/api/projects/${projectId}/versions/${v.id}/diff`); setDiff({ ...diff, [v.id]: d.diff }); }
    catch (err) { onError(err.message); }
  };
  const restore = async (v) => {
    if (!window.confirm(`Restore v${v.number} "${v.label}"? Your current state is saved as a version first.`)) return;
    await beforeRestore();
    try { await api.post(`/api/projects/${projectId}/versions/${v.id}/restore`); await onRestored(); load(); }
    catch (err) { onError(err.message); }
  };
  const summary = (d) => [
    d.pagesAdded.length && `pages added since: ${d.pagesAdded.join(", ")}`,
    d.pagesRemoved.length && `pages removed since: ${d.pagesRemoved.join(", ")}`,
    d.pagesChanged.length && `changed: ${d.pagesChanged.map((c) => `${c.route} (${c.nodesBefore}→${c.nodesAfter} nodes)`).join(", ")}`,
    d.entitiesAdded.length && `models added: ${d.entitiesAdded.join(", ")}`,
    d.entitiesChanged.length && `models changed: ${d.entitiesChanged.join(", ")}`,
    d.tokensChanged && "design tokens changed", d.layoutChanged && "header/footer changed",
  ].filter(Boolean).join("; ") || "Identical to the current project.";
  return (
    <div className="st-panel-pad">
      <form className="st-row" onSubmit={create}>
        <input className="aid-input" placeholder="Checkpoint name" value={label} onChange={(e) => setLabel(e.target.value)} />
        <button className="aid-btn aid-btn-sm">Save version</button>
      </form>
      <ul className="st-versions">
        {versions.map((v) => (
          <li key={v.id}>
            <div><strong>v{v.number}</strong> {v.label}</div>
            <div className="st-note">{new Date(v.createdAt).toLocaleString()} · {v.reason}</div>
            <div className="st-row">
              <button className="aid-btn aid-btn-sm" onClick={() => showDiff(v)}>Compare</button>
              <button className="aid-btn aid-btn-sm" onClick={() => restore(v)}>Restore</button>
            </div>
            {diff[v.id] && <div className="st-note">{summary(diff[v.id])}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export const absAsset = (a) => ({ ...a, absUrl: `${API_URL}${a.url}` });
