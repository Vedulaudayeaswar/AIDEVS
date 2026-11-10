"""Reusable section library (component palette + deterministic fallbacks).

All templates are expressed in the controlled component schema and use design
token CSS variables, so they automatically follow each project's branding.
"""
from services.schema import new_node_id


def N(ntype, name, props=None, base=None, children=None, tag=None, tablet=None, mobile=None):
    node = {
        "id": new_node_id(), "type": ntype, "name": name, "props": props or {},
        "styles": {"base": base or {}, "tablet": tablet or {}, "mobile": mobile or {}},
        "children": children or [],
    }
    if tag:
        node["tag"] = tag
    return node


def _inner(children, name="Container", gap="24px", direction="column", align=None, extra=None):
    base = {"maxWidth": "var(--max-width)", "margin": "0 auto", "display": "flex",
            "flexDirection": direction, "gap": gap, "width": "100%"}
    if align:
        base["alignItems"] = align
    base.update(extra or {})
    return N("container", name, base=base, children=children)


def _section(name, children, anchor=None, base=None, tag="section", mobile=None):
    style = {"padding": "96px 24px", "background": "var(--color-background)"}
    style.update(base or {})
    props = {"anchor": anchor} if anchor else {}
    return N("section", name, props, style, children, tag=tag,
             mobile=mobile or {"padding": "64px 20px"})


def _heading(text, level="h2", name="Heading", size="40px", mobile_size="30px", align=None, color=None):
    base = {"fontSize": size, "fontWeight": "800", "lineHeight": "1.15",
            "fontFamily": "var(--font-heading)", "color": color or "var(--color-text)"}
    if align:
        base["textAlign"] = align
    return N("heading", name, {"text": text}, base, tag=level, mobile={"fontSize": mobile_size})


def _text(text, name="Text", size="18px", color="var(--color-muted)", align=None, extra=None):
    base = {"fontSize": size, "lineHeight": "1.6", "color": color}
    if align:
        base["textAlign"] = align
    base.update(extra or {})
    return N("text", name, {"text": text}, base)


def _button(text, href="#", variant="primary", name="Button"):
    primary = variant == "primary"
    base = {"display": "inline-flex", "alignItems": "center", "justifyContent": "center",
            "padding": "14px 28px", "borderRadius": "var(--radius)", "fontWeight": "700",
            "fontSize": "16px", "textDecoration": "none",
            "background": "var(--color-primary)" if primary else "transparent",
            "color": "var(--color-on-primary)" if primary else "var(--color-text)",
            "border": "2px solid var(--color-primary)"}
    return N("button", name, {"text": text, "href": href, "variant": variant}, base)


def navbar(ctx):
    links = ctx.get("nav") or [{"label": "Home", "href": "/"}]
    return N("section", "Navbar", {}, {
        "position": "sticky", "top": "0", "zIndex": "50", "padding": "16px 24px",
        "background": "var(--color-background)", "borderBottom": "1px solid rgba(15,23,42,0.08)",
    }, [
        _inner([
            N("link", "Logo", {"text": ctx.get("name", "Brand"), "href": "/"},
              {"fontSize": "22px", "fontWeight": "800", "color": "var(--color-text)",
               "textDecoration": "none", "fontFamily": "var(--font-heading)"}),
            N("container", "Navigation Links", base={"display": "flex", "gap": "28px",
                                                     "alignItems": "center", "flexWrap": "wrap"},
              mobile={"gap": "14px"},
              children=[N("link", f"Nav: {link['label']}", {"text": link["label"], "href": link["href"]},
                          {"color": "var(--color-text)", "textDecoration": "none",
                           "fontWeight": "500", "fontSize": "15px"}) for link in links[:7]]),
        ], name="Navbar Inner", direction="row", align="center",
            extra={"justifyContent": "space-between", "flexWrap": "wrap", "gap": "12px"}),
    ], tag="header")


def hero(ctx):
    return _section("Hero Section", [
        _inner([
            N("text", "Eyebrow", {"text": ctx.get("tagline", "Welcome")},
              {"fontSize": "14px", "fontWeight": "700", "letterSpacing": "0.12em",
               "textTransform": "uppercase", "color": "var(--color-primary)"}),
            _heading(ctx.get("headline", f"Welcome to {ctx.get('name', 'our site')}"), "h1",
                     "Hero Heading", "64px", "38px", "center"),
            _text(ctx.get("subheadline", "Everything you need, beautifully designed."),
                  "Hero Description", "20px", align="center", extra={"maxWidth": "680px"}),
            N("container", "CTA Buttons", base={"display": "flex", "gap": "16px",
                                                "flexWrap": "wrap", "justifyContent": "center"},
              children=[_button(ctx.get("cta", "Get started"), ctx.get("cta_href", "#contact"),
                                name="Primary CTA"),
                        _button("Learn more", "#features", "secondary", "Secondary CTA")]),
        ], "Hero Content", gap="24px", align="center"),
    ], anchor="home", base={"padding": "128px 24px", "background":
                            "linear-gradient(180deg, var(--color-surface), var(--color-background))"},
        mobile={"padding": "80px 20px"})


def features(ctx):
    items = ctx.get("features") or [
        {"title": "Fast", "text": "Optimized for speed on every device."},
        {"title": "Reliable", "text": "Built on proven, secure foundations."},
        {"title": "Delightful", "text": "Thoughtful design in every detail."},
    ]
    cards = [N("container", f"Feature Card {i + 1}", base={
        "padding": "32px", "borderRadius": "var(--radius)", "background": "var(--color-surface)",
        "display": "flex", "flexDirection": "column", "gap": "12px",
        "border": "1px solid rgba(15,23,42,0.06)"}, children=[
        N("icon", "Icon", {"text": item.get("icon", "✦"), "label": item.get("title", "")},
          {"fontSize": "28px", "color": "var(--color-primary)"}),
        _heading(item.get("title", "Feature"), "h3", "Feature Title", "22px", "20px"),
        _text(item.get("text", ""), "Feature Text", "16px"),
    ]) for i, item in enumerate(items[:6])]
    return _section("Features", [
        _inner([
            _heading(ctx.get("features_title", "Why choose us"), "h2", "Features Heading", align="center"),
            N("container", "Features Grid", base={
                "display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "24px"},
              tablet={"gridTemplateColumns": "repeat(2, 1fr)"},
              mobile={"gridTemplateColumns": "1fr"}, children=cards),
        ], "Features Content", gap="40px"),
    ], anchor="features")


def stats(ctx):
    items = ctx.get("stats") or [{"value": "10k+", "label": "Customers"},
                                 {"value": "99.9%", "label": "Uptime"},
                                 {"value": "24/7", "label": "Support"}]
    return _section("Stats", [
        N("container", "Stats Grid", base={
            "maxWidth": "var(--max-width)", "margin": "0 auto", "display": "grid",
            "gridTemplateColumns": f"repeat({min(len(items), 4)}, 1fr)", "gap": "24px"},
          mobile={"gridTemplateColumns": "1fr 1fr"}, children=[
            N("container", f"Stat {i + 1}", base={"textAlign": "center", "display": "flex",
                                                  "flexDirection": "column", "gap": "6px"}, children=[
                _heading(s["value"], "h3", "Stat Value", "44px", "32px", "center", "var(--color-primary)"),
                _text(s["label"], "Stat Label", "16px", align="center")])
            for i, s in enumerate(items[:4])]),
    ], base={"padding": "64px 24px", "background": "var(--color-surface)"})


def about(ctx):
    return _section("About", [
        _inner([
            _heading(ctx.get("about_title", f"About {ctx.get('name', 'us')}"), "h2", "About Heading"),
            _text(ctx.get("about_text", "We are a passionate team dedicated to quality."),
                  "About Text", extra={"maxWidth": "760px"}),
        ], "About Content", gap="20px"),
    ], anchor="about")


def pricing(ctx):
    plans = ctx.get("plans") or [
        {"name": "Starter", "price": "$0", "text": "For individuals getting started."},
        {"name": "Pro", "price": "$19", "text": "For growing teams that need more."},
        {"name": "Business", "price": "$49", "text": "Advanced controls and support."},
    ]
    return _section("Pricing", [
        _inner([
            _heading("Simple, transparent pricing", "h2", "Pricing Heading", align="center"),
            N("container", "Pricing Grid", base={"display": "grid",
                                                 "gridTemplateColumns": "repeat(3, 1fr)", "gap": "24px"},
              tablet={"gridTemplateColumns": "1fr"}, children=[
                N("container", f"Plan: {p['name']}", base={
                    "padding": "32px", "borderRadius": "var(--radius)", "display": "flex",
                    "flexDirection": "column", "gap": "14px", "background": "var(--color-surface)",
                    "border": "1px solid rgba(15,23,42,0.08)"}, children=[
                    _heading(p["name"], "h3", "Plan Name", "22px", "20px"),
                    _heading(p["price"], "h4", "Plan Price", "40px", "32px", color="var(--color-primary)"),
                    _text(p["text"], "Plan Description", "16px"),
                    _button("Choose plan", "#contact", name="Plan CTA")])
                for p in plans[:4]]),
        ], "Pricing Content", gap="40px"),
    ], anchor="pricing")


def testimonials(ctx):
    quotes = ctx.get("testimonials") or [
        {"quote": "Absolutely transformed how we work.", "author": "Alex R."},
        {"quote": "Beautiful, fast and easy to use.", "author": "Priya S."},
    ]
    return _section("Testimonials", [
        _inner([
            _heading("What people say", "h2", "Testimonials Heading", align="center"),
            N("container", "Testimonials Grid", base={
                "display": "grid", "gridTemplateColumns": "repeat(2, 1fr)", "gap": "24px"},
              mobile={"gridTemplateColumns": "1fr"}, children=[
                N("container", f"Testimonial {i + 1}", base={
                    "padding": "28px", "borderRadius": "var(--radius)", "background": "var(--color-surface)",
                    "display": "flex", "flexDirection": "column", "gap": "12px"}, children=[
                    N("text", "Quote", {"text": f"“{q['quote']}”"},
                      {"fontSize": "18px", "lineHeight": "1.6", "color": "var(--color-text)"},
                      tag="blockquote"),
                    _text(f"— {q['author']}", "Author", "15px")])
                for i, q in enumerate(quotes[:4])]),
        ], "Testimonials Content", gap="40px"),
    ], anchor="testimonials", base={"background": "var(--color-background)"})


def cta(ctx):
    return _section("Call To Action", [
        _inner([
            _heading(ctx.get("cta_title", "Ready to get started?"), "h2", "CTA Heading",
                     align="center", color="var(--color-on-primary)"),
            _text(ctx.get("cta_text", "Join today — it only takes a minute."), "CTA Text",
                  align="center", color="var(--color-on-primary)"),
            N("container", "CTA Row", base={"display": "flex", "justifyContent": "center"}, children=[
                N("button", "CTA Button", {"text": ctx.get("cta", "Get started"), "href": "#contact"},
                  {"padding": "14px 28px", "borderRadius": "var(--radius)", "fontWeight": "700",
                   "background": "var(--color-on-primary)", "color": "var(--color-primary)",
                   "textDecoration": "none"})]),
        ], "CTA Content", gap="20px", align="center"),
    ], base={"background": "var(--color-primary)"})


def contact_form(ctx):
    entity = ctx.get("contact_entity", "contact_message")
    field_style = {"display": "flex", "flexDirection": "column", "gap": "6px",
                   "fontWeight": "600", "fontSize": "14px", "color": "var(--color-text)"}
    return _section("Contact", [
        _inner([
            _heading(ctx.get("contact_title", "Get in touch"), "h2", "Contact Heading", align="center"),
            _text("We usually reply within one business day.", "Contact Text", align="center"),
            N("form", "Contact Form", {"entity": entity, "submitText": "Send message",
                                       "successMessage": "Thanks! Your message was sent."},
              {"display": "flex", "flexDirection": "column", "gap": "16px", "width": "100%",
               "maxWidth": "560px", "margin": "0 auto"}, [
                N("input", "Name Field", {"label": "Name", "name": "name", "required": True,
                                          "placeholder": "Your name"}, field_style),
                N("input", "Email Field", {"label": "Email", "name": "email", "inputType": "email",
                                           "required": True, "placeholder": "you@example.com"},
                  field_style),
                N("textarea", "Message Field", {"label": "Message", "name": "message",
                                                "required": True, "rows": 5}, field_style),
                N("button", "Submit Button", {"text": "Send message"}, {
                    "padding": "14px 28px", "borderRadius": "var(--radius)", "fontWeight": "700",
                    "background": "var(--color-primary)", "color": "var(--color-on-primary)",
                    "border": "none", "cursor": "pointer"}),
            ]),
        ], "Contact Content", gap="20px"),
    ], anchor="contact", base={"background": "var(--color-surface)"})


def collection_grid(ctx):
    entity = ctx.get("entity") or {"name": "item", "label": "Items",
                                   "fields": [{"name": "title", "type": "string"}]}
    fields = {f["name"]: f["type"] for f in entity.get("fields", [])}
    title_field = next((n for n, t in fields.items() if t == "string"), next(iter(fields), "title"))
    image_field = next((n for n, t in fields.items() if t == "image"), None)
    price_field = next((n for n in fields if n in ("price", "cost", "amount")), None)
    desc_field = next((n for n, t in fields.items() if t == "text"), None)
    card_children = []
    if image_field:
        card_children.append(N("image", "Item Image", {"src": f"{{{{{image_field}}}}}",
                                                       "alt": f"{{{{{title_field}}}}}"},
                               {"width": "100%", "aspectRatio": "4 / 3", "objectFit": "cover",
                                "borderRadius": "var(--radius)"}))
    card_children.append(_heading(f"{{{{{title_field}}}}}", "h3", "Item Title", "20px", "18px"))
    if desc_field:
        card_children.append(_text(f"{{{{{desc_field}}}}}", "Item Description", "15px"))
    if price_field:
        card_children.append(N("text", "Item Price", {"text": f"${{{{{price_field}}}}}"},
                               {"fontWeight": "800", "fontSize": "18px", "color": "var(--color-primary)"}))
    return _section(f"{entity.get('label', 'Items')} Grid", [
        _inner([
            _heading(ctx.get("collection_title", entity.get("label", "Items")), "h2",
                     "Collection Heading"),
            N("collection", f"{entity.get('label', 'Items')} List",
              {"entity": entity["name"], "limit": 12, "emptyText": "Nothing here yet."},
              {"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "24px"},
              [N("container", "Item Card", base={
                  "display": "flex", "flexDirection": "column", "gap": "10px", "padding": "16px",
                  "borderRadius": "var(--radius)", "background": "var(--color-surface)",
                  "border": "1px solid rgba(15,23,42,0.06)"}, children=card_children)],
              tablet={"gridTemplateColumns": "repeat(2, 1fr)"},
              mobile={"gridTemplateColumns": "1fr"}),
        ], "Collection Content", gap="32px"),
    ], anchor=entity["name"].replace("_", "-"))


def footer(ctx):
    links = ctx.get("nav") or []
    return N("section", "Footer", {}, {
        "padding": "48px 24px", "background": "var(--color-text)", "color": "var(--color-background)",
    }, [
        _inner([
            _heading(ctx.get("name", "Brand"), "h3", "Footer Brand", "22px", "20px",
                     color="var(--color-background)"),
            N("container", "Footer Links", base={"display": "flex", "gap": "20px", "flexWrap": "wrap"},
              children=[N("link", f"Footer: {link['label']}", {"text": link["label"], "href": link["href"]},
                          {"color": "var(--color-background)", "opacity": "0.8",
                           "textDecoration": "none"}) for link in links[:8]]),
            N("text", "Copyright", {"text": f"© {ctx.get('year', 2026)} {ctx.get('name', 'Brand')}. All rights reserved."},
              {"fontSize": "14px", "opacity": "0.6", "color": "var(--color-background)"}),
        ], "Footer Inner", gap="16px"),
    ], tag="footer")


TEMPLATES = {
    "navbar": ("Navbar", navbar),
    "hero": ("Hero", hero),
    "features": ("Features grid", features),
    "stats": ("Stats", stats),
    "about": ("About", about),
    "pricing": ("Pricing", pricing),
    "testimonials": ("Testimonials", testimonials),
    "cta": ("Call to action", cta),
    "contact_form": ("Contact form", contact_form),
    "collection_grid": ("Data collection grid", collection_grid),
    "footer": ("Footer", footer),
}

# Single elements available in the editor's insert palette.
ELEMENTS = {
    "heading": lambda: _heading("New heading", "h2", "Heading", "36px", "28px"),
    "text": lambda: _text("New paragraph text.", "Paragraph"),
    "button": lambda: _button("Button", "#", name="Button"),
    "image": lambda: N("image", "Image", {"src": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200",
                                          "alt": "Image description"},
                       {"width": "100%", "maxWidth": "640px", "borderRadius": "var(--radius)"}),
    "container": lambda: N("container", "Container", base={"display": "flex", "flexDirection": "column",
                                                           "gap": "16px", "padding": "24px"}),
    "row": lambda: N("container", "Row", base={"display": "flex", "flexDirection": "row", "gap": "16px",
                                               "alignItems": "center", "flexWrap": "wrap"}),
    "grid": lambda: N("container", "Grid", base={"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)",
                                                 "gap": "24px"}, mobile={"gridTemplateColumns": "1fr"}),
    "divider": lambda: N("divider", "Divider", base={"border": "none", "borderTop": "1px solid rgba(15,23,42,0.1)",
                                                     "width": "100%"}),
    "link": lambda: N("link", "Link", {"text": "Link", "href": "#"}, {"color": "var(--color-primary)"}),
    "input": lambda: N("input", "Input", {"label": "Label", "name": "field", "placeholder": ""},
                       {"display": "flex", "flexDirection": "column", "gap": "6px"}),
}


def palette():
    return {
        "sections": [{"key": k, "label": v[0]} for k, v in TEMPLATES.items()],
        "elements": [{"key": k, "label": k.capitalize()} for k in ELEMENTS],
    }


def build_section(key, ctx):
    if key not in TEMPLATES:
        raise KeyError(key)
    return TEMPLATES[key][1](ctx)


def build_element(key):
    if key not in ELEMENTS:
        raise KeyError(key)
    return ELEMENTS[key]()
