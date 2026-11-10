"""Studio orchestrator: coordinates agents over persistent project state.

Pipeline for a new project:
  Requirements (+Research) -> user review -> Architect (layout + each page) ->
  Backend/DB (compiled from entities) -> Testing (checks) -> snapshot.

Every mutating AI operation snapshots the project first and applies its
validated result in a single DB transaction, so a failed or rejected AI step
never leaves the project half-modified (and can always be rolled back).
"""
import copy
import logging

from sqlalchemy import select

from agents.studio import architect, editing
from api.common import ApiError
from db import session_scope
from models import ChatMessage, Entity, Page, Project
from services import checks, jobs, memory, repair, versions
from services.ai_client import AIError, AINotConfigured, AIQuotaExceeded, AIRateLimited
from services.schema import sanitize_tokens

log = logging.getLogger("aidevs.orchestrator")


def ensure_idle(session, project_id):
    """Reject direct (non-job) mutations such as restore while an AI job holds the project lock."""
    if session.scalar(select(Project.active_run_id).where(Project.id == project_id)):
        raise ApiError("An AI task is running for this project. Wait for it to finish or cancel it.", 409)


def entity_dicts(entities):
    return [{"name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
             "sample_data": e.sample_data or []} for e in entities]


def create_project_from_spec(session, user, spec, prompt="", reference_url=""):
    project = Project(owner_id=user.id, name=spec["name"], description=spec.get("summary", ""),
                      prompt=prompt, reference_url=reference_url or "", spec=spec,
                      tokens=sanitize_tokens(spec.get("tokens")), status="draft")
    session.add(project)
    session.flush()
    for i, ent in enumerate(spec.get("entities", [])):
        session.add(Entity(project_id=project.id, name=ent["name"], label=ent["label"], fields=ent["fields"],
                           permissions=ent["permissions"], sample_data=ent.get("sample_data", []), position=i))
    for i, page in enumerate(spec.get("pages", [])):
        session.add(Page(project_id=project.id, name=page["name"], route=page["route"], position=i,
                         tree={"id": f"p_{i}_{project.id[:6]}", "type": "page", "name": page["name"], "tag": "div",
                               "props": {}, "styles": {"base": {}, "tablet": {}, "mobile": {}}, "children": []},
                         seo={"title": f"{page['name']} | {spec['name']}"[:70], "description": page.get("purpose", "")}))
    memory.remember(session, project.id, "instruction", f"Original request: {prompt[:1500]}")
    for feature in spec.get("features", [])[:8]:
        memory.remember(session, project.id, "decision", f"Feature: {feature}")
    if spec.get("brand", {}).get("voice"):
        memory.remember(session, project.id, "preference", f"Brand voice: {spec['brand']['voice']}")
    return project


# ------------------------------------------------------------------ generation
@jobs.register("generate")
def run_generation(ctx, project_id, user_id, reference_summary=""):
    with session_scope() as s:
        project = s.get(Project, project_id)
        project.status = "generating"
        spec = copy.deepcopy(project.spec)
        ents = entity_dicts(project.entities)
        pages = [{"id": p.id, "name": p.name, "route": p.route} for p in project.pages]
        context = memory.build_context(s, project, project.prompt, include_outline=False)

    ctx.step("Architect: building shared navigation and footer", 5)
    layout = architect.build_layout(spec, pages)
    with session_scope() as s:
        s.get(Project, project_id).layout = layout

    spec_pages = {p["route"]: p for p in spec.get("pages", [])}
    fallbacks = 0
    for i, page in enumerate(pages):
        progress = 10 + int(75 * i / max(1, len(pages)))
        ctx.step(f"Frontend agent: designing page '{page['name']}' ({page['route']})", progress)
        page_spec = spec_pages.get(page["route"], {"name": page["name"], "route": page["route"], "sections": []})
        try:
            result = architect.generate_page(spec, page_spec, ents, context=context,
                                             reference_summary=reference_summary,
                                             user_id=user_id, project_id=project_id)
        except AIError as exc:
            if isinstance(exc, (AIRateLimited, AIQuotaExceeded, AINotConfigured)):
                # Capacity/configuration problem, not bad output: stop (the user's quota is refunded)
                # instead of silently filling the project with template pages.
                raise
            fallbacks += 1
            ctx.step(f"AI output for '{page['name']}' failed validation ({exc.user_message}); "
                     "used the section library instead.", progress, level="warning")
            result = architect.fallback_page(spec, page_spec, ents)
        with session_scope() as s:
            row = s.get(Page, page["id"])
            result["tree"]["name"] = page["name"]
            row.tree = result["tree"]
            if result["seo"].get("description"):
                row.seo = result["seo"]
            row.revision += 1

    ctx.step("Testing agent: running contract, accessibility, SEO and build checks", 88)
    with session_scope() as s:
        project = s.get(Project, project_id)
        repair_result = repair.repair_project(s, project, user_id, step=lambda m: ctx.step(m, 92), snapshot=False)
        if repair_result["fixes"]:
            ctx.step(f"Repaired {len(repair_result['fixes'])} issue(s) automatically", 95)
    with session_scope() as s:
        project = s.get(Project, project_id)
        report = checks.run_checks(project, project.pages, project.entities)
        for issue in [i for i in report["issues"] if i["severity"] == "error"][:10]:
            memory.remember(s, project_id, "error", f"{issue['category']}: {issue['message']}")
        project.status = "ready"
        project.revision += 1
        versions.snapshot(s, project, "Initial generation", "auto-generate", user_id)
        s.add(ChatMessage(project_id=project_id, role="assistant", content=(
            f"Your project is ready: {len(pages)} page(s), {len(ents)} data model(s) with a generated REST API. "
            f"Checks: {report['summary']['error']} error(s), {report['summary']['warning']} warning(s)."
            + (f" {fallbacks} page(s) used the section library because the AI output was invalid." if fallbacks else "")
            + " Click any element to edit it, or ask me for changes.")))
    ctx.step("Done", 100)
    return {"checks": report["summary"], "fallbackPages": fallbacks,
            "repair": {k: repair_result[k] for k in ("errorsBefore", "errorsAfter", "fixes", "aiAttempts", "rolledBack")}}


def _generation_failed(_run_id, args, message):
    with session_scope() as s:
        project = s.get(Project, args[0])
        if project:
            project.status = "failed"
            memory.remember(s, project.id, "error", f"Generation failed: {message}")


run_generation.on_failure = _generation_failed


# --------------------------------------------------------------- feature work
def apply_feature_plan(session, project, plan, user_id):
    """Apply a validated plan atomically (caller commits)."""
    versions.snapshot(session, project, "Before AI change", "auto-ai", user_id)
    changed = []
    existing = {e.name: e for e in project.entities}
    for op in plan["entities"]:
        ent = op["entity"]
        if ent["name"] in existing:
            row = existing[ent["name"]]
            row.label, row.fields, row.permissions = ent["label"], ent["fields"], ent["permissions"]
            if ent["sample_data"]:
                row.sample_data = ent["sample_data"]
            changed.append(f"updated data model {ent['label']}")
        else:
            session.add(Entity(project_id=project.id, name=ent["name"], label=ent["label"], fields=ent["fields"],
                               permissions=ent["permissions"], sample_data=ent["sample_data"],
                               position=len(existing)))
            existing[ent["name"]] = True
            changed.append(f"added data model {ent['label']} (+ REST API)")
    pages = {p.route: p for p in project.pages}
    for op in plan["pages"]:
        if op["op"] == "add":
            session.add(Page(project_id=project.id, name=op["name"], route=op["route"], position=len(pages),
                             tree={**op["tree"], "name": op["name"]},
                             seo=op["seo"] if op["seo"].get("title") else {"title": op["name"]}))
            pages[op["route"]] = True
            changed.append(f"added page {op['route']}")
        else:
            page = pages[op["route"]]
            tree = copy.deepcopy(page.tree)
            new_sections = op["tree"]["children"]
            tree["children"] = new_sections + tree["children"] if op["position"] == "start" \
                else tree["children"] + new_sections
            page.tree = tree
            page.revision += 1
            changed.append(f"added {len(new_sections)} section(s) to {op['route']}")
    if plan["nav"] and project.layout and project.layout.get("header"):
        layout = copy.deepcopy(project.layout)
        links = _find_nav(layout["header"])
        if links is not None:
            have = {c["props"].get("href") for c in links["children"]}
            template = links["children"][0] if links["children"] else None
            for item in plan["nav"]:
                if item["href"] in have or template is None:
                    continue
                from services.schema import new_node_id
                link = copy.deepcopy(template)
                link.update(id=new_node_id(), name=f"Nav: {item['label']}")
                link["props"] = {**link["props"], "text": item["label"], "href": item["href"]}
                links["children"].append(link)
                changed.append(f"added nav link {item['label']}")
            project.layout = layout
    if plan["tokens"]:
        merged = copy.deepcopy(project.tokens or {})
        for key, value in plan["tokens"].items():
            if isinstance(value, dict):
                merged.setdefault(key, {}).update(value)
            else:
                merged[key] = value
        project.tokens = sanitize_tokens(merged)
        changed.append("updated design tokens")
    for note in plan["remember"]:
        memory.remember(session, project.id, "decision", note)
    project.revision += 1
    return changed


def _find_nav(header):
    from services.schema import walk
    for node, _ in walk(header):
        if node["type"] == "container" and node.get("children") and \
                all(c["type"] == "link" for c in node["children"]):
            return node
    return None


@jobs.register("feature")
def run_feature(ctx, project_id, user_id, message):
    with session_scope() as s:
        project = s.get(Project, project_id)
        context = memory.build_context(s, project, message)
        ents = entity_dicts(project.entities)
        routes = [p.route for p in project.pages]
    ctx.step("Orchestrator: analysing the request against project memory", 10)
    plan = editing.plan_feature(message, context, ents, routes, user_id=user_id, project_id=project_id)
    nothing = not (plan["entities"] or plan["pages"] or plan["nav"] or plan["tokens"])
    ctx.step("Backend/Database/Frontend agents: applying validated changes" if not nothing
             else "No project changes were needed", 70)
    with session_scope() as s:
        project = s.get(Project, project_id)
        changed = [] if nothing else apply_feature_plan(s, project, plan, user_id)
    if not nothing:
        ctx.step("Testing agent: validating the change", 80)
        with session_scope() as s:
            project = s.get(Project, project_id)
            fix = repair.repair_project(s, project, user_id, step=lambda m: ctx.step(m, 88), snapshot=False)
            changed += [f"auto-repaired: {f}" for f in fix["fixes"]]
            report = checks.run_checks(project, project.pages, project.entities)
    with session_scope() as s:
        reply = plan["reply"] + (("\n\nChanges: " + "; ".join(changed) + ".") if changed else "")
        s.add(ChatMessage(project_id=project_id, role="assistant", content=reply,
                          meta={"changes": changed}))
        memory.remember(s, project_id, "instruction", message[:500])
    ctx.step("Done", 100)
    return {"reply": reply, "changes": changed,
            "checks": report["summary"] if not nothing else None}


def _feature_failed(_run_id, args, message):
    with session_scope() as s:
        s.add(ChatMessage(project_id=args[0], role="assistant",
                          content=f"I couldn't complete that change: {message} Your project was not modified."))


run_feature.on_failure = _feature_failed


@jobs.register("repair")
def run_repair(ctx, project_id, user_id):
    ctx.step("Testing agent: running checks", 10)
    with session_scope() as s:
        project = s.get(Project, project_id)
        result = repair.repair_project(s, project, user_id, step=lambda m: ctx.step(m, 50))
        s.add(ChatMessage(project_id=project_id, role="assistant", content=(
            f"Automatic repair: {result['errorsBefore']} error(s) before, {result['errorsAfter']} after. "
            + ("Fixed: " + "; ".join(result["fixes"][:8]) if result["fixes"] else "No automatic fix was possible.")
            + (" A version was saved before repairing." if result["errorsBefore"] else ""))))
    ctx.step("Done", 100)
    return {k: result[k] for k in ("errorsBefore", "errorsAfter", "fixes", "aiAttempts", "rolledBack")}
