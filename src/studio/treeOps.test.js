import {
  duplicateNode, findNode, groupNode, moveNode, removeNode, ungroupNode, updateProps, updateStyles,
} from "./treeOps";

const leaf = (id, type = "text") => ({ id, type, name: id, props: { text: id }, styles: { base: {}, tablet: {}, mobile: {} }, children: [] });
const box = (id, children, extra = {}) => ({ id, type: "container", name: id, props: {}, styles: { base: {}, tablet: {}, mobile: {} }, children, ...extra });

const tree = () => ({
  id: "root", type: "page", name: "Page", props: {}, styles: {}, children: [
    { ...box("header", [leaf("logo", "link")]), type: "section", shared: "header" },
    { ...box("hero", [leaf("h1", "heading"), leaf("cta", "button")]), type: "section" },
    box("grid", [leaf("a"), leaf("b")]),
    { ...box("footer", [leaf("copy")]), type: "section", shared: "footer" },
  ],
});

test("updates are immutable and target one node", () => {
  const t = tree();
  const next = updateProps(t, "h1", { text: "Hello" });
  expect(findNode(next, "h1").props.text).toBe("Hello");
  expect(findNode(t, "h1").props.text).toBe("h1");
  expect(next.children[2]).toBe(t.children[2]); // untouched branches are shared
});

test("desktop style edits do not touch mobile overrides", () => {
  let t = updateStyles(tree(), "h1", "mobile", { fontSize: "32px" });
  t = updateStyles(t, "h1", "base", { fontSize: "64px", color: "#fff" });
  expect(findNode(t, "h1").styles.mobile).toEqual({ fontSize: "32px" });
  t = updateStyles(t, "h1", "base", { color: "" });
  expect(findNode(t, "h1").styles.base).toEqual({ fontSize: "64px" });
});

test("move reorders and reparents, rejects invalid moves", () => {
  const t = tree();
  const moved = moveNode(t, "cta", "h1", "before");
  expect(findNode(moved, "hero").children.map((c) => c.id)).toEqual(["cta", "h1"]);
  const into = moveNode(t, "a", "hero", "inside");
  expect(findNode(into, "hero").children.map((c) => c.id)).toEqual(["h1", "cta", "a"]);
  expect(findNode(into, "grid").children.map((c) => c.id)).toEqual(["b"]);
  expect(moveNode(t, "hero", "h1", "inside")).toBeNull(); // into own descendant / non-container
  expect(moveNode(t, "grid", "header", "before")).toBeNull(); // header stays first
  expect(moveNode(t, "header", "grid", "after")).toBeNull(); // shared regions are fixed
});

test("delete, duplicate, group and ungroup", () => {
  const t = tree();
  expect(findNode(removeNode(t, "grid"), "grid")).toBeNull();
  const { tree: dup, newId } = duplicateNode(t, "a");
  expect(findNode(dup, "grid").children.map((c) => c.id)).toEqual(["a", newId, "b"]);
  expect(newId).not.toBe("a");
  const { tree: grouped, newId: gid } = groupNode(t, "a");
  expect(findNode(grouped, gid).children[0].id).toBe("a");
  const { tree: ungrouped } = ungroupNode(grouped, gid);
  expect(findNode(ungrouped, "grid").children.map((c) => c.id)).toEqual(["a", "b"]);
});
