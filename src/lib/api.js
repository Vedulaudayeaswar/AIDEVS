// Central API client: attaches the in-memory access token, transparently
// refreshes it with the rotating refresh token on 401, and normalizes errors.
import API_URL from "../config";

const REFRESH_KEY = "aidevs_refresh";
let accessToken = null;
let refreshPromise = null;
const listeners = new Set();
const wakeListeners = new Set();

// ---- Cold starts: free hosting sleeps when idle and takes ~1 minute to wake. ----
// Safe (idempotent) requests are retried with backoff for up to WAKE_BUDGET_MS while
// subscribers (the ServerStatus banner) are told the server is starting.
const WAKE_BUDGET_MS = 100000;
const RETRY_STATUSES = new Set([502, 503, 504]);
let waking = false;

export function onServerWaking(fn) {
  wakeListeners.add(fn);
  fn(waking);
  return () => wakeListeners.delete(fn);
}

function setWaking(value) {
  if (waking === value) return;
  waking = value;
  wakeListeners.forEach((fn) => fn(value));
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchWithWake(url, init, { retry = true } = {}) {
  const started = Date.now();
  let delay = 1500;
  for (;;) {
    let res = null;
    try {
      res = await fetch(url, init);
    } catch (err) {
      res = null; // network error: server asleep / starting / offline
    }
    const retryable = !res || (RETRY_STATUSES.has(res.status) && !(await isAppError(res)));
    if (!retryable || !retry || Date.now() - started > WAKE_BUDGET_MS) {
      setWaking(false);
      if (!res) throw new ApiError("Cannot reach the AIDevs server. It may be starting up - please try again in a moment.", 0);
      return res;
    }
    setWaking(true);
    await sleep(delay);
    delay = Math.min(delay * 1.6, 8000);
  }
}

/** Wake a sleeping free-tier server before a non-idempotent request (login, register). */
export async function wakeServer() {
  await fetchWithWake(`${API_URL}/api/health/live`, { method: "GET" });
}

// 503s produced by the app itself (AI capacity paused, DB waking) carry a JSON `code`;
// those are shown to the user instead of being retried silently (except db_unavailable).
async function isAppError(res) {
  try {
    const data = await res.clone().json();
    return Boolean(data && data.code && data.code !== "db_unavailable");
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data || {};
  }
}

function readRefresh() {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

function writeRefresh(token) {
  try {
    if (token) localStorage.setItem(REFRESH_KEY, token);
    else localStorage.removeItem(REFRESH_KEY);
    // v1 keys are obsolete; remove them so old JWTs are not left in storage.
    localStorage.removeItem("aidevs_token");
    localStorage.removeItem("aidevs_username");
  } catch {
    /* storage unavailable (private mode) - session lasts for this tab only */
  }
}

export function setSession(payload) {
  accessToken = payload ? payload.accessToken : null;
  writeRefresh(payload ? payload.refreshToken : null);
  listeners.forEach((fn) => fn(payload ? payload.user : null));
}

export function onSessionChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function hasStoredSession() {
  return Boolean(readRefresh());
}

export async function refreshSession() {
  const token = readRefresh();
  if (!token) return null;
  if (!refreshPromise) {
    // Refresh is safe to retry: the server only rotates the token when it succeeds.
    refreshPromise = fetchWithWake(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: token }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          // Only a definitive rejection ends the session; network errors keep it.
          if (res.status === 401) setSession(null);
          throw new ApiError(data.error || "Session expired", res.status, data);
        }
        setSession(data);
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function parse(res) {
  const type = res.headers.get("Content-Type") || "";
  if (type.includes("application/json")) return res.json().catch(() => ({}));
  return null;
}

export async function apiFetch(path, { method = "GET", body, raw = false, form, retry = true } = {}) {
  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  // Only idempotent GETs are retried automatically during a cold start; writes are never
  // replayed (no duplicate projects/charges against quotas), the UI asks the user to retry.
  const res = await fetchWithWake(`${API_URL}${path}`, { method, headers, body: payload }, { retry: method === "GET" });
  if (res.status === 401 && retry && readRefresh()) {
    try {
      await refreshSession();
      return apiFetch(path, { method, body, raw, form, retry: false });
    } catch {
      /* fall through to the 401 below */
    }
  }
  if (raw && res.ok) return res;
  const data = await parse(res);
  if (!res.ok) {
    throw new ApiError((data && data.error) || `Request failed (${res.status})`, res.status, data);
  }
  return data;
}

export const api = {
  get: (p) => apiFetch(p),
  post: (p, body) => apiFetch(p, { method: "POST", body: body || {} }),
  put: (p, body) => apiFetch(p, { method: "PUT", body }),
  patch: (p, body) => apiFetch(p, { method: "PATCH", body }),
  del: (p) => apiFetch(p, { method: "DELETE" }),
};

export function getAccessToken() {
  return accessToken;
}
