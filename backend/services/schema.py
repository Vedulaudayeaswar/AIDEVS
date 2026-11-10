"""AIDevs controlled component schema.

A page is a tree of nodes::

    {"id": "n_ab12cd34", "type": "heading", "name": "Hero heading",
     "tag": "h1", "props": {"text": "Hello"},
     "styles": {"base": {"fontSize": "56px"}, "tablet": {}, "mobile": {"fontSize": "36px"}},
     "children": []}

Everything the AI or the visual editor produces passes through
`sanitize_tree`, which enforces an allow-list of node types, tags, props and
CSS properties. Content is always rendered escaped and no node can carry
scripts or event handlers, which is what makes the preview canvas and the
exported code safe.
"""
import copy
import keyword
import re
import secrets

MAX_NODES = 2000
MAX_DEPTH = 32
MAX_TEXT = 5000
BREAKPOINTS = ("base", "tablet", "mobile")
BREAKPOINT_MEDIA = {"tablet": "(max-width: 1024px)", "mobile": "(max-width: 640px)"}

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
ENTITY_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
BINDING_RE = re.compile(r"\{\{\s*([a-z][a-z0-9_]{0,40})\s*\}\}")

CONTAINER_TYPES = {"page", "section", "container", "form", "collection"}

NODE_TYPES = {
    "page": {"tags": {"div"}, "default": "div", "props": set()},
    "section": {"tags": {"section", "header", "footer", "nav", "main", "aside", "article", "div"},
                "default": "section", "props": {"anchor"}},
    "container": {"tags": {"div", "section", "article", "aside", "header", "footer", "nav", "ul", "li"},
                  "default": "div", "props": {"anchor"}},
    "heading": {"tags": {"h1", "h2", "h3", "h4", "h5", "h6"}, "default": "h2", "props": {"text"}},
    "text": {"tags": {"p", "span", "small", "blockquote", "li", "strong"}, "default": "p",
             "props": {"text"}},
    "button": {"tags": {"a", "button"}, "default": "a", "props": {"text", "href", "variant"}},
    "link": {"tags": {"a"}, "default": "a", "props": {"text", "href"}},
    "image": {"tags": {"img"}, "default": "img", "props": {"src", "alt"}},
    "icon": {"tags": {"span"}, "default": "span", "props": {"text", "label"}},
    "divider": {"tags": {"hr"}, "default": "hr", "props": set()},
    "form": {"tags": {"form"}, "default": "form",
             "props": {"entity", "successMessage", "submitText"}},
    "input": {"tags": {"label"}, "default": "label",
              "props": {"label", "name", "inputType", "placeholder", "required"}},
    "textarea": {"tags": {"label"}, "default": "label",
                 "props": {"label", "name", "placeholder", "required", "rows"}},
    "select": {"tags": {"label"}, "default": "label",
               "props": {"label", "name", "options", "required"}},
    "collection": {"tags": {"div", "ul"}, "default": "div",
                   "props": {"entity", "limit", "emptyText"}},
}

INPUT_TYPES = {"text", "email", "tel", "number", "password", "url", "date"}

STYLE_PROPS = {
    "display", "position", "top", "right", "bottom", "left", "zIndex",
    "width", "height", "minWidth", "minHeight", "maxWidth", "maxHeight",
    "margin", "marginTop", "marginRight", "marginBottom", "marginLeft",
    "padding", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "gap", "rowGap", "columnGap", "flexDirection", "flexWrap", "justifyContent",
    "alignItems", "alignSelf", "alignContent", "flex", "flexGrow", "flexShrink",
    "flexBasis", "gridTemplateColumns", "gridTemplateRows", "gridColumn", "gridRow",
    "placeItems", "order", "background", "backgroundColor", "backgroundImage",
    "backgroundSize", "backgroundPosition", "backgroundRepeat", "color",
    "border", "borderTop", "borderRight", "borderBottom", "borderLeft",
    "borderRadius", "borderColor", "borderWidth", "borderStyle", "boxShadow",
    "opacity", "overflow", "fontFamily", "fontSize", "fontWeight", "lineHeight",
    "letterSpacing", "textAlign", "textTransform", "textDecoration", "fontStyle",
    "objectFit", "aspectRatio", "transform", "transition", "cursor",
    "backdropFilter", "filter", "whiteSpace", "listStyle",
}
UNITLESS = {"opacity", "zIndex", "fontWeight", "lineHeight", "flexGrow", "flexShrink", "order"}
FORBIDDEN_VALUE = re.compile(r"[;{}<>\\@]|expression\s*\(|javascript:|behavior\s*:|-moz-binding",
                             re.IGNORECASE)
URL_IN_CSS = re.compile(r"url\(\s*['\"]?([^'\")]*)['\"]?\s*\)", re.IGNORECASE)
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
COLOR_FN = re.compile(r"^(rgb|rgba|hsl|hsla)\([0-9.,%\s/]+\)$")
FONT_NAME = re.compile(r"^[A-Za-z0-9 ]{1,40}$")

FIELD_TYPES = {"string", "text", "integer", "number", "boolean", "date", "datetime",
               "email", "url", "image"}
PERMISSION_LEVELS = {"public", "auth", "owner", "admin"}
RESERVED_ENTITIES = {"user", "users", "auth", "api", "health", "admin", "token", "session",
                     "metadata", "query", "base", "model", "app", "db", "auth_login", "auth_register"}
RESERVED_FIELDS = {"id", "owner_id", "created_at", "updated_at", "metadata", "query", "to_dict",
                   "registry"}
JS_RESERVED = {"default", "function", "var", "let", "const", "new", "delete", "this", "switch",
               "case", "typeof", "void", "enum", "export", "extends", "super"}


class SchemaError(ValueError):
    pass


def new_node_id():
    return "n_" + secrets.token_hex(4)


# --------------------------------------------------------------------- values
def is_safe_url(value, allow_binding=False, kind="href"):
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v or len(v) > 2048:
        return False
    if allow_binding and BINDING_RE.fullmatch(v):
        return True
    if any(c in v for c in "<>\"'` \n\r\t"):
        return False
    lower = v.lower()
    if kind == "src":
        return lower.startswith("https://") or lower.startswith("/api/assets/") \
            or lower.startswith("http://localhost")
    if lower.startswith(("https://", "http://", "mailto:", "tel:")):
        return True
    return v.startswith("#") or (v.startswith("/") and not v.startswith("//"))


def sanitize_style_value(prop, value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value) if prop in UNITLESS else f"{value}px"
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or len(v) > 400 or FORBIDDEN_VALUE.search(v):
        return None
    for url in URL_IN_CSS.findall(v):
        if not is_safe_url(url, kind="src"):
            return None
    if prop == "fontFamily":
        parts = [p.strip().strip("'\"") for p in v.split(",")]
        generic = {"serif", "sans-serif", "monospace", "cursive", "system-ui", "inherit"}
        if not all(FONT_NAME.match(p) or p in generic or p.startswith("var(--") for p in parts if p):
            return None
    return v


def sanitize_styles(styles, warnings, node_id):
    clean = {bp: {} for bp in BREAKPOINTS}
    if not isinstance(styles, dict):
        return clean
    # Accept a flat style dict as "base"
    if not any(k in styles for k in BREAKPOINTS):
        styles = {"base": styles}
    for bp in BREAKPOINTS:
        block = styles.get(bp) or {}
        if not isinstance(block, dict):
            continue
        for prop, value in block.items():
            if prop not in STYLE_PROPS:
                warnings.append(f"{node_id}: dropped style '{prop}'")
                continue
            sv = sanitize_style_value(prop, value)
            if sv is None:
                warnings.append(f"{node_id}: dropped unsafe value for '{prop}'")
                continue
            clean[bp][prop] = sv
    return clean


def _text(value, limit=MAX_TEXT):
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):
        return ""
    return str(value)[:limit]


def sanitize_props(ntype, props, warnings, node_id):
    allowed = NODE_TYPES[ntype]["props"]
    props = props if isinstance(props, dict) else {}
    out = {}
    for key, value in props.items():
        if key not in allowed:
            continue
        if key == "href":
            if is_safe_url(value):
                out[key] = value.strip()
            else:
                warnings.append(f"{node_id}: dropped unsafe href")
        elif key == "src":
            if is_safe_url(value, allow_binding=True, kind="src"):
                out[key] = value.strip()
            else:
                warnings.append(f"{node_id}: dropped unsafe image src")
        elif key in ("required",):
            out[key] = bool(value)
        elif key in ("rows", "limit"):
            try:
                out[key] = max(1, min(int(value), 100))
            except (TypeError, ValueError):
                pass
        elif key == "inputType":
            out[key] = value if value in INPUT_TYPES else "text"
        elif key in ("name", "entity"):
            if isinstance(value, str) and FIELD_RE.match(value.strip()):
                out[key] = value.strip()
        elif key == "options":
            if isinstance(value, list):
                out[key] = [_text(o, 120) for o in value[:50] if isinstance(o, (str, int, float))]
        elif key == "anchor":
            if isinstance(value, str) and re.match(r"^[a-z0-9-]{1,40}$", value):
                out[key] = value
        elif key == "variant":
            out[key] = value if value in ("primary", "secondary", "ghost") else "primary"
        else:
            out[key] = _text(value)
    if ntype == "image":
        out.setdefault("alt", "")
    return out


def sanitize_node(node, warnings, seen_ids, depth=0, counter=None):
    if counter is None:
        counter = [0]
    if not isinstance(node, dict):
        raise SchemaError("node must be an object")
    counter[0] += 1
    if counter[0] > MAX_NODES:
        raise SchemaError(f"tree exceeds {MAX_NODES} nodes")
    if depth > MAX_DEPTH:
        raise SchemaError("tree is nested too deeply")

    ntype = node.get("type")
    if ntype not in NODE_TYPES:
        # Graceful coercion of common AI vocabulary.
        aliases = {"div": "container", "box": "container", "row": "container", "column": "container",
                   "grid": "container", "card": "container", "paragraph": "text", "p": "text",
                   "img": "image", "a": "link", "nav": "section", "header": "section",
                   "footer": "section", "hr": "divider", "h1": "heading", "h2": "heading",
                   "h3": "heading", "span": "text", "list": "container"}
        mapped = aliases.get(str(ntype).lower())
        if not mapped:
            raise SchemaError(f"unknown node type '{ntype}'")
        warnings.append(f"coerced type '{ntype}' -> '{mapped}'")
        if mapped == "heading" and str(ntype).lower() in ("h1", "h2", "h3"):
            node = {**node, "tag": str(ntype).lower()}
        if mapped == "section" and str(ntype).lower() in ("nav", "header", "footer"):
            node = {**node, "tag": node.get("tag") or str(ntype).lower()}
        ntype = mapped

    nid = node.get("id")
    if not isinstance(nid, str) or not ID_RE.match(nid) or nid in seen_ids:
        nid = new_node_id()
        while nid in seen_ids:
            nid = new_node_id()
    seen_ids.add(nid)

    spec = NODE_TYPES[ntype]
    tag = node.get("tag")
    if tag not in spec["tags"]:
        tag = spec["default"]
    props = sanitize_props(ntype, node.get("props"), warnings, nid)
    if ntype == "button" and tag == "a" and "href" not in props:
        tag = "button"

    clean = {
        "id": nid,
        "type": ntype,
        "name": _text(node.get("name") or ntype.capitalize(), 80),
        "tag": tag,
        "props": props,
        "styles": sanitize_styles(node.get("styles"), warnings, nid),
        "children": [],
    }
    # Shared layout regions (global header/footer) live directly under the page.
    if depth == 1 and node.get("shared") in ("header", "footer"):
        clean["shared"] = node["shared"]
    children = node.get("children") or []
    if ntype in CONTAINER_TYPES and isinstance(children, list):
        for child in children:
            try:
                clean["children"].append(sanitize_node(child, warnings, seen_ids, depth + 1, counter))
            except SchemaError as exc:
                if "exceeds" in str(exc) or "deeply" in str(exc):
                    raise
                warnings.append(f"{nid}: dropped child ({exc})")
    elif children:
        warnings.append(f"{nid}: '{ntype}' cannot have children; dropped")
    return clean


def sanitize_tree(tree, root_type="page"):
    """Validate + sanitize a full tree. Returns (clean_tree, warnings)."""
    warnings = []
    if not isinstance(tree, dict):
        raise SchemaError("tree must be an object")
    if root_type == "page":
        tree = {**tree, "type": "page"}
    clean = sanitize_node(tree, warnings, set())
    return clean, warnings


def sanitize_subtree(node, existing_ids=()):
    warnings = []
    seen = set(existing_ids)
    clean = sanitize_node(node, warnings, seen)
    return clean, warnings


# ---------------------------------------------------------------- traversal
def walk(node, parent=None):
    yield node, parent
    for child in node.get("children", []):
        yield from walk(child, node)


def find_node(tree, node_id):
    for node, parent in walk(tree):
        if node["id"] == node_id:
            return node, parent
    return None, None


def all_ids(tree):
    return {n["id"] for n, _ in walk(tree)}


def reassign_ids(node, taken):
    node = copy.deepcopy(node)
    for n, _ in walk(node):
        nid = new_node_id()
        while nid in taken:
            nid = new_node_id()
        n["id"] = nid
        taken.add(nid)
    return node


def count_nodes(tree):
    return sum(1 for _ in walk(tree))


def bindings_in(node):
    """Return set of `{{field}}` bindings used in a collection template."""
    fields = set()
    for n, _ in walk(node):
        for key in ("text", "src", "href", "alt"):
            value = n.get("props", {}).get(key)
            if isinstance(value, str):
                fields.update(BINDING_RE.findall(value))
    return fields


# ---------------------------------------------------------------- entities
def sanitize_entity(entity):
    if not isinstance(entity, dict):
        raise SchemaError("entity must be an object")
    name = str(entity.get("name", "")).strip().lower().replace(" ", "_").replace("-", "_")
    if name.endswith("s") and not name.endswith("ss") and len(name) > 3:
        name = name[:-1]  # prefer singular model names
    if not ENTITY_RE.match(name) or name in RESERVED_ENTITIES:
        raise SchemaError(f"invalid entity name '{name}'")
    fields, seen = [], set()
    for field in (entity.get("fields") or [])[:30]:
        if not isinstance(field, dict):
            continue
        fname = str(field.get("name", "")).strip().lower().replace(" ", "_").replace("-", "_")
        if keyword.iskeyword(fname) or fname in JS_RESERVED:
            fname = f"{fname}_value"
        if not FIELD_RE.match(fname) or fname in RESERVED_FIELDS or fname in seen:
            continue
        ftype = field.get("type", "string")
        ftype = {"str": "string", "int": "integer", "float": "number", "decimal": "number",
                 "price": "number", "bool": "boolean", "image_url": "image", "longtext": "text"
                 }.get(ftype, ftype)
        if ftype not in FIELD_TYPES:
            ftype = "string"
        seen.add(fname)
        fields.append({
            "name": fname,
            "label": _text(field.get("label") or fname.replace("_", " ").title(), 80),
            "type": ftype,
            "required": bool(field.get("required", False)),
        })
    if not fields:
        raise SchemaError(f"entity '{name}' has no valid fields")
    perms_in = entity.get("permissions") or {}
    defaults = {"read": "public", "create": "admin", "update": "admin", "delete": "admin"}
    permissions = {}
    for action, default in defaults.items():
        level = perms_in.get(action, default) if isinstance(perms_in, dict) else default
        permissions[action] = level if level in PERMISSION_LEVELS else default
    samples = []
    field_names = {f["name"] for f in fields}
    for row in (entity.get("sample_data") or entity.get("samples") or [])[:12]:
        if isinstance(row, dict):
            samples.append({k: v for k, v in row.items()
                            if k in field_names and isinstance(v, (str, int, float, bool))})
    return {
        "name": name,
        "label": _text(entity.get("label") or name.replace("_", " ").title(), 120),
        "fields": fields,
        "permissions": permissions,
        "sample_data": samples,
    }


def validate_record(entity_fields, data, partial=False):
    """Validate a record against entity fields (used by the preview data API)."""
    if not isinstance(data, dict):
        raise SchemaError("record must be an object")
    out, errors = {}, {}
    for field in entity_fields:
        name, ftype = field["name"], field["type"]
        if name not in data or data[name] in (None, ""):
            if field.get("required") and not partial:
                errors[name] = "is required"
            continue
        value = data[name]
        try:
            if ftype in ("integer",):
                value = int(value)
            elif ftype == "number":
                value = float(value)
            elif ftype == "boolean":
                value = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "on")
            else:
                value = str(value)[:MAX_TEXT]
                if ftype == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
                    raise ValueError("must be a valid email")
                if ftype in ("url", "image") and not re.match(r"^https?://", value):
                    raise ValueError("must be an http(s) URL")
        except (TypeError, ValueError) as exc:
            errors[name] = str(exc) if str(exc).startswith("must") else f"must be {ftype}"
            continue
        out[name] = value
    if errors:
        raise SchemaError("; ".join(f"{k} {v}" for k, v in errors.items()))
    return out


# ------------------------------------------------------------------ tokens
DEFAULT_TOKENS = {
    "colors": {
        "primary": "#6366f1", "secondary": "#0ea5e9", "accent": "#f59e0b",
        "background": "#ffffff", "surface": "#f8fafc", "text": "#0f172a", "muted": "#64748b",
        "onPrimary": "#ffffff",
    },
    "fonts": {"heading": "Inter", "body": "Inter"},
    "radius": "12px",
    "maxWidth": "1200px",
}


def sanitize_tokens(tokens):
    tokens = tokens if isinstance(tokens, dict) else {}
    out = copy.deepcopy(DEFAULT_TOKENS)
    colors = tokens.get("colors") if isinstance(tokens.get("colors"), dict) else {}
    for key, value in colors.items():
        if re.match(r"^[a-zA-Z][a-zA-Z0-9]{0,30}$", str(key)) and isinstance(value, str) and \
                (HEX_COLOR.match(value.strip()) or COLOR_FN.match(value.strip())):
            out["colors"][key] = value.strip()
    fonts = tokens.get("fonts") if isinstance(tokens.get("fonts"), dict) else {}
    for key in ("heading", "body"):
        value = fonts.get(key)
        if isinstance(value, str) and FONT_NAME.match(value.strip()):
            out["fonts"][key] = value.strip()
    for key in ("radius", "maxWidth"):
        value = tokens.get(key)
        if isinstance(value, str) and re.match(r"^\d{1,4}(px|rem|em|%)$", value.strip()):
            out[key] = value.strip()
    return out



def unflatten(nodes):
    """Rebuild nested trees from the flat {"id", "parent", ...} list the AI agents emit.

    Returns the list of root nodes (parent null) in order. Unknown parents and cycles are
    rejected so the model can be asked for a corrected answer."""
    if not isinstance(nodes, list) or not nodes:
        raise SchemaError("expected a non-empty list of nodes")
    by_id, roots, order = {}, [], []
    for raw in nodes:
        if not isinstance(raw, dict):
            continue
        nid = str(raw.get("id") or "")
        if not nid or nid in by_id:
            raise SchemaError(f"every node needs a unique id (problem with {nid!r})")
        node = {k: v for k, v in raw.items() if k not in ("parent", "children")}
        node["children"] = []
        by_id[nid] = node
        order.append((nid, raw.get("parent")))
    for nid, parent in order:
        if parent in (None, "", "null"):
            roots.append(by_id[nid])
        elif str(parent) in by_id and str(parent) != nid:
            by_id[str(parent)]["children"].append(by_id[nid])
        else:
            raise SchemaError(f"node {nid!r} has unknown parent {parent!r}")
    # cycle check: every node must be reachable from a root
    seen = set()
    stack = list(roots)
    while stack:
        n = stack.pop()
        if id(n) in seen:
            raise SchemaError("node graph contains a cycle")
        seen.add(id(n))
        stack.extend(n["children"])
    if len(seen) != len(by_id):
        raise SchemaError("some nodes are not connected to a top-level section")
    return roots
