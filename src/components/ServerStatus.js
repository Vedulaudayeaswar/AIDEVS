import React, { useEffect, useState } from "react";
import { onServerWaking } from "../lib/api";

// Global, non-blocking banner shown while the free-tier backend is waking up.
export default function ServerStatus() {
  const [waking, setWaking] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => onServerWaking(setWaking), []);
  useEffect(() => {
    if (!waking) { setSeconds(0); return undefined; }
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [waking]);

  if (!waking) return null;
  return (
    <div className="aid-wake" role="status" aria-live="polite">
      <div className="aid-spinner" />
      <div>
        <strong>Starting the AIDevs server…</strong>
        <span> AIDevs runs on free hosting that sleeps when idle; waking up can take up to a minute
          ({seconds}s). Your work is safe — this page will continue automatically.</span>
      </div>
    </div>
  );
}
