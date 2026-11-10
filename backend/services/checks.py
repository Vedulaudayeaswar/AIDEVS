"""Testing / QA agent: deterministic checks over the project source of truth.

These are real checks (no LLM opinions): API contract consistency between
forms/collections and entities, link integrity, accessibility (alt text,
heading order, labels, WCAG contrast), SEO, responsive pitfalls, permission
safety, and a syntax compile of every generated backend Python file.
"""
import re

from services.export_backend import backend_files
from services.schema import BINDING_RE, walk

VAR_RE = re.compile(r"var\(--color-([a-z0-9-]+)\)")


def _hex_to_rgb(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) not in (6, 8) or not re.fullmatch(r"[0-9a-fA-F]+", value):
        return None
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def resolve_color(value, tokens):
    if not isinstance(value, str):
        return None
    m = VAR_RE.fullmatch(value.strip())
    if m:
        name = re.sub(r"-([a-z])", lambda x: x.group(1).upper(), m.group(1))
        value = tokens.get("colors", {}).get(name, "")
    return _hex_to_rgb(value) if value.strip().startswith("#") else None


def run_checks(project, pages, entities):
    tokens = project.tokens or {}
    entity_map = {e.name: e for e in entities}
    routes = {p.route for p in pages}
    issues = []

    def add(severity, category, message, route=None, node=None):
        issues.append({"severity": severity, "category": category, "message": message,
                       "route": route, "nodeId": node})

    layout = project.layout or {}
    trees = [(p.route, p.tree, p) for p in pages]
    if layout.get("header"):
        trees.append(("(shared header)", layout["header"], None))
    if layout.get("footer"):
        trees.append(("(shared footer)", layout["footer"], None))

    anchors = set()
    for _route, tree, _p in trees:
        for node, _ in walk(tree):
            if node.get("props", {}).get("anchor"):
                anchors.add(node["props"]["anchor"])

    for route, tree, page in trees:
        levels = []
        for node, _parent in walk(tree):
            t, p, nid = node["type"], node.get("props", {}), node["id"]
            base = node.get("styles", {}).get("base", {})
            mobile = node.get("styles", {}).get("mobile", {})
            # --- contracts ---------------------------------------------------
            if t == "form":
                ent_name = p.get("entity")
                if ent_name in ("auth_login", "auth_register"):
                    pass
                elif not ent_name or ent_name not in entity_map:
                    add("error", "contract", f"Form '{node['name']}' submits to unknown data model "
                        f"'{ent_name}'. Bind it to an existing model.", route, nid)
                else:
                    ent = entity_map[ent_name]
                    names = {c.get("props", {}).get("name") for c, _ in walk(node)
                             if c["type"] in ("input", "textarea", "select")}
                    fields = {f["name"]: f for f in ent.fields}
                    for missing in [f for f, d in fields.items() if d["required"] and f not in names]:
                        add("error", "contract", f"Form '{node['name']}' is missing required field "
                            f"'{missing}' of {ent.label}.", route, nid)
                    for extra in names - set(fields) - {None}:
                        add("warning", "contract", f"Field '{extra}' in form '{node['name']}' is not part "
                            f"of {ent.label} and will be ignored by the API.", route, nid)
                    if ent.permissions.get("create") not in ("public",):
                        add("info", "contract", f"Form '{node['name']}' requires a signed-in user "
                            f"({ent.permissions.get('create')}) to submit.", route, nid)
            if t == "collection":
                ent = entity_map.get(p.get("entity"))
                if not ent:
                    add("error", "contract", f"Collection '{node['name']}' reads unknown data model "
                        f"'{p.get('entity')}'.", route, nid)
                else:
                    unknown = _bindings(node) - {f["name"] for f in ent.fields}
                    for b in sorted(unknown):
                        add("error", "contract", f"Collection template uses '{{{{{b}}}}}' but {ent.label} "
                            f"has no such field.", route, nid)
            # --- links -----------------------------------------------------
            href = p.get("href")
            if isinstance(href, str) and not BINDING_RE.search(href):
                if href.startswith("/") and href.split("#")[0].split("?")[0] not in routes:
                    add("error", "links", f"Link '{p.get('text', '')}' points to missing page {href}.", route, nid)
                elif href.startswith("#") and len(href) > 1 and href[1:] not in anchors:
                    add("warning", "links", f"Anchor link {href} has no matching section anchor.", route, nid)
                elif href.startswith("http://"):
                    add("warning", "security", f"Insecure http:// link {href}.", route, nid)
            # --- accessibility ---------------------------------------------
            if t == "image" and not str(p.get("alt", "")).strip():
                add("warning", "accessibility", f"Image '{node['name']}' has no alt text.", route, nid)
            if t in ("button", "link") and not str(p.get("text", "")).strip():
                add("error", "accessibility", f"{t.capitalize()} '{node['name']}' has no accessible text.", route, nid)
            if t in ("input", "textarea", "select") and not str(p.get("label", "")).strip():
                add("warning", "accessibility", f"Form control '{node['name']}' has no label.", route, nid)
            if t == "heading":
                levels.append((int(node["tag"][1]), nid))
            fg = resolve_color(base.get("color"), tokens)
            bg = resolve_color(base.get("backgroundColor") or base.get("background"), tokens)
            if fg and bg and t in ("heading", "text", "button", "link"):
                ratio = contrast_ratio(fg, bg)
                if ratio < 4.5:
                    add("warning", "accessibility", f"Low colour contrast {ratio:.1f}:1 on '{node['name']}' "
                        "(WCAG AA needs 4.5:1).", route, nid)
            # --- responsive ------------------------------------------------
            cols = str(base.get("gridTemplateColumns", ""))
            m = re.match(r"repeat\((\d+)", cols)
            if m and int(m.group(1)) > 2 and "gridTemplateColumns" not in mobile:
                add("warning", "responsive", f"'{node['name']}' keeps {m.group(1)} columns on mobile.", route, nid)
            width = str(base.get("width", ""))
            wm = re.fullmatch(r"(\d+)px", width)
            if wm and int(wm.group(1)) > 640 and "width" not in mobile and "maxWidth" not in base:
                add("warning", "responsive", f"'{node['name']}' has a fixed {width} width that overflows phones.",
                    route, nid)
        if page is not None:
            h1s = [nid for lvl, nid in levels if lvl == 1]
            if len(h1s) == 0:
                add("warning", "seo", "Page has no H1 heading.", route)
            elif len(h1s) > 1:
                add("warning", "seo", f"Page has {len(h1s)} H1 headings; use exactly one.", route, h1s[1])
            for (prev, _), (cur, nid) in zip(levels, levels[1:], strict=False):
                if cur > prev + 1:
                    add("info", "accessibility", f"Heading level jumps from H{prev} to H{cur}.", route, nid)
            seo = page.seo or {}
            if not seo.get("description"):
                add("info", "seo", "Missing meta description.", route)

    # --- permission safety -------------------------------------------------
    for e in entities:
        if e.permissions.get("delete") == "public" or e.permissions.get("update") == "public":
            add("error", "security", f"Anyone can modify or delete {e.label}. Restrict update/delete.")
        if e.permissions.get("read") == "public" and any(f["type"] == "email" for f in e.fields) \
                and e.permissions.get("create") == "public":
            add("warning", "security", f"{e.label} stores emails and is publicly readable. "
                "Set read permission to admin.")

    # --- generated backend compiles ------------------------------------------
    entity_dicts = [{"name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
                     "sample_data": e.sample_data or []} for e in entities]
    try:
        for path, source in backend_files(project.name, entity_dicts).items():
            if path.endswith(".py"):
                compile(source, path, "exec")
    except SyntaxError as exc:
        add("error", "build", f"Generated backend does not compile: {exc}")

    summary = {s: sum(1 for i in issues if i["severity"] == s) for s in ("error", "warning", "info")}
    return {"issues": issues, "summary": summary, "passed": summary["error"] == 0}


def _bindings(node):
    found = set()
    for n, _ in walk(node):
        for key in ("text", "src", "href", "alt"):
            v = n.get("props", {}).get(key)
            if isinstance(v, str):
                found.update(BINDING_RE.findall(v))
    return found
