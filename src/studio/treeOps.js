// Pure, immutable operations on the AIDevs component tree.
// Every editor action (canvas, layers, inspector, AI) goes through these, so
// undo/redo is just a stack of tree values and the server receives a tree.

export const CONTAINER_TYPES = new Set(["page", "section", "container", "form", "collection"]);

export function newId() {
  const bytes = new Uint8Array(4);
  const cryptoObj = typeof window !== "undefined" ? window.crypto || window.msCrypto : null;
  if (cryptoObj && cryptoObj.getRandomValues) cryptoObj.getRandomValues(bytes);
  else for (let i = 0; i < 4; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  return "n_" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function findNode(tree, id) {
  if (!tree) return null;
  if (tree.id === id) return tree;
  for (const child of tree.children || []) {
    const hit = findNode(child, id);
    if (hit) return hit;
  }
  return null;
}

// Path of nodes from root to `id` (inclusive), or null.
export function pathTo(tree, id, acc = []) {
  if (!tree) return null;
  const next = [...acc, tree];
  if (tree.id === id) return next;
  for (const child of tree.children || []) {
    const hit = pathTo(child, id, next);
    if (hit) return hit;
  }
  return null;
}

export function parentOf(tree, id) {
  const path = pathTo(tree, id);
  return path && path.length > 1 ? path[path.length - 2] : null;
}

export function isDescendant(tree, ancestorId, id) {
  const anc = findNode(tree, ancestorId);
  return Boolean(anc && findNode(anc, id));
}

export function mapNode(tree, id, fn) {
  if (tree.id === id) return fn(tree);
  if (!tree.children || !tree.children.length) return tree;
  let changed = false;
  const children = tree.children.map((c) => {
    const next = mapNode(c, id, fn);
    if (next !== c) changed = true;
    return next;
  });
  return changed ? { ...tree, children } : tree;
}

export function updateProps(tree, id, patch) {
  return mapNode(tree, id, (n) => ({ ...n, props: { ...(n.props || {}), ...patch } }));
}

export function updateNode(tree, id, patch) {
  return mapNode(tree, id, (n) => ({ ...n, ...patch }));
}

// Set (or clear with "" / null) style props for one breakpoint.
export function updateStyles(tree, id, breakpoint, patch) {
  return mapNode(tree, id, (n) => {
    const styles = { base: {}, tablet: {}, mobile: {}, ...(n.styles || {}) };
    const bp = { ...(styles[breakpoint] || {}) };
    Object.entries(patch).forEach(([k, v]) => {
      if (v === "" || v === null || v === undefined) delete bp[k];
      else bp[k] = v;
    });
    return { ...n, styles: { ...styles, [breakpoint]: bp } };
  });
}

export function removeNode(tree, id) {
  if (!tree.children) return tree;
  const filtered = tree.children.filter((c) => c.id !== id);
  if (filtered.length !== tree.children.length) return { ...tree, children: filtered };
  let changed = false;
  const children = tree.children.map((c) => {
    const next = removeNode(c, id);
    if (next !== c) changed = true;
    return next;
  });
  return changed ? { ...tree, children } : tree;
}

export function cloneWithNewIds(node) {
  const { shared, ...rest } = node; // a duplicate is never the shared header/footer
  return { ...rest, id: newId(), children: (node.children || []).map(cloneWithNewIds) };
}

// Insert `node` relative to target: "before" | "after" | "inside" (appended).
export function insertNode(tree, targetId, position, node) {
  if (position === "inside") {
    return mapNode(tree, targetId, (t) => ({ ...t, children: [...(t.children || []), node] }));
  }
  const parent = parentOf(tree, targetId);
  if (!parent) return tree;
  return mapNode(tree, parent.id, (p) => {
    const idx = p.children.findIndex((c) => c.id === targetId);
    const children = [...p.children];
    children.splice(position === "before" ? idx : idx + 1, 0, node);
    return { ...p, children };
  });
}

// Returns the new tree, or null if the move is structurally invalid.
export function moveNode(tree, id, targetId, position) {
  if (id === targetId || id === tree.id) return null;
  if (isDescendant(tree, id, targetId)) return null; // into itself
  const node = findNode(tree, id);
  const target = findNode(tree, targetId);
  if (!node || !target || node.shared) return null;
  if (position === "inside" && !CONTAINER_TYPES.has(target.type)) return null;
  if (position === "inside" && target.type === "collection") return null;
  if (position !== "inside") {
    if (target.id === tree.id) return null;
    const parent = parentOf(tree, targetId);
    if (target.shared && parent && parent.id === tree.id) {
      // Keep header first / footer last.
      if ((target.shared === "header" && position === "before") || (target.shared === "footer" && position === "after")) {
        return null;
      }
    }
    if (parent && parent.type === "collection") return null;
  }
  if (node.type === "section" && position === "inside" && target.type !== "page") {
    // sections may nest in containers too; allowed
  }
  const without = removeNode(tree, id);
  return insertNode(without, targetId, position, node);
}

export function duplicateNode(tree, id) {
  const node = findNode(tree, id);
  if (!node || id === tree.id || node.shared) return { tree, newId: null };
  const parent = parentOf(tree, id);
  if (parent && parent.type === "collection") return { tree, newId: null };
  const copy = cloneWithNewIds(node);
  return { tree: insertNode(tree, id, "after", copy), newId: copy.id };
}

// Wrap a node in a new container ("group"), or unwrap a container ("ungroup").
export function groupNode(tree, id) {
  const node = findNode(tree, id);
  if (!node || id === tree.id || node.shared) return { tree, newId: null };
  const group = {
    id: newId(), type: "container", name: "Group", tag: "div", props: {},
    styles: { base: { display: "flex", flexDirection: "column", gap: "12px" }, tablet: {}, mobile: {} },
    children: [node],
  };
  const replaced = mapNode(tree, parentOf(tree, id).id, (p) => ({
    ...p, children: p.children.map((c) => (c.id === id ? group : c)),
  }));
  return { tree: replaced, newId: group.id };
}

export function ungroupNode(tree, id) {
  const node = findNode(tree, id);
  const parent = parentOf(tree, id);
  if (!node || !parent || node.type !== "container" || node.shared) return { tree, newId: null };
  const replaced = mapNode(tree, parent.id, (p) => ({
    ...p, children: p.children.flatMap((c) => (c.id === id ? c.children || [] : [c])),
  }));
  return { tree: replaced, newId: (node.children && node.children[0] && node.children[0].id) || parent.id };
}

export function replaceNode(tree, id, next) {
  return mapNode(tree, id, (old) => ({ ...next, id: old.id, ...(old.shared ? { shared: old.shared } : {}) }));
}

export function walk(tree, fn, depth = 0, parent = null) {
  fn(tree, depth, parent);
  (tree.children || []).forEach((c) => walk(c, fn, depth + 1, tree));
}
