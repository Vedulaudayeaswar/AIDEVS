import React, { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import "./ProjectsPage.css";

// Operator console. The server independently enforces admin access (404 for others).
export default function AdminPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState(null);
  const [settings, setSettings] = useState([]);
  const [draft, setDraft] = useState({});
  const [users, setUsers] = useState([]);
  const [models, setModels] = useState(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");

  const load = useCallback(async () => {
    try {
      const [o, s, u] = await Promise.all([api.get("/api/admin/overview"), api.get("/api/admin/settings"),
        api.get("/api/admin/users")]);
      setOverview(o); setSettings(s.settings); setUsers(u.users); setError("");
    } catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { if (user && user.role === "admin") load(); }, [user, load]);

  if (user && user.role !== "admin") return <Navigate to="/projects" replace />;

  const saveSettings = async () => {
    try {
      const body = {};
      Object.entries(draft).forEach(([k, v]) => {
        const s = settings.find((x) => x.key === k);
        body[k] = s.type === "bool" ? v === true || v === "true" : Number(v);
      });
      const res = await api.put("/api/admin/settings", body);
      setSettings(res.settings); setDraft({}); setSaved("Settings saved."); setTimeout(() => setSaved(""), 3000);
    } catch (e) { setError(e.message); }
  };
  const toggleUser = async (u) => {
    if (!window.confirm(`${u.isActive ? "Disable" : "Enable"} ${u.email}?${u.isActive ? " All their sessions end immediately." : ""}`)) return;
    try { await api.patch(`/api/admin/users/${u.id}`, { isActive: !u.isActive }); load(); } catch (e) { setError(e.message); }
  };

  return (
    <div className="pp">
      <div className="pp-top" role="banner">
        <Link to="/projects" className="pp-logo">AIDevs <span>Admin</span></Link>
        <div className="pp-top-right"><button className="aid-btn aid-btn-sm" onClick={load}>Refresh</button>
          <Link className="aid-btn aid-btn-sm" to="/projects">Projects</Link></div>
      </div>
      <div className="pp-main" role="main">
        {error && <div className="aid-alert aid-alert-error" role="alert">{error}</div>}
        {!overview ? <div className="aid-spinner" /> : (
          <>
            <section className="pp-review">
              <h3>Health</h3>
              <div className="acc-grid">
                <div><strong>{overview.users}</strong><div className="pp-muted">users ({overview.newUsers24h} new today)</div></div>
                <div><strong>{overview.projects}</strong><div className="pp-muted">projects</div></div>
                <div><strong>{Object.entries(overview.queue).map(([k, v]) => `${k}: ${v}`).join(" · ") || "empty"}</strong><div className="pp-muted">job queue</div></div>
                <div><strong>{overview.workerHeartbeat ? new Date(overview.workerHeartbeat).toLocaleTimeString() : "no in-process worker"}</strong><div className="pp-muted">worker heartbeat</div></div>
                <div><strong>{overview.rateLimitBackend}</strong><div className="pp-muted">rate-limit backend · blocked: {Object.entries(overview.rateLimited).map(([k, v]) => `${k} ${v}`).join(", ") || "none"}</div></div>
              </div>
            </section>
            <section className="pp-review">
              <h3>AI usage (24h, one platform Groq key)</h3>
              <table className="adm-table"><thead><tr><th>Model</th><th>Status</th><th>Requests</th><th>Tokens</th></tr></thead>
                <tbody>{overview.aiUsage24h.map((r, i) => <tr key={i}><td>{r.model}</td><td>{r.status}</td><td>{r.requests}</td><td>{r.tokens.toLocaleString()}</td></tr>)}</tbody></table>
              <button className="aid-btn aid-btn-sm" onClick={async () => { try { setModels(await api.get("/api/admin/models")); } catch (e) { setError(e.message); } }}>Check model availability</button>
              {models && (
                <table className="adm-table"><thead><tr><th>Task</th><th>Configured chain</th><th>Usable with this key</th></tr></thead>
                  <tbody>{models.tasks.map((t) => <tr key={t.task}><td>{t.task}</td><td>{t.deterministic ? "deterministic (no model)" : t.configured.join(" → ")}</td>
                    <td>{t.deterministic ? "—" : (models.availabilityChecked ? t.usable.join(", ") || "NONE" : "not checked (no key)")}</td></tr>)}</tbody></table>
              )}
            </section>
            <section className="pp-review">
              <h3>Failed AI runs (24h)</h3>
              {overview.failedRuns.length === 0 ? <p className="pp-muted">None.</p> : (
                <table className="adm-table"><thead><tr><th>When</th><th>Kind</th><th>Attempts</th><th>Error</th></tr></thead>
                  <tbody>{overview.failedRuns.map((r) => <tr key={r.id}><td>{new Date(r.at).toLocaleString()}</td><td>{r.kind}</td><td>{r.attempts}</td><td>{r.error}</td></tr>)}</tbody></table>
              )}
            </section>
            <section className="pp-review">
              <h3>Limits</h3>
              {saved && <div className="aid-alert aid-alert-info">{saved}</div>}
              <table className="adm-table"><thead><tr><th>Setting</th><th>Value</th><th>Default</th></tr></thead><tbody>
                {settings.map((s) => (
                  <tr key={s.key}><td>{s.description}<div className="pp-muted"><code>{s.key}</code></div></td>
                    <td>{s.type === "bool" ? (
                      <select className="aid-select" value={String(draft[s.key] ?? s.value)} onChange={(e) => setDraft({ ...draft, [s.key]: e.target.value })}>
                        <option value="true">on</option><option value="false">off</option></select>
                    ) : (
                      <input className="aid-input" type="number" min="0" value={draft[s.key] ?? s.value} aria-label={s.key}
                        onChange={(e) => setDraft({ ...draft, [s.key]: e.target.value })} />)}</td>
                    <td>{String(s.default)}</td></tr>))}
              </tbody></table>
              <div className="pp-actions"><button className="aid-btn aid-btn-primary" disabled={!Object.keys(draft).length} onClick={saveSettings}>Save limits</button></div>
            </section>
            <section className="pp-review">
              <h3>Users</h3>
              <table className="adm-table"><thead><tr><th>Email</th><th>Role</th><th>Projects</th><th>AI 24h</th><th>Last login</th><th /></tr></thead>
                <tbody>{users.map((u) => (
                  <tr key={u.id}><td>{u.email}</td><td>{u.role}</td><td>{u.projects}</td><td>{u.aiRequests24h}</td>
                    <td>{u.lastLoginAt ? new Date(u.lastLoginAt).toLocaleDateString() : "—"}</td>
                    <td>{u.id !== user.id && <button className={`aid-btn aid-btn-sm ${u.isActive ? "aid-btn-danger" : ""}`} onClick={() => toggleUser(u)}>{u.isActive ? "Disable" : "Enable"}</button>}</td></tr>))}
                </tbody></table>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
