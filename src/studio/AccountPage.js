import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, apiFetch, setSession } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import "./ProjectsPage.css";

function Meter({ label, used, limit, format = (v) => v }) {
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  return (
    <div className="acc-meter">
      <div className="acc-meter-head"><span>{label}</span><span>{format(used)} / {format(limit)}</span></div>
      <div className="st-progress" style={{ width: "100%" }}><span style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export default function AccountPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [usage, setUsage] = useState(null);
  const [pw, setPw] = useState({ currentPassword: "", newPassword: "" });
  const [del, setDel] = useState({ password: "", confirm: "" });
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [busy, setBusy] = useState("");

  useEffect(() => { api.get("/api/usage").then(setUsage).catch((e) => setMsg({ type: "error", text: e.message })); }, []);
  const mb = (b) => `${(b / (1024 * 1024)).toFixed(1)} MB`;

  const changePassword = async (e) => {
    e.preventDefault();
    setBusy("pw");
    try {
      const data = await api.post("/api/auth/change-password", pw);
      setSession(data); // this device keeps a fresh session; all others are signed out
      setPw({ currentPassword: "", newPassword: "" });
      setMsg({ type: "info", text: "Password changed. All other devices were signed out." });
    } catch (err) { setMsg({ type: "error", text: err.message }); } finally { setBusy(""); }
  };

  const exportData = async () => {
    setBusy("export");
    try {
      const res = await apiFetch("/api/auth/export", { raw: true });
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url; a.download = "aidevs-account-data.json";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setMsg({ type: "error", text: err.message }); } finally { setBusy(""); }
  };

  const deleteAccount = async (e) => {
    e.preventDefault();
    if (!window.confirm("Permanently delete your account and ALL projects? This cannot be undone.")) return;
    setBusy("delete");
    try {
      await apiFetch("/api/auth/account", { method: "DELETE", body: del });
      setSession(null);
      navigate("/", { replace: true });
    } catch (err) { setMsg({ type: "error", text: err.message }); setBusy(""); }
  };

  return (
    <div className="pp">
      <div className="pp-top" role="banner">
        <Link to="/projects" className="pp-logo">AIDevs <span>Studio</span></Link>
        <div className="pp-top-right">
          <Link className="aid-btn aid-btn-sm" to="/projects">Projects</Link>
          <button className="aid-btn aid-btn-sm" onClick={async () => { await logout(); navigate("/"); }}>Log out</button>
        </div>
      </div>
      <div className="pp-main" role="main">
        <h1 className="acc-title">Account</h1>
        {msg.text && <div className={`aid-alert ${msg.type === "error" ? "aid-alert-error" : "aid-alert-info"}`} role="status">{msg.text}</div>}
        <section className="pp-review">
          <h3>Profile</h3>
          <p className="pp-muted">{user && `${user.firstName} ${user.lastName}`} · {user && user.email} · username <code>{user && user.username}</code></p>
        </section>
        <section className="pp-review">
          <h3>Usage &amp; limits (last 24 hours)</h3>
          <p className="pp-muted">AIDevs is free to use and runs on free-tier infrastructure, so fair-use limits apply. Allowances refill on a rolling 24-hour basis; failed or cancelled AI tasks are not counted.</p>
          {!usage ? <div className="aid-spinner" /> : (
            <div className="acc-grid">
              {usage.today && <Meter label="AI generations today" used={usage.today.generate} limit={usage.dailyLimits.generate} />}
              {usage.today && <Meter label="AI modifications today" used={usage.today.modify} limit={usage.dailyLimits.modify} />}
              {usage.today && <Meter label="Exports today" used={usage.today.export} limit={usage.dailyLimits.export} />}
              <Meter label="AI requests" used={usage.requests} limit={usage.requestLimit} />
              <Meter label="AI tokens" used={usage.tokens} limit={usage.tokenLimit} format={(v) => v.toLocaleString()} />
              <Meter label="Projects" used={usage.projects} limit={usage.projectLimit} />
              <Meter label="Running AI tasks" used={usage.activeJobs} limit={usage.jobLimit} />
              <Meter label="Upload storage" used={usage.storageBytes} limit={usage.storageLimitBytes} format={mb} />
            </div>
          )}
        </section>
        <section className="pp-review">
          <h3>Change password</h3>
          <form className="acc-form" onSubmit={changePassword}>
            <label className="aid-label" htmlFor="cur-pw">Current password</label>
            <input id="cur-pw" className="aid-input" type="password" autoComplete="current-password" required
              value={pw.currentPassword} onChange={(e) => setPw({ ...pw, currentPassword: e.target.value })} />
            <label className="aid-label" htmlFor="new-pw">New password (8+ chars, letter, number, symbol)</label>
            <input id="new-pw" className="aid-input" type="password" autoComplete="new-password" required minLength={8}
              value={pw.newPassword} onChange={(e) => setPw({ ...pw, newPassword: e.target.value })} />
            <button className="aid-btn aid-btn-primary" disabled={busy === "pw"}>{busy === "pw" ? "Saving…" : "Change password"}</button>
          </form>
        </section>
        <section className="pp-review">
          <h3>Your data</h3>
          <p className="pp-muted">Download everything AIDevs stores about you (profile, projects, versions, conversations, AI usage) as JSON. Each project can also be exported as runnable code from the Studio.</p>
          <div><button className="aid-btn" onClick={exportData} disabled={busy === "export"}>{busy === "export" ? "Preparing…" : "Download my data"}</button></div>
        </section>
        <section className="pp-review acc-danger">
          <h3>Delete account</h3>
          <p className="pp-muted">Deletes your account, projects, versions, assets and conversations immediately. Aggregated, anonymised AI usage counts are kept for capacity planning. See the <Link to="/legal/data-retention">data retention policy</Link>.</p>
          <form className="acc-form" onSubmit={deleteAccount}>
            <label className="aid-label" htmlFor="del-pw">Password</label>
            <input id="del-pw" className="aid-input" type="password" autoComplete="current-password" required
              value={del.password} onChange={(e) => setDel({ ...del, password: e.target.value })} />
            <label className="aid-label" htmlFor="del-confirm">Type DELETE to confirm</label>
            <input id="del-confirm" className="aid-input" required value={del.confirm} onChange={(e) => setDel({ ...del, confirm: e.target.value })} />
            <button className="aid-btn aid-btn-danger" disabled={busy === "delete" || del.confirm !== "DELETE"}>
              {busy === "delete" ? "Deleting…" : "Permanently delete my account"}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
