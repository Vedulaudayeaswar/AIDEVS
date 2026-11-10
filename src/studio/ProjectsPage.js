import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { plural } from "./Panels";
import "./ProjectsPage.css";
import "./ProjectsTheme.css";

const EXAMPLES = [
  "A modern e-commerce website for a premium sneaker brand with product catalog and wishlist.",
  "A SaaS landing site for an AI note-taking app with pricing, FAQ and a waitlist signup.",
  "A portfolio for a freelance product designer with case studies and a contact form.",
  "A booking site for a yoga studio with class schedule, instructors and class bookings.",
];

function SpecReview({ spec, reference, onChange, onBack, onGenerate, busy }) {
  const [excluded, setExcluded] = useState(new Set());
  const togglePage = (route) => setExcluded((prev) => {
    const next = new Set(prev);
    if (next.has(route)) next.delete(route); else if (route !== "/") next.add(route);
    return next;
  });
  const colors = (spec.tokens && spec.tokens.colors) || {};
  return (
    <div className="pp-review">
      <div className="pp-review-head">
        <div>
          <span className="aid-label">Application plan</span>
          <input className="aid-input pp-name" value={spec.name} aria-label="Project name"
            onChange={(e) => onChange({ ...spec, name: e.target.value })} />
          <p className="pp-muted">{spec.summary}</p>
          {spec.audience && <p className="pp-muted"><strong>Audience:</strong> {spec.audience}</p>}
        </div>
        <div className="pp-swatches" aria-label="Brand palette">
          {Object.entries(colors).slice(0, 8).map(([k, v]) => (
            <span key={k} title={`${k}: ${v}`} style={{ background: v }} />
          ))}
          <small className="pp-muted">{spec.tokens && spec.tokens.fonts && `${spec.tokens.fonts.heading} / ${spec.tokens.fonts.body}`}</small>
        </div>
      </div>
      {reference && <div className="aid-alert aid-alert-info">Using {reference.url} as structural inspiration ({reference.pages.length} page(s) analysed). Copy and imagery will be original.</div>}
      <div className="pp-cols">
        <section>
          <h3>Pages</h3>
          {spec.pages.map((p) => (
            <label key={p.route} className={`pp-page ${excluded.has(p.route) ? "off" : ""}`}>
              <input type="checkbox" checked={!excluded.has(p.route)} disabled={p.route === "/"}
                onChange={() => togglePage(p.route)} />
              <div>
                <strong>{p.name}</strong> <code>{p.route}</code>
                <div className="pp-muted">{p.purpose}</div>
                <div className="pp-chips">{p.sections.map((s, i) => <span key={i}>{s.kind.replace("_", " ")}</span>)}</div>
              </div>
            </label>
          ))}
        </section>
        <section>
          <h3>Data models &amp; API</h3>
          {spec.entities.length === 0 && <p className="pp-muted">No database needed.</p>}
          {spec.entities.map((e) => (
            <div key={e.name} className="pp-entity">
              <strong>{e.label}</strong> <code>/api/{plural(e.name)}</code>
              <div className="pp-muted">{e.fields.map((f) => `${f.name}${f.required ? "*" : ""}: ${f.type}`).join(", ")}</div>
              <div className="pp-chips">{Object.entries(e.permissions).map(([a, l]) => <span key={a}>{a}: {l}</span>)}</div>
            </div>
          ))}
          {spec.features && spec.features.length > 0 && (<><h3>Features</h3><ul className="pp-list">{spec.features.map((f) => <li key={f}>{f}</li>)}</ul></>)}
          {spec.open_questions && spec.open_questions.length > 0 && (
            <><h3>Assumptions to review</h3><ul className="pp-list">{spec.open_questions.map((q) => <li key={q}>{q}</li>)}</ul></>
          )}
        </section>
      </div>
      <div className="pp-actions">
        <button className="aid-btn" onClick={onBack} disabled={busy}>Back</button>
        <button className="aid-btn aid-btn-primary" disabled={busy || !spec.name.trim()}
          onClick={() => onGenerate({ ...spec, pages: spec.pages.filter((p) => !excluded.has(p.route)) })}>
          {busy ? "Starting…" : "Generate application"}
        </button>
      </div>
    </div>
  );
}

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [projects, setProjects] = useState(null);
  const [total, setTotal] = useState(0);
  const [usage, setUsage] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [refUrl, setRefUrl] = useState("");
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, u] = await Promise.all([api.get("/api/projects?limit=24"), api.get("/api/usage")]);
      setProjects(p.projects);
      setTotal(p.total);
      setUsage(u);
    } catch (e) {
      setError(e.message);
      setProjects([]);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const makePlan = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api.post("/api/projects/plan", { prompt, referenceUrl: refUrl.trim() || undefined });
      setPlan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const generate = async (spec) => {
    setBusy(true);
    setError("");
    try {
      const data = await api.post("/api/projects", { spec, prompt, referenceUrl: refUrl.trim(), reference: plan.reference });
      navigate(`/studio/${data.project.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const blank = async () => {
    setBusy(true);
    try {
      const data = await api.post("/api/projects", { blank: true, name: "Untitled project" });
      navigate(`/studio/${data.project.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const loadMore = async () => {
    try {
      const p = await api.get(`/api/projects?limit=24&offset=${projects.length}`);
      setProjects((prev) => [...prev, ...p.projects]);
      setTotal(p.total);
    } catch (err) { setError(err.message); }
  };

  const remove = async (project) => {
    if (!window.confirm(`Delete "${project.name}" and all its versions? This cannot be undone.`)) return;
    try {
      await api.del(`/api/projects/${project.id}`);
      setProjects((ps) => ps.filter((p) => p.id !== project.id));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="pp">
      <div className="pp-top" role="banner">
        <Link to="/" className="pp-logo">AIDevs <span>Studio</span></Link>
        <div className="pp-top-right">
          {usage && usage.today && (
            <span className="aid-badge" title="Free-plan allowances for the last 24 hours (see Account)">
              {usage.dailyLimits.generate - usage.today.generate} generations · {usage.dailyLimits.modify - usage.today.modify} AI edits left today
            </span>
          )}
          <span className="pp-muted">{user && user.email}</span>
          {user && user.role === "admin" && <Link className="aid-btn aid-btn-sm" to="/admin">Admin</Link>}
          <Link className="aid-btn aid-btn-sm" to="/account">Account</Link>
          <Link className="aid-btn aid-btn-sm" to="/chatbot">Classic builder</Link>
          <button className="aid-btn aid-btn-sm" onClick={async () => { await logout(); navigate("/"); }}>Log out</button>
        </div>
      </div>

      <div className="pp-main" role="main">
        {error && <div className="aid-alert aid-alert-error" role="alert">{error}</div>}
        {usage && usage.aiCapacity && !usage.aiCapacity.available && (
          <div className="aid-alert aid-alert-info aid-capacity" role="status">
            The shared free AI capacity is busy right now, so new AI tasks are paused for about
            {" "}{Math.max(1, Math.round(usage.aiCapacity.retryAfterSeconds / 60))} minute(s). You can still open and edit your projects.
          </div>
        )}
        {usage && usage.projects >= usage.projectLimit && (
          <div className="aid-alert aid-alert-info" role="status">
            You have reached the free plan's {usage.projectLimit}-project limit. Delete a project to start a new one.
          </div>
        )}
        {!plan ? (
          <form className="pp-create" onSubmit={makePlan}>
            <h1>What do you want to build, {user ? user.firstName : ""}?</h1>
            <p className="pp-muted">Describe the idea once. AIDevs plans the pages, design system, database and API, then builds a full-stack app you can edit visually.</p>
            <textarea className="aid-textarea pp-prompt" rows={4} value={prompt} maxLength={4000}
              placeholder={EXAMPLES[0]} onChange={(e) => setPrompt(e.target.value)} aria-label="Describe your app" />
            <div className="pp-row">
              <input className="aid-input" value={refUrl} onChange={(e) => setRefUrl(e.target.value)}
                placeholder="Optional reference website, e.g. https://example.com" aria-label="Reference website URL" />
              <button className="aid-btn aid-btn-primary" type="submit" disabled={busy || prompt.trim().length < 8}>
                {busy ? "Planning…" : "Plan my app"}
              </button>
            </div>
            <div className="pp-examples">
              {EXAMPLES.map((ex) => <button type="button" key={ex} onClick={() => setPrompt(ex)}>{ex}</button>)}
            </div>
            <button type="button" className="pp-link" onClick={blank} disabled={busy}>or start from a blank project</button>
          </form>
        ) : (
          <SpecReview spec={plan.spec} reference={plan.reference} busy={busy}
            onChange={(spec) => setPlan({ ...plan, spec })} onBack={() => setPlan(null)} onGenerate={generate} />
        )}

        <section className="pp-projects">
          <h2>Your projects</h2>
          {projects === null && <div className="aid-spinner" />}
          {projects && projects.length === 0 && <p className="pp-muted">No projects yet.</p>}
          <div className="pp-grid">
            {(projects || []).map((p) => (
              <article key={p.id} className="pp-card">
                <div className="pp-card-swatch" style={{ background: p.primary || "#1f2937" }} />
                <div className="pp-card-body">
                  <h3>{p.name}</h3>
                  <p className="pp-muted">{p.pageCount} page(s) · updated {new Date(p.updatedAt || p.createdAt).toLocaleString()}</p>
                  <span className={`aid-badge ${p.status === "ready" ? "ok" : p.status === "failed" ? "err" : p.status === "partial" ? "warn" : "run"}`}>
                    {p.status === "partial" ? "partly built" : p.status}</span>
                </div>
                <div className="pp-card-actions">
                  <Link className="aid-btn aid-btn-primary aid-btn-sm" to={`/studio/${p.id}`}>Open</Link>
                  <button className="aid-btn aid-btn-sm aid-btn-danger" onClick={() => remove(p)}>Delete</button>
                </div>
              </article>
            ))}
          </div>
          {projects && projects.length < total && (
            <div className="pp-actions"><button className="aid-btn" onClick={loadMore}>Load more ({total - projects.length} more)</button></div>
          )}
        </section>
        <footer className="pp-legal"><Link to="/legal/terms">Terms</Link> · <Link to="/legal/privacy">Privacy</Link> ·
          {" "}<Link to="/legal/acceptable-use">Acceptable use</Link> · <Link to="/legal/ai-disclosure">AI disclosure</Link></footer>
      </div>
    </div>
  );
}
