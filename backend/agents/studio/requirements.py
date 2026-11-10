"""Requirement Analysis + Research agents: idea (and optional reference site) -> AppSpec."""
import json
import re

from agents.studio.prompts import PERMISSIONS_GUIDE
from services.ai_client import get_ai_client
from services.schema import SchemaError, sanitize_entity, sanitize_tokens
from services.templates import TEMPLATES

ROUTE_RE = re.compile(r"^/[a-z0-9\-/]{0,60}$")
SECTION_KINDS = set(TEMPLATES) | {"custom"}

SYSTEM = f"""You are the Requirement Analysis Agent of AIDevs, a senior product architect.
Turn a short website/app idea into a complete, buildable application specification.
Infer everything the user did not say: audience, brand, palette, typography, pages, sections, user journeys,
data models, auth, SEO. Only include pages the product genuinely needs (typically 2-6). Do not pad.
{PERMISSIONS_GUIDE}
Section "kind" must be one of: {", ".join(sorted(SECTION_KINDS))}. Navbar/footer are shared and added automatically,
so do NOT list them as sections. Use "collection_grid" for lists of data and "contact_form" for forms.
Every form/collection must reference an entity you define.
Return ONLY JSON:
{{"name": str, "summary": str, "site_type": str, "audience": str,
 "brand": {{"voice": str, "tagline": str}},
 "tokens": {{"colors": {{"primary": hex, "secondary": hex, "accent": hex, "background": hex, "surface": hex,
            "text": hex, "muted": hex, "onPrimary": hex}}, "fonts": {{"heading": GoogleFontName, "body": GoogleFontName}},
            "radius": "12px"}},
 "pages": [{{"name": str, "route": "/" or "/kebab", "purpose": str,
            "sections": [{{"kind": str, "brief": "what this section says/does", "entity": optional entity name}}]}}],
 "entities": [entity...],
 "features": [str], "user_journeys": [str],
 "auth": {{"required": bool, "notes": str}},
 "seo": {{"title": str, "description": str, "keywords": [str]}},
 "open_questions": [str]}}
Colors must have WCAG AA contrast (text on background, onPrimary on primary)."""


def validate_spec(data):
    if not isinstance(data, dict):
        raise SchemaError("spec must be an object")
    name = str(data.get("name") or "").strip()[:80]
    if not name:
        raise SchemaError("spec.name is required")
    entities, names = [], set()
    for raw in (data.get("entities") or [])[:12]:
        try:
            ent = sanitize_entity(raw)
        except SchemaError:
            continue
        if ent["name"] not in names:
            names.add(ent["name"])
            entities.append(ent)

    pages, routes = [], set()
    for raw in (data.get("pages") or [])[:8]:
        if not isinstance(raw, dict):
            continue
        route = str(raw.get("route") or "").strip().lower().rstrip("/") or "/"
        if not ROUTE_RE.match(route) or route in routes:
            continue
        routes.add(route)
        sections = []
        for s in (raw.get("sections") or [])[:10]:
            if not isinstance(s, dict):
                continue
            kind = s.get("kind") if s.get("kind") in SECTION_KINDS else "custom"
            if kind in ("navbar", "footer"):
                continue
            entity = s.get("entity") if s.get("entity") in names else None
            if kind == "collection_grid" and not entity:
                kind = "custom"
            sections.append({"kind": kind, "brief": str(s.get("brief", ""))[:400], "entity": entity})
        pages.append({"name": str(raw.get("name") or route.strip("/").title() or "Home")[:60],
                      "route": route, "purpose": str(raw.get("purpose", ""))[:300], "sections": sections})
    if not pages:
        raise SchemaError("spec must contain at least one page")
    if "/" not in routes:
        pages[0]["route"] = "/"
    pages.sort(key=lambda p: p["route"] != "/")

    # A contact section needs a data model to submit into.
    if any(s["kind"] == "contact_form" for p in pages for s in p["sections"]) and \
            not any(e["name"] == "contact_message" for e in entities):
        entities.append(sanitize_entity({
            "name": "contact_message", "label": "Contact messages",
            "fields": [{"name": "name", "type": "string", "required": True},
                       {"name": "email", "type": "email", "required": True},
                       {"name": "message", "type": "text", "required": True}],
            "permissions": {"read": "admin", "create": "public", "update": "admin", "delete": "admin"}}))

    def strs(key, n=12):
        return [str(x)[:300] for x in (data.get(key) or [])[:n] if isinstance(x, (str, int, float))]

    brand = data.get("brand") if isinstance(data.get("brand"), dict) else {}
    seo = data.get("seo") if isinstance(data.get("seo"), dict) else {}
    auth = data.get("auth") if isinstance(data.get("auth"), dict) else {}
    return {
        "name": name, "summary": str(data.get("summary", ""))[:600],
        "site_type": str(data.get("site_type", ""))[:60], "audience": str(data.get("audience", ""))[:300],
        "brand": {"voice": str(brand.get("voice", ""))[:200], "tagline": str(brand.get("tagline", ""))[:200]},
        "tokens": sanitize_tokens(data.get("tokens"), ensure_contrast=True),
        "pages": pages, "entities": entities,
        "features": strs("features"), "user_journeys": strs("user_journeys"),
        "auth": {"required": bool(auth.get("required")), "notes": str(auth.get("notes", ""))[:300]},
        "seo": {"title": str(seo.get("title", name))[:70], "description": str(seo.get("description", ""))[:170],
                "keywords": [str(k)[:40] for k in (seo.get("keywords") or [])[:12]]},
        "open_questions": strs("open_questions", 6),
    }


def summarize_reference(reference):
    """Compact the crawler output for the prompt."""
    pages = []
    for p in reference.get("pages", [])[:5]:
        pages.append({
            "url": p["url"], "title": p["title"], "description": p["description"],
            "nav": [n["label"] for n in p["nav"]][:10], "headings": p["headings"][:10],
            "sections": [{k: s[k] for k in ("tag", "hint", "heading", "images", "forms", "inputs")}
                         for s in p["sections"][:14]],
            "colors": p["colors"], "fonts": p["fonts"],
        })
    return json.dumps(pages)[:7000]


def plan_application(prompt, *, reference=None, choices=None, user_id=None):
    user = f"IDEA:\n{prompt.strip()[:4000]}"
    if reference:
        user += ("\n\nREFERENCE WEBSITE ANALYSIS (use for structure/design inspiration only; write original copy, "
                 "do not reuse their brand name, text or images):\n" + summarize_reference(reference))
        if choices:
            user += f"\nUser wants to borrow from the reference: {json.dumps(choices)[:800]}"
    result = get_ai_client().complete_json("plan", SYSTEM, user, validator=validate_spec,
                                           user_id=user_id, max_tokens=6000)
    return result.data
