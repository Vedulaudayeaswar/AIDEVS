import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import API_URL from "../config";
import { ApiError, apiFetch, getAccessToken, hasStoredSession, onSessionChange, refreshSession, setSession, wakeServer } from "../lib/api";

const AuthContext = createContext(null);

async function authRequest(path, body) {
  let res;
  await wakeServer(); // free hosting may be asleep: wait for it instead of failing the login
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the AIDevs server. Please try again.", 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || "Request failed", res.status, data);
  return data;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "restoring" while we exchange the stored refresh token after a page reload.
  const [status, setStatus] = useState(hasStoredSession() ? "restoring" : "anonymous");

  useEffect(() => onSessionChange((u) => {
    setUser(u);
    setStatus(u ? "authenticated" : "anonymous");
  }), []);

  useEffect(() => {
    if (!hasStoredSession()) return;
    refreshSession().catch((err) => {
      // Keep the stored session on network errors; the user can retry.
      setStatus(err.status === 401 ? "anonymous" : "offline");
    });
  }, []);

  const login = useCallback(async (identifier, password) => {
    const data = await authRequest("/api/auth/login", { identifier, password });
    setSession(data);
    return data.user;
  }, []);

  const register = useCallback(async (details) => {
    const data = await authRequest("/api/auth/register", details);
    setSession(data);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    let refreshToken = null;
    try {
      refreshToken = localStorage.getItem("aidevs_refresh");
    } catch {
      /* ignore */
    }
    try {
      if (getAccessToken() || refreshToken) {
        await apiFetch("/api/auth/logout", { method: "POST", body: { refreshToken }, retry: false });
      }
    } catch {
      /* server-side revoke failed; still clear locally */
    }
    setSession(null);
  }, []);

  const retry = useCallback(() => {
    setStatus("restoring");
    refreshSession().catch((err) => setStatus(err.status === 401 ? "anonymous" : "offline"));
  }, []);

  const value = useMemo(() => ({ user, status, login, register, logout, retry }),
    [user, status, login, register, logout, retry]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function RequireAuth({ children }) {
  const { status, retry } = useAuth();
  const location = useLocation();
  if (status === "restoring") {
    return <div className="aid-fullscreen-msg"><div className="aid-spinner" />Restoring your session…</div>;
  }
  if (status === "offline") {
    return (
      <div className="aid-fullscreen-msg">
        <p>We couldn't reach the AIDevs server to restore your session.</p>
        <button className="aid-btn aid-btn-primary" onClick={retry}>Try again</button>
      </div>
    );
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}
