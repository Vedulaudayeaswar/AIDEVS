"""Deterministic compiler: component schema -> CSS + HTML.

The same CSS generator is used by the live preview and the React export, so
what the user sees in the canvas is exactly what ships.
"""
import html
import os
import re
import secrets
from urllib.parse import quote_plus

from services.schema import BINDING_RE, BREAKPOINT_MEDIA, CONTAINER_TYPES, is_safe_url, walk

_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
_BRIDGE_PATH = os.path.join(os.path.dirname(__file__), "editor_bridge.js")


def kebab(name):
    return _CAMEL.sub("-", name).lower()


def class_of(node_id):
    return f"n-{node_id}"


# ------------------------------------------------------------------ styles
def tokens_css(tokens):
    lines = [":root {"]
    for key, value in tokens.get("colors", {}).items():
        lines.append(f"  --color-{kebab(key)}: {value};")
    fonts = tokens.get("fonts", {})
    lines.append(f"  --font-heading: '{fonts.get('heading', 'Inter')}', system-ui, sans-serif;")
    lines.append(f"  --font-body: '{fonts.get('body', 'Inter')}', system-ui, sans-serif;")
    lines.append(f"  --radius: {tokens.get('radius', '12px')};")
    lines.append(f"  --max-width: {tokens.get('maxWidth', '1200px')};")
    lines.append("}")
    return "\n".join(lines)


BASE_CSS = """*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; font-family: var(--font-body); color: var(--color-text);
  background: var(--color-background); line-height: 1.5; -webkit-font-smoothing: antialiased; }
h1, h2, h3, h4, h5, h6, p, blockquote { margin: 0; }
img { max-width: 100%; display: block; }
a { color: inherit; }
button { font: inherit; cursor: pointer; }
input, textarea, select { font: inherit; padding: 12px 14px; border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.18); background: #fff; color: #0f172a; width: 100%; }
input:focus, textarea:focus, select:focus { outline: 2px solid var(--color-primary); outline-offset: 1px; }
a:focus-visible, button:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 2px; }
.aid-form-status { min-height: 1.2em; font-size: 14px; margin: 0; }
.aid-form-status[data-state="error"] { color: #dc2626; }
.aid-form-status[data-state="ok"] { color: #16a34a; }
.aid-empty { color: var(--color-muted); }
/* Low-specificity defaults so sparse designs still look finished; every .n-* rule overrides these. */
section { padding: 64px max(24px, calc((100% - var(--max-width)) / 2)); }
section > * + * { margin-top: 16px; }
label { display: flex; flex-direction: column; gap: 6px; font-weight: 600; font-size: 14px; }
button { padding: 12px 22px; border-radius: var(--radius); border: none; background: var(--color-primary);
  color: var(--color-on-primary); font-weight: 600; }
h1 { font-family: var(--font-heading); font-size: clamp(32px, 5vw, 56px); line-height: 1.1; }
h2, h3 { font-family: var(--font-heading); line-height: 1.2; }
"""


def _rules(styles):
    return "; ".join(f"{kebab(p)}: {v}" for p, v in styles.items())


def tree_css(roots):
    """CSS for all nodes in `roots` (list of trees). Base first, then overrides."""
    base, media = [], {bp: [] for bp in BREAKPOINT_MEDIA}
    for root in roots:
        for node, _ in walk(root):
            styles = node.get("styles", {})
            selector = f".{class_of(node['id'])}"
            if styles.get("base"):
                base.append(f"{selector} {{ {_rules(styles['base'])}; }}")
            for bp in BREAKPOINT_MEDIA:
                if styles.get(bp):
                    media[bp].append(f"  {selector} {{ {_rules(styles[bp])}; }}")
    out = list(base)
    for bp, query in BREAKPOINT_MEDIA.items():  # tablet then mobile (mobile wins)
        if media[bp]:
            out.append(f"@media {query} {{\n" + "\n".join(media[bp]) + "\n}")
    return "\n".join(out)


def google_fonts_url(tokens):
    families = {tokens.get("fonts", {}).get("heading", "Inter"), tokens.get("fonts", {}).get("body", "Inter")}
    params = "&".join(f"family={quote_plus(f)}:wght@400;500;600;700;800" for f in sorted(families))
    return f"https://fonts.googleapis.com/css2?{params}&display=swap"


# ------------------------------------------------------------------- html
def _esc(value):
    return html.escape(str(value), quote=True)


def bind(text, record):
    if record is None:
        return text
    return BINDING_RE.sub(lambda m: str(record.get(m.group(1), "")), text)


def _abs_src(src, api_base):
    if src.startswith("/api/assets/") and api_base:
        return api_base.rstrip("/") + src
    return src


class HtmlRenderer:
    def __init__(self, records=None, editor=False, api_base=""):
        self.records = records or {}
        self.editor = editor
        self.api_base = api_base

    def attrs(self, node, extra=None, clone_of=None):
        parts = [f'class="{class_of(node["id"])}"']
        if self.editor:
            if clone_of:
                parts.append(f'data-aclone="{_esc(clone_of)}"')
            else:
                parts.append(f'data-aid="{_esc(node["id"])}"')
                parts.append(f'data-aname="{_esc(node.get("name", ""))}"')
                parts.append(f'data-atype="{_esc(node["type"])}"')
                if node["type"] in CONTAINER_TYPES:
                    parts.append('data-acontainer="1"')
                if node.get("shared"):
                    parts.append(f'data-ashared="{_esc(node["shared"])}"')
        for key, value in (extra or {}).items():
            if value is None or value is False:
                continue
            parts.append(_esc(key) if value is True else f'{_esc(key)}="{_esc(value)}"')
        return " ".join(parts)

    def render(self, node, record=None, clone=False, in_form=False):
        t, p, tag = node["type"], node.get("props", {}), node.get("tag")
        clone_of = node["id"] if clone else None
        a = lambda extra=None: self.attrs(node, extra, clone_of)  # noqa: E731
        text = _esc(bind(p.get("text", ""), record))
        kids = lambda: "".join(self.render(c, record, clone, in_form or t == "form")  # noqa: E731
                               for c in node.get("children", []))

        if t in ("page", "section", "container"):
            return f"<{tag} {a({'id': p.get('anchor')})}>{kids()}</{tag}>"
        if t == "heading" or t == "text":
            return f"<{tag} {a()}>{text}</{tag}>"
        if t == "link":
            return f"<a {a({'href': bind(p.get('href', '#'), record)})}>{text}</a>"
        if t == "button":
            if tag == "a" and p.get("href"):
                return f"<a {a({'href': p['href'], 'role': 'button'})}>{text}</a>"
            return f"<button {a({'type': 'submit' if in_form else 'button'})}>{text}</button>"
        if t == "image":
            src = bind(p.get("src", ""), record)
            if not is_safe_url(src, kind="src"):
                src = ""
            return f"<img {a({'src': _abs_src(src, self.api_base) or None, 'alt': bind(p.get('alt', ''), record), 'loading': 'lazy'})}>"
        if t == "icon":
            return f"<span {a({'role': 'img', 'aria-label': p.get('label') or None})}>{text}</span>"
        if t == "divider":
            return f"<hr {a()}>"
        if t == "form":
            extra = {"data-aform": p.get("entity", ""), "data-success": p.get("successMessage", "")}
            return (f"<form {a(extra)}>{kids()}"
                    f'<p class="aid-form-status" role="status" aria-live="polite"></p></form>')
        if t in ("input", "textarea", "select"):
            label = f"<span>{_esc(p.get('label', ''))}</span>"
            common = {"name": p.get("name", "field"), "required": bool(p.get("required")),
                      "placeholder": p.get("placeholder") or None}
            if t == "input":
                ctrl = f"<input {_attr_str({**common, 'type': p.get('inputType', 'text')})}>"
            elif t == "textarea":
                ctrl = f"<textarea {_attr_str({**common, 'rows': p.get('rows', 4)})}></textarea>"
            else:
                opts = "".join(f"<option>{_esc(o)}</option>" for o in p.get("options", []))
                common.pop("placeholder", None)
                ctrl = f"<select {_attr_str(common)}>{opts}</select>"
            return f"<label {a()}>{label}{ctrl}</label>"
        if t == "collection":
            rows = self.records.get(p.get("entity"), [])[: p.get("limit", 12)]
            template = node.get("children", [])
            if not template:
                return f"<{tag} {a({'data-acollection': p.get('entity')})}></{tag}>"
            if rows:
                items = [self.render(template[0], row, clone or i > 0) for i, row in enumerate(rows)]
            else:
                empty = f'<p class="aid-empty">{_esc(p.get("emptyText", "No items yet."))}</p>'
                items = [self.render(template[0], {}, clone)] if self.editor else [empty]
            return f"<{tag} {a({'data-acollection': p.get('entity')})}>{''.join(items)}</{tag}>"
        return ""


def _attr_str(attrs):
    parts = []
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        parts.append(_esc(key) if value is True else f'{_esc(key)}="{_esc(value)}"')
    return " ".join(parts)


def compose_page(layout, page_tree):
    """Insert the shared header/footer around a page's own sections."""
    children = [c for c in page_tree.get("children", []) if not c.get("shared")]
    composed = dict(page_tree)
    head = (layout or {}).get("header")
    foot = (layout or {}).get("footer")
    composed["children"] = ([{**head, "shared": "header"}] if head else []) + children + \
                           ([{**foot, "shared": "footer"}] if foot else [])
    return composed


def split_page(tree):
    """Inverse of compose_page -> (page_tree, header, footer)."""
    header = footer = None
    own = []
    for child in tree.get("children", []):
        if child.get("shared") == "header" and header is None:
            header = {k: v for k, v in child.items() if k != "shared"}
        elif child.get("shared") == "footer" and footer is None:
            footer = {k: v for k, v in child.items() if k != "shared"}
        else:
            own.append({k: v for k, v in child.items() if k != "shared"})
    return {**tree, "children": own}, header, footer


def preview_document(tree, tokens, *, title="Preview", records=None, editor=True,
                     api_base="", mode="edit"):
    """Self-contained HTML document for the sandboxed canvas iframe."""
    nonce = secrets.token_urlsafe(16)
    css = "\n".join([tokens_css(tokens), BASE_CSS, tree_css([tree])])
    body = HtmlRenderer(records, editor=editor, api_base=api_base).render(tree)
    img_src = "https: data:" + (f" {api_base.rstrip('/')}" if api_base else "")
    csp = (f"default-src 'none'; img-src {img_src}; "
           "style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
           f"script-src 'nonce-{nonce}'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-src 'none'")
    bridge = ""
    if editor:
        with open(_BRIDGE_PATH, encoding="utf-8") as fh:
            bridge = f'<script nonce="{nonce}">window.__AID_MODE__={_js_str(mode)};\n{fh.read()}</script>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{_esc(csp)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{css}</style>
</head>
<body>
{body}
{bridge}
<!-- Web fonts are injected from script so they never block parsing or rendering:
     if the font CDN is slow or unreachable the canvas still renders with fallback fonts. -->
<script nonce="{nonce}">(function(){{var l=document.createElement("link");l.rel="stylesheet";l.href={_js_str(google_fonts_url(tokens))};document.head.appendChild(l);}})();</script>
</body>
</html>"""


def _js_str(value):
    import json
    return json.dumps(value).replace("</", "<\\/")
