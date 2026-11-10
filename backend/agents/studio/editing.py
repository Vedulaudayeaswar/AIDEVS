"""Feature agent (project-wide targeted changes) + Visual Editing agent (selected element)."""
import json
import re

from agents.studio.architect import make_validator
from agents.studio.prompts import FLAT_FORMAT, PERMISSIONS_GUIDE, SCHEMA_GUIDE
from services.ai_client import get_ai_client
from services.schema import SchemaError, sanitize_entity, sanitize_subtree, walk

ROUTE_RE = re.compile(r"^/[a-z0-9\-/]{0,60}$")

FEATURE_SYSTEM = f"""You are the AIDevs Orchestrator working with the Backend, Database and Frontend agents.
The user asks for a change to an EXISTING application. Make the smallest set of targeted changes that fully
implements it: new/updated data models (backend API + database are generated from them automatically),
new pages or new sections on existing pages, and navigation links. Never recreate existing pages or
sections that do not need to change. If the message is only a question, answer it and change nothing.
{PERMISSIONS_GUIDE}
{SCHEMA_GUIDE}
{FLAT_FORMAT}
Return ONLY JSON:
{{"reply": "short explanation to the user of what you changed or the answer",
 "entities": [{{"op": "add"|"update", ...entity}}],
 "pages": [{{"op": "add", "name": str, "route": "/kebab", "nodes": [flat node]}} |
           {{"op": "add_sections", "route": existing route, "position": "start"|"end", "nodes": [flat node]}}],
 "nav": [{{"label": str, "href": "/route"}}],
 "tokens": optional partial design tokens to change,
 "remember": ["durable decisions/preferences worth remembering"]}}
For "update" of an entity, return the COMPLETE new field list (existing fields you keep + new ones).
COMPACT OUTPUT (hard limit ~3,500 tokens): at most 3 new sections per page, omit empty objects and default styles."""

EDIT_SYSTEM = f"""You are the AIDevs Visual Editing Agent. You receive ONE selected element (a node subtree)
and an instruction. Return the modified subtree, preserving node ids of elements you keep, and keeping the
same root "type". Change only what the instruction asks (and what good design needs for it).
{SCHEMA_GUIDE}
Return ONLY JSON: {{"node": Node, "summary": "one sentence describing the change"}}
Keep the JSON compact (omit empty objects; only meaningful styles) - it must stay under ~3,000 tokens."""


def validate_feature_plan(project_entities, routes):
    def validate(data):
        if not isinstance(data, dict):
            raise SchemaError("expected an object")
        entities = {e["name"]: e for e in project_entities}
        out_entities = []
        for raw in (data.get("entities") or [])[:6]:
            if not isinstance(raw, dict):
                continue
            ent = sanitize_entity(raw)
            op = "update" if ent["name"] in entities else "add"
            out_entities.append({"op": op, "entity": ent})
            entities[ent["name"]] = ent
        page_ops = []
        all_routes = set(routes)
        for raw in (data.get("pages") or [])[:6]:
            if not isinstance(raw, dict):
                continue
            op = raw.get("op")
            route = str(raw.get("route", "")).lower().rstrip("/") or "/"
            if not ROUTE_RE.match(route):
                raise SchemaError(f"invalid route {route}")
            if op == "add":
                if route in all_routes:
                    op = "add_sections"
                else:
                    all_routes.add(route)
            elif op != "add_sections" or route not in all_routes:
                raise SchemaError(f"page op must be add (new route) or add_sections (existing route): {route}")
            validated = make_validator(entities)({"nodes": raw["nodes"]} if isinstance(raw.get("nodes"), list)
                                                 else {"sections": raw.get("sections") or []})
            page_ops.append({"op": op, "route": route, "name": str(raw.get("name") or route.strip('/').title())[:60],
                             "position": "start" if raw.get("position") == "start" else "end",
                             "tree": validated["tree"], "seo": validated["seo"]})
        nav = []
        for item in (data.get("nav") or [])[:6]:
            if isinstance(item, dict) and str(item.get("href", "")).rstrip("/") in all_routes | {""}:
                nav.append({"label": str(item.get("label", ""))[:40], "href": str(item["href"]) or "/"})
        return {
            "reply": str(data.get("reply", ""))[:2000] or "Done.",
            "entities": out_entities, "pages": page_ops, "nav": nav,
            # Partial token changes; merged with the project's tokens (and re-sanitized) when applied.
            "tokens": data["tokens"] if isinstance(data.get("tokens"), dict) and data["tokens"] else None,
            "remember": [str(r)[:300] for r in (data.get("remember") or [])[:5] if isinstance(r, str)],
        }
    return validate


def plan_feature(message, context, project_entities, routes, *, user_id=None, project_id=None):
    user = f"PROJECT CONTEXT:\n{context}\n\nUSER REQUEST:\n{message.strip()[:3000]}"
    result = get_ai_client().complete_json(
        "feature", FEATURE_SYSTEM, user, validator=validate_feature_plan(project_entities, routes),
        user_id=user_id, project_id=project_id, max_tokens=9000)
    return result.data


def edit_node(node, instruction, tokens, entities, context="", *, page_ids=(), user_id=None, project_id=None):
    original_ids = {n["id"] for n, _ in walk(node)}

    def validate(data):
        if not isinstance(data, dict) or not isinstance(data.get("node"), dict):
            raise SchemaError('expected {"node": {...}}')
        new = dict(data["node"])
        if new.get("type") != node["type"]:
            raise SchemaError(f"root type must stay '{node['type']}'")
        new["id"] = node["id"]
        # ids from the original subtree may be reused; everything else on the page must not collide.
        clean, warnings = sanitize_subtree(new, existing_ids=set(page_ids) - original_ids)
        if node.get("shared"):
            clean["shared"] = node["shared"]
        entity_map = {e["name"]: e for e in entities}
        for n, _ in walk(clean):
            if n["type"] in ("form", "collection") and n["props"].get("entity") not in entity_map and \
                    n["props"].get("entity") not in ("auth_login", "auth_register"):
                raise SchemaError(f"unknown entity {n['props'].get('entity')}; valid: {sorted(entity_map)}")
        return {"node": clean, "summary": str(data.get("summary", ""))[:300], "warnings": warnings}

    user = (f"Design tokens: {json.dumps(tokens)}\nData models: "
            f"{json.dumps([{'name': e['name'], 'fields': [f['name'] for f in e['fields']]} for e in entities])}\n"
            f"{('Project memory:' + chr(10) + context) if context else ''}\n\nSELECTED ELEMENT:\n"
            f"{json.dumps(node)[:12000]}\n\nINSTRUCTION: {instruction.strip()[:2000]}")
    result = get_ai_client().complete_json("edit", EDIT_SYSTEM, user, validator=validate,
                                           user_id=user_id, project_id=project_id, max_tokens=7000)
    return result.data
