"""UI/UX Architect + Frontend agents: spec -> validated page trees."""
import json
from datetime import datetime

from agents.studio.prompts import FLAT_FORMAT, SCHEMA_GUIDE
from services.ai_client import get_ai_client
from services import templates as T
from services.schema import SchemaError, all_ids, sanitize_subtree, sanitize_tree, unflatten, walk


def normalize_headings(tree):
    """Exactly one h1 per page (SEO/accessibility): promote the first heading if none,
    demote extra h1s to h2. Deterministic, so the model does not need another round-trip."""
    headings = [n for n, _ in walk(tree) if n["type"] == "heading"]
    h1s = [n for n in headings if n.get("tag") == "h1"]
    if not h1s and headings:
        headings[0]["tag"] = "h1"
    for extra in h1s[1:]:
        extra["tag"] = "h2"
    return tree


SYSTEM = f"""You are the UI/UX Architect and Frontend Engineer of AIDevs. You design premium, modern,
conversion-focused, accessible, fully responsive web pages and output them in a strict component schema.
{SCHEMA_GUIDE}
{FLAT_FORMAT}
Return ONLY JSON: {{"nodes": [flat node, ...], "seo": {{"title": str, "description": str}}}}
Rules: 3-5 top-level "section" nodes; exactly one h1 on the page; give every section a meaningful "name"
(it is shown in the layers panel) and an "anchor"; use rich layouts (split hero, card grids, stats, testimonials)
with generous spacing, consistent radius and subtle shadows; use the brand palette via tokens.
COMPACT OUTPUT (stay under ~3,500 tokens): omit empty "props", "tablet" and "mobile" objects; only include style
properties that matter; at most 4 cards per grid; short, specific copy; no comments or whitespace padding."""


def layout_context(spec, pages):
    nav = [{"label": p["name"], "href": p["route"]} for p in pages][:6]
    return {"name": spec.get("name", "Brand"), "nav": nav, "year": datetime.now().year,
            "tagline": spec.get("brand", {}).get("tagline", "")}


def build_layout(spec, pages):
    ctx = layout_context(spec, pages)
    # Everything persisted must be in normalized schema form (tags, styles, ids).
    header, _ = sanitize_subtree(T.navbar(ctx))
    footer, _ = sanitize_subtree(T.footer(ctx), existing_ids=all_ids(header))
    return {"header": header, "footer": footer}


def make_validator(entity_map):
    def validate(data):
        if isinstance(data, dict) and isinstance(data.get("nodes"), list):
            data = {**data, "sections": unflatten(data["nodes"])}  # flat format (preferred)
        if not isinstance(data, dict) or not isinstance(data.get("sections"), list) or not data["sections"]:
            raise SchemaError('expected {"nodes": [...]} with at least one top-level section')
        tree, warnings = sanitize_tree({"type": "page", "name": "Page", "children": data["sections"][:10]})
        normalize_headings(tree)
        if len(tree["children"]) == 0:
            raise SchemaError("no valid sections")
        for node, _ in walk(tree):
            p = node.get("props", {})
            if node["type"] in ("form", "collection"):
                ent = p.get("entity")
                if ent in ("auth_login", "auth_register") and node["type"] == "form":
                    continue
                if ent not in entity_map:
                    raise SchemaError(f"{node['type']} '{node['name']}' uses unknown entity '{ent}'. "
                                      f"Valid entities: {sorted(entity_map) or 'none (do not use forms/collections)'}")
                if node["type"] == "form":
                    fields = {f["name"] for f in entity_map[ent]["fields"]}
                    for c, _ in walk(node):
                        if c["type"] in ("input", "textarea", "select") and c["props"].get("name") not in fields:
                            raise SchemaError(f"form field '{c['props'].get('name')}' not in entity {ent} "
                                              f"fields {sorted(fields)}")
            if node["type"] == "collection" and len(node.get("children", [])) != 1:
                raise SchemaError(f"collection '{node['name']}' must have exactly one template child")
        seo = data.get("seo") if isinstance(data.get("seo"), dict) else {}
        return {"tree": tree, "warnings": warnings,
                "seo": {"title": str(seo.get("title", ""))[:70], "description": str(seo.get("description", ""))[:170]}}
    return validate


def generate_page(spec, page, entities, *, context="", reference_summary="", user_id=None, project_id=None):
    entity_map = {e["name"]: e for e in entities}
    entity_desc = json.dumps([{"name": e["name"], "label": e["label"],
                               "fields": [f"{f['name']}:{f['type']}{'*' if f['required'] else ''}" for f in e["fields"]],
                               "create": e["permissions"]["create"]} for e in entities])
    user = f"""Design the page "{page['name']}" (route {page['route']}).
Purpose: {page.get('purpose', '')}
Planned sections: {json.dumps(page.get('sections', []))}
Brand: {spec.get('name')} - {spec.get('summary', '')}. Audience: {spec.get('audience', '')}.
Voice: {spec.get('brand', {}).get('voice', '')}. Tagline: {spec.get('brand', {}).get('tagline', '')}
Design tokens: {json.dumps(spec.get('tokens', {}))}
Other pages (for links): {json.dumps([{'name': p['name'], 'route': p['route']} for p in spec.get('pages', [])])}
Data models (forms must use these entity + field names exactly; * = required, include every required field):
{entity_desc}
The shared navbar and footer already exist - do not create them.
{('Project memory:' + chr(10) + context) if context else ''}
{('Reference site structure (inspiration only):' + chr(10) + reference_summary) if reference_summary else ''}"""
    result = get_ai_client().complete_json("page", SYSTEM, user, validator=make_validator(entity_map),
                                           user_id=user_id, project_id=project_id, max_tokens=9000)
    return result.data


def fallback_page(spec, page, entities):
    """Deterministic page built from the section library (used when AI output fails validation)."""
    entity_map = {e["name"]: e for e in entities}
    brand = spec.get("brand", {})
    children = []
    for i, section in enumerate(page.get("sections") or [{"kind": "hero"}, {"kind": "features"}]):
        kind = section.get("kind")
        ctx = {"name": spec.get("name", "Brand"), "tagline": brand.get("tagline", ""),
               "headline": section.get("brief", "")[:80] if i == 0 and section.get("brief") else
               f"{spec.get('name', 'Welcome')}", "subheadline": spec.get("summary", "")[:200],
               "entity": entity_map.get(section.get("entity")),
               "contact_entity": "contact_message"}
        if kind == "custom" or kind not in T.TEMPLATES or kind in ("navbar", "footer"):
            kind = "hero" if i == 0 else "about"
            ctx["about_title"] = page["name"]
            ctx["about_text"] = section.get("brief") or page.get("purpose", "")
        if kind == "collection_grid" and not ctx["entity"]:
            kind = "about"
        if kind == "contact_form" and "contact_message" not in entity_map:
            kind = "cta"
        children.append(T.build_section(kind, ctx))
    tree, _ = sanitize_tree({"type": "page", "name": page["name"], "children": children})
    return {"tree": tree, "warnings": [], "seo": {"title": f"{page['name']} | {spec.get('name', '')}"[:70],
                                                  "description": page.get("purpose", "")[:170]}}
