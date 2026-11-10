import React, { useEffect, useMemo, useState } from "react";
import { CONTAINER_TYPES, pathTo } from "./treeOps";

const ICONS = {
  page: "▤", section: "▭", container: "▢", heading: "H", text: "¶", button: "⬚", link: "🔗", image: "🖼",
  icon: "★", divider: "—", form: "✎", input: "⌨", textarea: "⌨", select: "▾", collection: "≣",
};

function LayerRow({ node, depth, selectedId, hoveredId, expanded, toggle, onSelect, onHover, onRename,
  onDrop, dragState, setDragState }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(node.name);
  const hasKids = (node.children || []).length > 0;
  const isOpen = expanded.has(node.id);
  const draggable = depth > 0 && !node.shared;
  const isContainer = CONTAINER_TYPES.has(node.type) && node.type !== "collection";

  useEffect(() => setName(node.name), [node.name]);

  const dropPosition = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    if (isContainer && y > rect.height * 0.3 && y < rect.height * 0.7) return "inside";
    return y < rect.height / 2 ? "before" : "after";
  };

  return (
    <>
      <div
        className={`st-layer ${selectedId === node.id ? "selected" : ""} ${hoveredId === node.id ? "hovered" : ""} ${
          dragState && dragState.over === node.id ? `drop-${dragState.position}` : ""}`}
        style={{ paddingLeft: 6 + depth * 14 }}
        role="treeitem"
        aria-selected={selectedId === node.id}
        aria-expanded={hasKids ? isOpen : undefined}
        tabIndex={selectedId === node.id ? 0 : -1}
        draggable={draggable && !editing}
        onDragStart={(e) => { e.dataTransfer.effectAllowed = "move"; setDragState({ id: node.id }); }}
        onDragOver={(e) => {
          if (!dragState || dragState.id === node.id) return;
          e.preventDefault();
          const position = dropPosition(e);
          if (dragState.over !== node.id || dragState.position !== position) setDragState({ ...dragState, over: node.id, position });
        }}
        onDragLeave={() => dragState && dragState.over === node.id && setDragState({ id: dragState.id })}
        onDrop={(e) => { e.preventDefault(); if (dragState) onDrop(dragState.id, node.id, dropPosition(e)); setDragState(null); }}
        onDragEnd={() => setDragState(null)}
        onClick={() => onSelect(node.id)}
        onMouseEnter={() => onHover(node.id)}
        onMouseLeave={() => onHover(null)}
        onDoubleClick={() => depth > 0 && setEditing(true)}
      >
        <button type="button" className="st-layer-toggle" tabIndex={-1} aria-label={isOpen ? "Collapse" : "Expand"}
          onClick={(e) => { e.stopPropagation(); if (hasKids) toggle(node.id); }}>
          {hasKids ? (isOpen ? "▾" : "▸") : ""}
        </button>
        <span className="st-layer-icon" aria-hidden="true">{ICONS[node.type] || "•"}</span>
        {editing ? (
          <input className="aid-input st-layer-input" value={name} autoFocus maxLength={80}
            onChange={(e) => setName(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onBlur={() => { setEditing(false); if (name.trim() && name !== node.name) onRename(node.id, name.trim()); }}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
              if (e.key === "Escape") { setName(node.name); setEditing(false); }
            }} />
        ) : (
          <span className="st-layer-name">{node.name}</span>
        )}
        {node.shared && <span className="st-layer-tag" title="Shared across all pages">shared</span>}
      </div>
      {hasKids && isOpen && node.children.map((child) => (
        <LayerRow key={child.id} node={child} depth={depth + 1} selectedId={selectedId} hoveredId={hoveredId}
          expanded={expanded} toggle={toggle} onSelect={onSelect} onHover={onHover} onRename={onRename}
          onDrop={onDrop} dragState={dragState} setDragState={setDragState} />
      ))}
    </>
  );
}

export default function LayersPanel({ tree, selectedId, hoveredId, onSelect, onHover, onRename, onMove,
  onDuplicate, onDelete, onGroup, onUngroup }) {
  const [expanded, setExpanded] = useState(() => new Set(tree ? [tree.id, ...(tree.children || []).map((c) => c.id)] : []));
  const [dragState, setDragState] = useState(null);
  const rootId = tree ? tree.id : null;

  // Pages load asynchronously: expand the root and its sections once a page arrives.
  useEffect(() => {
    if (!tree) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      next.add(tree.id);
      (tree.children || []).forEach((c) => next.add(c.id));
      return next;
    });
  }, [rootId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reveal the selection (e.g. when clicked in the canvas).
  const path = useMemo(() => (tree && selectedId ? pathTo(tree, selectedId) : null), [tree, selectedId]);
  useEffect(() => {
    if (!path) return;
    setExpanded((prev) => {
      const missing = path.slice(0, -1).filter((n) => !prev.has(n.id));
      if (!missing.length) return prev;
      const next = new Set(prev);
      missing.forEach((n) => next.add(n.id));
      return next;
    });
    const el = document.querySelector(".st-layer.selected");
    if (el) el.scrollIntoView({ block: "nearest" });
  }, [path]);

  if (!tree) return null;
  const toggle = (id) => setExpanded((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const sel = selectedId && selectedId !== tree.id;

  return (
    <div className="st-layers">
      <div className="st-layer-actions">
        <button className="aid-icon-btn" title="Duplicate (Ctrl+D)" disabled={!sel} onClick={onDuplicate}>⧉</button>
        <button className="aid-icon-btn" title="Group (Ctrl+G)" disabled={!sel} onClick={onGroup}>⊞</button>
        <button className="aid-icon-btn" title="Ungroup (Ctrl+Shift+G)" disabled={!sel} onClick={onUngroup}>⊟</button>
        <button className="aid-icon-btn" title="Delete (Del)" disabled={!sel} onClick={onDelete}>🗑</button>
        <span className="st-hint">Drag to reorder · double-click to rename</span>
      </div>
      <div role="tree" aria-label="Layers" className="st-layer-tree">
        <LayerRow node={tree} depth={0} selectedId={selectedId} hoveredId={hoveredId} expanded={expanded}
          toggle={toggle} onSelect={onSelect} onHover={onHover} onRename={onRename} onDrop={onMove}
          dragState={dragState} setDragState={setDragState} />
      </div>
    </div>
  );
}
