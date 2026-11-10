"""Compile pages (component schema) into a React + Vite frontend.

* One component file per top-level section, one file per page, shared
  SiteHeader / SiteFooter.
* Styling uses the same generated CSS as the canvas (`.n-<nodeId>` classes),
  so visual edits survive export exactly. `aidevs.sourcemap.json` maps every
  node id to the file that renders it.
"""
import json
import re

from services.compiler import BASE_CSS, class_of, google_fonts_url, tokens_css, tree_css
from services.export_backend import plural
from services.schema import BINDING_RE, is_safe_url

SELF_CLOSING = {"img", "hr", "input"}


def js(value):
    """Safe JS string literal (also safe inside JSX expression containers)."""
    return json.dumps(str(value), ensure_ascii=False).replace("</", "<\\/")


def component_name(name, taken, suffix=""):
    base = re.sub(r"[^A-Za-z0-9]+", " ", name or "Section").title().replace(" ", "") or "Section"
    if not base[0].isalpha():
        base = "S" + base
    base += suffix
    candidate, i = base, 2
    while candidate in taken:
        candidate = f"{base}{i}"
        i += 1
    taken.add(candidate)
    return candidate


class JsxRenderer:
    def __init__(self, asset_map, sourcemap, filename):
        self.asset_map = asset_map  # "/api/assets/<id>" -> "/assets/<file>"
        self.sourcemap = sourcemap
        self.filename = filename
        self.uses_link = False
        self.uses_form = False
        self.uses_collection = False

    def expr(self, text, item_var=None):
        """Turn text with optional {{field}} bindings into a JSX expression."""
        if item_var and BINDING_RE.search(text):
            parts, pos = [], 0
            for m in BINDING_RE.finditer(text):
                if m.start() > pos:
                    parts.append(js(text[pos:m.start()]))
                parts.append(f"String({item_var}.{m.group(1)} ?? \"\")")
                pos = m.end()
            if pos < len(text):
                parts.append(js(text[pos:]))
            return "{" + " + ".join(parts) + "}"
        return "{" + js(text) + "}"

    def attr(self, name, value, item_var=None):
        if value is None or value is False:
            return ""
        if value is True:
            return f" {name}"
        return f" {name}={self.expr(str(value), item_var)}"

    def src(self, value):
        if value in self.asset_map:
            return self.asset_map[value]
        return value if is_safe_url(value, allow_binding=True, kind="src") else ""

    def render(self, node, indent=2, item_var=None, in_form=False):
        self.sourcemap[node["id"]] = {"file": self.filename, "className": class_of(node["id"]),
                                      "name": node.get("name", ""), "type": node["type"]}
        pad = " " * indent
        t, p, tag = node["type"], node.get("props", {}), node.get("tag")
        cls = f' className="{class_of(node["id"])}"'

        def kids(var=item_var, form=in_form):
            return "".join(self.render(c, indent + 2, var, form or t == "form") for c in node.get("children", []))

        if t in ("page", "section", "container"):
            anchor = self.attr("id", p.get("anchor"))
            return f"{pad}<{tag}{cls}{anchor}>\n{kids()}{pad}</{tag}>\n"
        if t in ("heading", "text"):
            return f"{pad}<{tag}{cls}>{self.expr(p.get('text', ''), item_var)}</{tag}>\n"
        if t in ("link", "button") and (t == "link" or tag == "a") and p.get("href"):
            href = p["href"]
            role = ' role="button"' if t == "button" else ""
            if href.startswith("/") and not href.startswith("//") and not BINDING_RE.search(href):
                self.uses_link = True
                return f"{pad}<Link{cls}{role} to={js(href)}>{self.expr(p.get('text', ''), item_var)}</Link>\n"
            return f"{pad}<a{cls}{role}{self.attr('href', href, item_var)}>{self.expr(p.get('text', ''), item_var)}</a>\n"
        if t in ("button", "link"):
            btype = "submit" if in_form else "button"
            return f'{pad}<button{cls} type="{btype}">{self.expr(p.get("text", ""), item_var)}</button>\n'
        if t == "image":
            src = self.src(p.get("src", ""))
            return (f"{pad}<img{cls}{self.attr('src', src or None, item_var)}"
                    f"{self.attr('alt', p.get('alt', ''), item_var)} loading=\"lazy\" />\n")
        if t == "icon":
            label = self.attr("aria-label", p.get("label") or None)
            return f'{pad}<span{cls} role="img"{label}>{self.expr(p.get("text", ""))}</span>\n'
        if t == "divider":
            return f"{pad}<hr{cls} />\n"
        if t == "form":
            self.uses_form = True
            return (f"{pad}<DataForm{cls} entity={js(p.get('entity', ''))} "
                    f"successMessage={js(p.get('successMessage', 'Saved!'))}>\n{kids()}{pad}</DataForm>\n")
        if t in ("input", "textarea", "select"):
            common = (f" name={js(p.get('name', 'field'))}" + (" required" if p.get("required") else "")
                      + (self.attr("placeholder", p.get("placeholder")) if t != "select" else ""))
            if t == "input":
                ctrl = f"<input type={js(p.get('inputType', 'text'))}{common} />"
            elif t == "textarea":
                ctrl = f"<textarea rows={{{int(p.get('rows', 4))}}}{common} />"
            else:
                opts = "".join(f"<option>{self.expr(o)}</option>" for o in p.get("options", []))
                ctrl = f"<select{common}>{opts}</select>"
            return f"{pad}<label{cls}><span>{self.expr(p.get('label', ''))}</span>{ctrl}</label>\n"
        if t == "collection":
            self.uses_collection = True
            template = node.get("children", [])
            body = self.render(template[0], indent + 4, "item") if template else f"{pad}    <div />\n"
            return (f"{pad}<Collection{cls} entity={js(p.get('entity', ''))} limit={{{int(p.get('limit', 12))}}}"
                    f" emptyText={js(p.get('emptyText', 'No items yet.'))}>\n"
                    f"{pad}  {{(item) => (\n{body}{pad}  )}}\n{pad}</Collection>\n")
        return ""


def component_file(name, node, asset_map, sourcemap, filename):
    r = JsxRenderer(asset_map, sourcemap, filename)
    body = r.render(node, 4)
    imports = ['import React from "react";']
    if r.uses_link:
        imports.append('import { Link } from "react-router-dom";')
    depth = filename.count("/") - 2  # relative to src/
    up = "../" * depth if depth > 0 else "./"
    if r.uses_form:
        imports.append(f'import DataForm from "{up}lib/DataForm";')
    if r.uses_collection:
        imports.append(f'import Collection from "{up}lib/Collection";')
    return ("\n".join(imports) + "\n\n"
            f"// Generated by AIDevs from node {node['id']} ({node.get('name', '')}).\n"
            f"export default function {name}() {{\n  return (\n{body}  );\n}}\n")


API_JS = """// API client for the generated backend.
const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:5000").replace(/\\/$/, "");
const TOKEN_KEY = "app_token";

export const RESOURCE_PATHS = __PATHS__;

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(token) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
}

export async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const fields = data && data.fields ? Object.entries(data.fields).map(([k, v]) => `${k} ${v}`).join(", ") : "";
    throw new Error(fields || (data && data.error) || `Request failed (${response.status})`);
  }
  return data;
}

function pathFor(entity) {
  const path = RESOURCE_PATHS[entity];
  if (!path) throw new Error(`Unknown resource "${entity}"`);
  return `/api/${path}`;
}

export const api = {
  list: (entity, params = {}) => request(`${pathFor(entity)}?${new URLSearchParams(params)}`),
  get: (entity, id) => request(`${pathFor(entity)}/${id}`),
  create: (entity, data) => request(pathFor(entity), { method: "POST", body: data }),
  update: (entity, id, data) => request(`${pathFor(entity)}/${id}`, { method: "PATCH", body: data }),
  remove: (entity, id) => request(`${pathFor(entity)}/${id}`, { method: "DELETE" }),
  async login(credentials) {
    const data = await request("/api/auth/login", { method: "POST", body: credentials });
    setToken(data.token);
    return data.user;
  },
  async register(details) {
    const data = await request("/api/auth/register", { method: "POST", body: details });
    setToken(data.token);
    return data.user;
  },
  logout() { setToken(null); },
};
"""

DATAFORM_JSX = """import React, { useState } from "react";
import { api } from "../api";

// Submits its fields to the generated backend. entity "auth_login" / "auth_register" sign users in.
export default function DataForm({ entity, successMessage, className, children }) {
  const [status, setStatus] = useState({ state: "idle", message: "" });

  async function onSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());
    setStatus({ state: "sending", message: "Sending…" });
    try {
      if (entity === "auth_login") await api.login(data);
      else if (entity === "auth_register") await api.register(data);
      else await api.create(entity, data);
      form.reset();
      setStatus({ state: "ok", message: successMessage || "Saved!" });
    } catch (error) {
      setStatus({ state: "error", message: error.message });
    }
  }

  return (
    <form className={className} onSubmit={onSubmit}>
      {children}
      <p className="aid-form-status" role="status" aria-live="polite" data-state={status.state}>
        {status.message}
      </p>
    </form>
  );
}
"""

COLLECTION_JSX = """import React, { useEffect, useState } from "react";
import { api } from "../api";

// Loads records of `entity` from the backend and renders `children(item)` for each.
export default function Collection({ entity, limit = 12, emptyText, className, children }) {
  const [state, setState] = useState({ loading: true, items: [], error: "" });

  useEffect(() => {
    let active = true;
    api.list(entity, { per_page: limit })
      .then((data) => active && setState({ loading: false, items: data.items, error: "" }))
      .catch((error) => active && setState({ loading: false, items: [], error: error.message }));
    return () => { active = false; };
  }, [entity, limit]);

  if (state.loading) return <div className={className} aria-busy="true">Loading…</div>;
  if (state.error) return <div className={className} role="alert">{state.error}</div>;
  if (!state.items.length) return <div className={className}><p className="aid-empty">{emptyText}</p></div>;
  return (
    <div className={className}>
      {state.items.map((item) => <React.Fragment key={item.id}>{children(item)}</React.Fragment>)}
    </div>
  );
}
"""


def frontend_files(project, pages, entities, tokens, asset_map):
    """Return {path: content} for the React app plus the node->file sourcemap."""
    sourcemap, files, taken = {}, {}, set()
    layout = project.get("layout") or {}
    header, footer = layout.get("header"), layout.get("footer")
    roots_for_css = [n for n in (header, footer) if n]

    if header:
        files["frontend/src/components/layout/SiteHeader.jsx"] = component_file(
            "SiteHeader", header, asset_map, sourcemap, "frontend/src/components/layout/SiteHeader.jsx")
    if footer:
        files["frontend/src/components/layout/SiteFooter.jsx"] = component_file(
            "SiteFooter", footer, asset_map, sourcemap, "frontend/src/components/layout/SiteFooter.jsx")

    routes, page_names = [], set()
    for page in pages:
        tree = page["tree"]
        roots_for_css.append(tree)
        page_comp = component_name(page["name"], page_names, "Page")
        section_imports, section_tags = [], []
        for section in tree.get("children", []):
            if section.get("shared"):
                continue
            name = component_name(section.get("name"), taken)
            path = f"frontend/src/components/{name}.jsx"
            files[path] = component_file(name, section, asset_map, sourcemap, path)
            section_imports.append(f'import {name} from "../components/{name}";')
            section_tags.append(f"      <{name} />")
        sourcemap[tree["id"]] = {"file": f"frontend/src/pages/{page_comp}.jsx", "className": class_of(tree["id"]),
                                 "name": page["name"], "type": "page"}
        seo = page.get("seo") or {}
        title = seo.get("title") or f"{page['name']} | {project['name']}"
        files[f"frontend/src/pages/{page_comp}.jsx"] = (
            'import React, { useEffect } from "react";\n' + "\n".join(section_imports) + "\n\n"
            f"export default function {page_comp}() {{\n"
            f"  useEffect(() => {{ document.title = {js(title)}; }}, []);\n"
            f'  return (\n    <main className="{class_of(tree["id"])}">\n'
            + "\n".join(section_tags) + "\n    </main>\n  );\n}\n")
        routes.append((page["route"], page_comp))

    imports = "\n".join(f'import {comp} from "./pages/{comp}";' for _, comp in routes)
    route_lines = "\n".join(f'          <Route path={js(route)} element={{<{comp} />}} />' for route, comp in routes)
    files["frontend/src/App.jsx"] = (
        'import React from "react";\nimport { BrowserRouter, Routes, Route } from "react-router-dom";\n'
        + ('import SiteHeader from "./components/layout/SiteHeader";\n' if header else "")
        + ('import SiteFooter from "./components/layout/SiteFooter";\n' if footer else "")
        + imports + "\n\nexport default function App() {\n  return (\n    <BrowserRouter>\n"
        + ("      <SiteHeader />\n" if header else "")
        + "      <Routes>\n" + route_lines
        + '\n          <Route path="*" element={<main style={{ padding: 48 }}><h1>Page not found</h1></main>} />\n'
        + "      </Routes>\n" + ("      <SiteFooter />\n" if footer else "")
        + "    </BrowserRouter>\n  );\n}\n")

    files["frontend/src/main.jsx"] = (
        'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n'
        'import "./styles/app.css";\n\nReactDOM.createRoot(document.getElementById("root")).render(\n'
        "  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n")
    css = tree_css(roots_for_css)
    for old, new in asset_map.items():
        css = css.replace(old, new)
    files["frontend/src/styles/tokens.css"] = tokens_css(tokens) + "\n"
    files["frontend/src/styles/app.css"] = '@import "./tokens.css";\n\n' + BASE_CSS + "\n" + css + "\n"
    paths = {e["name"]: plural(e["name"]) for e in entities}
    files["frontend/src/api.js"] = API_JS.replace("__PATHS__", json.dumps(paths, indent=2))
    files["frontend/src/lib/DataForm.jsx"] = DATAFORM_JSX
    files["frontend/src/lib/Collection.jsx"] = COLLECTION_JSX

    first_seo = (pages[0].get("seo") if pages else {}) or {}
    files["frontend/index.html"] = (
        '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
        f'  <title>{_html(project["name"])}</title>\n'
        f'  <meta name="description" content="{_html(first_seo.get("description") or project.get("description", ""))}" />\n'
        '  <link rel="preconnect" href="https://fonts.googleapis.com" />\n'
        '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
        # Non-blocking web fonts: the page renders with fallback fonts if the font CDN is slow or down.
        f'  <link rel="stylesheet" href="{_html(google_fonts_url(tokens))}" media="print" '
        'onload="this.media=\'all\'" />\n'
        '</head>\n<body>\n  <div id="root"></div>\n  <script type="module" src="/src/main.jsx"></script>\n'
        "</body>\n</html>\n")
    files["frontend/package.json"] = json.dumps({
        "name": re.sub(r"[^a-z0-9-]+", "-", project["name"].lower()).strip("-") or "aidevs-app",
        "private": True, "version": "1.0.0", "type": "module",
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
        "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1", "react-router-dom": "^7.18.5"},
        "devDependencies": {"@vitejs/plugin-react": "^4.7.0", "vite": "^6.4.6"},
    }, indent=2) + "\n"
    files["frontend/vite.config.js"] = (
        'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\n\n'
        "export default defineConfig({ plugins: [react()], server: { port: 5173 } });\n")
    files["frontend/.env.example"] = "VITE_API_URL=http://localhost:5000\n"
    sitemap_urls = "".join(f"  <url><loc>https://example.com{p['route']}</loc></url>\n" for p in pages)
    files["frontend/public/sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap_urls}</urlset>\n")
    files["frontend/public/robots.txt"] = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    files["frontend/public/_redirects"] = "/*    /index.html   200\n"
    return files, sourcemap


def _html(value):
    import html
    return html.escape(str(value or ""), quote=True)
