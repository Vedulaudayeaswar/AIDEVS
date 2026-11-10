import React, { useEffect, useRef, useState } from "react";

const SUGGEST_SELECTION = ["Make this more premium", "Improve the spacing and hierarchy", "Make it accessible", "Rewrite the copy to be punchier"];
const SUGGEST_PROJECT = ["Add a wishlist feature", "Add a pricing page", "Add a testimonials section to the home page", "Switch to a dark colour scheme"];

export default function AssistantPanel({ messages, onSend, busy, activeRun, selection, onClearSelection, onCancel }) {
  const [text, setText] = useState("");
  const [useSelection, setUseSelection] = useState(true);
  const endRef = useRef(null);
  useEffect(() => { if (endRef.current) endRef.current.scrollIntoView({ block: "end" }); }, [messages, activeRun]);

  const target = selection && useSelection ? selection : null;
  const submit = (value) => {
    const message = (value ?? text).trim();
    if (!message || busy) return;
    onSend(message, target);
    setText("");
  };

  return (
    <div className="st-assistant">
      <div className="st-messages" aria-live="polite">
        {messages.length === 0 && <p className="st-note">Ask for changes in plain language. With an element selected, I edit just that element; otherwise I plan project-wide changes (pages, data models, API, navigation).</p>}
        {messages.map((m) => (
          <div key={m.id} className={`st-msg ${m.role}`}>
            {m.content.split("\n").map((line, i) => <p key={i}>{line}</p>)}
          </div>
        ))}
        {activeRun && (
          <div className="st-msg assistant run">
            <div className="st-progress"><span style={{ width: `${activeRun.progress}%` }} /></div>
            <p>{activeRun.message || "Working…"}</p>
            {onCancel && <button type="button" className="st-link" onClick={onCancel}>Cancel</button>}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="st-composer">
        {selection && (
          <div className="st-target">
            <label><input type="checkbox" checked={useSelection} onChange={(e) => setUseSelection(e.target.checked)} />
              Edit selected: <strong>{selection.name}</strong></label>
            <button type="button" className="st-link" onClick={onClearSelection}>clear</button>
          </div>
        )}
        <div className="st-suggest">
          {(target ? SUGGEST_SELECTION : SUGGEST_PROJECT).map((s) => (
            <button key={s} type="button" disabled={busy} onClick={() => submit(s)}>{s}</button>
          ))}
        </div>
        <form onSubmit={(e) => { e.preventDefault(); submit(); }}>
          <textarea className="aid-textarea" rows={3} maxLength={4000} value={text} disabled={busy}
            placeholder={target ? `Describe a change to "${selection.name}"…` : "Describe a change to your app…"}
            onChange={(e) => setText(e.target.value)} aria-label="Message to AI assistant"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
          <button className="aid-btn aid-btn-primary" disabled={busy || !text.trim()}>{busy ? "Working…" : "Send"}</button>
        </form>
      </div>
    </div>
  );
}
