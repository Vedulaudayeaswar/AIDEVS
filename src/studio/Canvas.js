import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "../lib/api";

export const DEVICES = {
  desktop: { label: "Desktop", width: 1440, breakpoint: "base", icon: "🖥" },
  laptop: { label: "Laptop", width: 1280, breakpoint: "base", icon: "💻" },
  tablet: { label: "Tablet", width: 834, breakpoint: "tablet", icon: "▭" },
  mobile: { label: "Mobile", width: 390, breakpoint: "mobile", icon: "📱" },
};

const ALLOWED_TYPES = new Set(["ready", "select", "hover", "text-edit", "resize", "move", "key", "navigate",
  "submit", "console", "scrolled", "rerender"]);

// Renders the compiled page inside an opaque-origin sandbox (sandbox="allow-scripts"
// without allow-same-origin): the generated site cannot read the studio's
// storage, cookies or DOM. All interaction flows through validated postMessage.
export default function Canvas({ projectId, pageId, tree, device, zoom, mode, selectedId, hoveredId,
  renderKey, onMessage, onError }) {
  const iframeRef = useRef(null);
  const wrapRef = useRef(null);
  const scrollY = useRef(0);
  const [html, setHtml] = useState("");
  const [fitScale, setFitScale] = useState(1);
  const [loading, setLoading] = useState(false);
  const latest = useRef({ selectedId, onMessage });
  latest.current = { selectedId, onMessage };

  // Compile the (possibly unsaved) tree on the server - the single source of truth
  // for HTML/CSS, identical to what the export ships.
  useEffect(() => {
    if (!tree || !pageId) return undefined;
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      api.post(`/api/projects/${projectId}/preview`, { pageId, tree, mode })
        .then((data) => { if (!cancelled) setHtml(data.html); })
        .catch((err) => { if (!cancelled) onError(err.message); })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, 120);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [projectId, pageId, tree, mode, renderKey, onError]);

  useEffect(() => { scrollY.current = 0; }, [pageId]);

  useEffect(() => {
    function handle(event) {
      const frame = iframeRef.current;
      if (!frame || event.source !== frame.contentWindow) return; // only our canvas
      const msg = event.data;
      if (!msg || msg.source !== "aidevs-canvas" || !ALLOWED_TYPES.has(msg.type)) return;
      if (msg.type === "ready") {
        post({ type: "scroll", y: scrollY.current });
        if (latest.current.selectedId) post({ type: "select", id: latest.current.selectedId });
      }
      if (msg.type === "scrolled") { scrollY.current = Number(msg.y) || 0; return; }
      latest.current.onMessage(msg, post);
    }
    window.addEventListener("message", handle);
    return () => window.removeEventListener("message", handle);
  }, []);

  function post(message) {
    const frame = iframeRef.current;
    // Opaque-origin frames can only be addressed with "*"; payloads hold no secrets.
    if (frame && frame.contentWindow) frame.contentWindow.postMessage({ ...message, source: "aidevs-studio" }, "*");
  }

  useEffect(() => { post({ type: "select", id: selectedId, scroll: true }); }, [selectedId]);
  useEffect(() => { post({ type: "hover", id: hoveredId }); }, [hoveredId]);

  const width = DEVICES[device].width;
  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const update = () => setFitScale(Math.min(1, (el.clientWidth - 48) / width));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [width]);
  const scale = zoom === "fit" ? fitScale : zoom;

  return (
    <div className="st-canvas-wrap" ref={wrapRef}>
      <div className="st-canvas-stage" style={{ width: width * scale, height: "100%" }}>
        <div className="st-device-label">{DEVICES[device].label} · {width}px · {Math.round(scale * 100)}%
          {loading && <span className="st-dot" aria-label="Rendering" />}</div>
        <iframe
          ref={iframeRef}
          title="Website canvas"
          className="st-iframe"
          sandbox="allow-scripts"
          referrerPolicy="no-referrer"
          srcDoc={html}
          style={{ width, height: `calc((100% - 22px) / ${scale})`, transform: `scale(${scale})` }}
        />
      </div>
    </div>
  );
}
