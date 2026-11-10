"""Shared prompt fragments for the AIDevs studio agents."""

SCHEMA_GUIDE = """COMPONENT SCHEMA (the ONLY output format for UI):
Node = {"type": T, "name": "Human readable layer name", "tag": optional, "props": {...},
        "styles": {"base": {cssProp: value}, "tablet": {...}, "mobile": {...}}, "children": [Node]}
Types T and props:
- "section"  (tag: section|header|footer|nav|main|article)  props: {"anchor": "kebab-id"}  -> top-level page block
- "container" (tag: div|ul|li|article)  layout box; use display flex/grid
- "heading"  tag h1..h6, props {"text"}
- "text"     tag p|span|small|blockquote|strong, props {"text"}
- "button"   props {"text", "href"? , "variant": "primary"|"secondary"}  (inside a form without href = submit)
- "link"     props {"text", "href"}
- "image"    props {"src", "alt"}   src MUST be https://picsum.photos/seed/<word>/<w>/<h>
- "icon"     props {"text": one emoji or symbol, "label"}
- "divider"
- "form"     props {"entity": <data model name>, "submitText", "successMessage"} children = inputs + one button
- "input"    props {"label", "name": <field name>, "inputType": text|email|tel|number|password|url|date, "placeholder", "required"}
- "textarea" props {"label", "name", "rows", "required"};  "select" props {"label", "name", "options": [..]}
- "collection" props {"entity": <data model name>, "limit": n, "emptyText"}; EXACTLY ONE child = card template.
   Inside the template use {{field}} bindings in text/src/alt, e.g. {"type":"heading","props":{"text":"{{title}}"}}
Only section/container/form/collection may have children.
Styles: camelCase CSS (padding, display, gridTemplateColumns, gap, fontSize, color, background, borderRadius,
boxShadow, maxWidth, margin, textAlign, alignItems, justifyContent, flexDirection, flexWrap, ...). No url() except https.
Use design tokens: var(--color-primary|secondary|accent|background|surface|text|muted|on-primary),
var(--font-heading), var(--font-body), var(--radius), var(--max-width).
Responsive: put overrides in "tablet" (<=1024px) and "mobile" (<=640px), e.g. grids collapse to 1 column on mobile,
large headings shrink, section padding shrinks. Desktop styles go in "base".
Center content with an inner container {maxWidth: "var(--max-width)", margin: "0 auto", width: "100%"}.
Never output scripts, event handlers, HTML strings or markdown. Write real, specific, original copy (no lorem ipsum)."""

PERMISSIONS_GUIDE = """Data model ("entity") = {"name": snake_case singular, "label", "fields": [{"name": snake_case,
"type": string|text|integer|number|boolean|date|datetime|email|url|image, "required": bool}],
"permissions": {"read","create","update","delete": public|auth|owner|admin}, "sample_data": [rows]}
Permission levels: public=anyone, auth=any signed-in user, owner=the creating user (or admin), admin=site admin.
Typical: catalog content read public / write admin; contact messages create public / read admin;
per-user data (wishlist, orders, bookings) all owner (create auth). Never make update/delete public.
Do not define a "user" entity: user accounts and login already exist. Fields id/owner_id/created_at are automatic."""


FLAT_FORMAT = """OUTPUT FORMAT - FLAT NODE LIST (do NOT nest "children" arrays; deep nesting breaks JSON):
Each node is one object in a flat array: {"id": "short unique id", "parent": "<parent id>" or null, "type": ...,
"name": ..., "tag": optional, "props": optional, "styles": optional}.
Top-level page sections have "parent": null. List every parent BEFORE its children and siblings in display order.
Example: [{"id":"s1","parent":null,"type":"section","name":"Hero","props":{"anchor":"hero"}},
{"id":"c1","parent":"s1","type":"container","name":"Hero Content","styles":{"base":{"display":"flex"}}},
{"id":"h1","parent":"c1","type":"heading","tag":"h1","name":"Headline","props":{"text":"..."}}]"""
