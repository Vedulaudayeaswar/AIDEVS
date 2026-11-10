"""Projects / pages / entities / versions / AI assistant API (all owner-scoped)."""
import re

from flask import Blueprint, current_app, jsonify, request, Response
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func, select, update

from agents.studio import editing, orchestrator
from agents.studio.requirements import plan_application, summarize_reference, validate_spec
from api.common import ApiError, audit, get_owned_project, json_body, rate_limit
from db import get_session
from models import utcnow, AgentRun, Asset, ChatMessage, Entity, Page, PreviewRecord, Project, ProjectVersion
from services import checks, jobs, limits, memory, templates, versions
from services.compiler import compose_page, preview_document, split_page
from services.crawler import CrawlError, crawl
from services.exporter import build_export, referenced_asset_ids
from services.schema import (SchemaError, all_ids, sanitize_entity, sanitize_subtree,
                             sanitize_tokens, sanitize_tree, validate_record)

bp = Blueprint("projects", __name__, url_prefix="/api")
ROUTE_RE = re.compile(r"^/[a-z0-9\-/]{0,60}$")
MAX_PREVIEW_RECORDS = 500


# ------------------------------------------------------------------ helpers
def page_dict(page, project, with_tree=True):
    data = {"id": page.id, "name": page.name, "route": page.route, "position": page.position,
            "revision": page.revision, "seo": page.seo or {},
            "updatedAt": page.updated_at.isoformat() if page.updated_at else None}
    if with_tree:
        data["tree"] = compose_page(project.layout, page.tree)
    return data


def entity_dict(e):
    return {"id": e.id, "name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
            "sampleData": e.sample_data or []}


def run_dict(run):
    return {"id": run.id, "kind": run.kind, "status": run.status, "progress": run.progress,
            "attempts": run.attempts, "maxAttempts": run.max_attempts, "cancelRequested": run.cancel_requested,
            "message": run.message, "steps": run.steps or [], "result": run.result or {}, "error": run.error,
            "createdAt": run.created_at.isoformat() if run.created_at else None,
            "finishedAt": run.finished_at.isoformat() if run.finished_at else None}


def project_summary(p, session, page_count=None):
    pages = page_count if page_count is not None else         session.scalar(select(func.count(Page.id)).where(Page.project_id == p.id))
    return {"id": p.id, "name": p.name, "description": p.description, "status": p.status,
            "pageCount": pages, "primary": (p.tokens or {}).get("colors", {}).get("primary"),
            "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat() if p.updated_at else None}


def project_dict(p, session, with_trees=False):
    latest = session.scalars(select(AgentRun).where(AgentRun.project_id == p.id)
                             .order_by(AgentRun.created_at.desc()).limit(1)).first()
    return {
        **project_summary(p, session), "prompt": p.prompt, "referenceUrl": p.reference_url,
        "spec": p.spec, "specVersion": p.spec_version, "tokens": p.tokens, "revision": p.revision,
        "pages": [page_dict(pg, p, with_trees) for pg in p.pages],
        "entities": [entity_dict(e) for e in p.entities],
        "latestRun": run_dict(latest) if latest else None,
    }


def api_base():
    configured = current_app.config.get("PUBLIC_API_URL")
    return (configured or request.host_url).rstrip("/")


def preview_records(session, project):
    records = {}
    for e in project.entities:
        rows = list(e.sample_data or [])
        stored = session.scalars(select(PreviewRecord).where(
            PreviewRecord.project_id == project.id, PreviewRecord.entity == e.name)
            .order_by(PreviewRecord.created_at.desc()).limit(50)).all()
        records[e.name] = [{"id": r.id, **r.data} for r in stored] + rows
    return records


def get_page(project, page_id):
    page = next((p for p in project.pages if p.id == page_id), None)
    if page is None:
        raise ApiError("Page not found", 404)
    return page


def _ensure_ai_capacity():
    """Pause new AI work (clear 503 + Retry-After) when the shared free AI budget is exhausted."""
    from services import ai_capacity
    status = ai_capacity.capacity_status()
    if not status["available"]:
        raise limits.LimitExceeded(
            "Shared free AI capacity is temporarily used up, so new AI tasks are paused. Please try again in "
            f"about {max(1, status['retryAfterSeconds'] // 60)} minute(s). Your projects are safe.", status=503)


def _submit_or_refund(s, quota_id, *args, **kwargs):
    try:
        return jobs.submit(s, *args, quota_id=quota_id, **kwargs)
    except Exception:
        s.rollback()
        limits.refund(quota_id)
        raise


# ------------------------------------------------------------------ projects
@bp.get("/projects")
@jwt_required()
def list_projects():
    s = get_session()
    try:
        limit = max(1, min(100, int(request.args.get("limit", 24))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        raise ApiError("limit and offset must be integers", 400) from None
    base = select(Project).where(Project.owner_id == current_user.id)
    total = s.scalar(select(func.count()).select_from(base.subquery()))
    rows = s.scalars(base.order_by(Project.updated_at.desc()).limit(limit).offset(offset)).all()
    # One grouped query for page counts instead of one query per project (avoids N+1).
    counts = dict(s.execute(select(Page.project_id, func.count(Page.id))
                            .where(Page.project_id.in_([p.id for p in rows])).group_by(Page.project_id)).all())         if rows else {}
    return jsonify(projects=[project_summary(p, s, counts.get(p.id, 0)) for p in rows], total=total, limit=limit,
                   offset=offset)


@bp.post("/projects/analyze-url")
@jwt_required()
@rate_limit("analyze-url", limit=5, window=60, per_user=True)
def analyze_url():
    url = str(json_body().get("url", "")).strip()
    try:
        result = crawl(url)
    except CrawlError as exc:
        raise ApiError(str(exc), 400) from exc
    return jsonify(reference=result)


@bp.post("/projects/plan")
@jwt_required()
@rate_limit("plan", limit=8, window=60, per_user=True)
def plan_project():
    data = json_body()
    prompt = str(data.get("prompt", "")).strip()
    if len(prompt) < 8:
        raise ApiError("Describe your idea in at least a sentence.", 400)
    reference = data.get("reference") if isinstance(data.get("reference"), dict) else None
    if not reference and data.get("referenceUrl"):
        try:
            reference = crawl(str(data["referenceUrl"]))
        except CrawlError as exc:
            raise ApiError(f"Reference website: {exc}", 400) from exc
    spec = plan_application(prompt, reference=reference, choices=data.get("choices"), user_id=current_user.id)
    return jsonify(spec=spec, reference=reference)


@bp.post("/projects")
@jwt_required()
def create_project():
    data = json_body()
    s = get_session()
    limits.check_project_quota(s, current_user.id)
    if data.get("blank"):
        name = str(data.get("name") or "Untitled project").strip()[:80] or "Untitled project"
        spec = validate_spec({"name": name, "pages": [{"name": "Home", "route": "/", "sections": [
            {"kind": "hero"}, {"kind": "features"}, {"kind": "contact_form"}]}]})
        project = orchestrator.create_project_from_spec(s, current_user, spec, prompt="Blank project")
        s.flush()
        from agents.studio import architect
        layout = architect.build_layout(spec, spec["pages"])
        project.layout = layout
        page = s.scalars(select(Page).where(Page.project_id == project.id)).first()
        page.tree = architect.fallback_page(spec, spec["pages"][0], spec["entities"])["tree"]
        project.status = "ready"
        versions.snapshot(s, project, "Project created", "auto-generate", current_user.id)
        audit(s, current_user.id, "project.create", project.id)
        s.commit()
        return jsonify(project=project_dict(project, s)), 201
    try:
        spec = validate_spec(data.get("spec"))
    except SchemaError as exc:
        raise ApiError(f"Invalid specification: {exc}", 400) from exc
    reference = data.get("reference") if isinstance(data.get("reference"), dict) else None
    _ensure_ai_capacity()
    quota_id = limits.consume(s, current_user.id, "generate")
    project = orchestrator.create_project_from_spec(
        s, current_user, spec, prompt=str(data.get("prompt", ""))[:4000],
        reference_url=str(data.get("referenceUrl", ""))[:2048])
    audit(s, current_user.id, "project.create", project.id)
    s.commit()
    try:
        run = jobs.submit(s, project.id, current_user.id, "generate", "generate",
                          project.id, current_user.id, summarize_reference(reference) if reference else "",
                          quota_id=quota_id)
    except Exception:
        s.rollback()
        limits.refund(quota_id)
        s.delete(s.get(Project, project.id))  # never leave an empty, ungenerated project behind
        s.commit()
        raise
    s.refresh(project)
    return jsonify(project=project_dict(project, s), run=run_dict(run)), 201


@bp.get("/projects/<project_id>")
@jwt_required()
def get_project(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    return jsonify(project=project_dict(project, s, with_trees=request.args.get("trees") == "1"))


@bp.patch("/projects/<project_id>")
@jwt_required()
def update_project(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    data = json_body()
    if "name" in data:
        name = str(data["name"]).strip()[:80]
        if not name:
            raise ApiError("Name cannot be empty", 400)
        project.name = name
    if "description" in data:
        project.description = str(data["description"])[:600]
    if "tokens" in data:
        project.tokens = sanitize_tokens(data["tokens"])
        memory.remember(s, project.id, "decision", "Design tokens updated manually")
    project.revision += 1
    s.commit()
    return jsonify(project=project_dict(project, s))


@bp.delete("/projects/<project_id>")
@jwt_required()
def delete_project(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    audit(s, current_user.id, "project.delete", project.id, name=project.name)
    s.delete(project)
    s.commit()
    return jsonify(success=True)


@bp.post("/projects/<project_id>/generate")
@jwt_required()
def regenerate(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    orchestrator.ensure_idle(s, project.id)
    _ensure_ai_capacity()
    quota_id = limits.consume(s, current_user.id, "generate")
    versions.snapshot(s, project, "Before regeneration", "auto-ai", current_user.id)
    s.commit()
    run = _submit_or_refund(s, quota_id, project.id, current_user.id, "generate", "generate",
                            project.id, current_user.id, "")
    return jsonify(run=run_dict(run)), 202


# --------------------------------------------------------------------- pages
@bp.get("/projects/<project_id>/pages/<page_id>")
@jwt_required()
def read_page(project_id, page_id):
    project = get_owned_project(project_id)
    return jsonify(page=page_dict(get_page(project, page_id), project))


@bp.put("/projects/<project_id>/pages/<page_id>")
@jwt_required()
def save_page(project_id, page_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    page = get_page(project, page_id)
    data = json_body()
    try:
        base = int(data["baseRevision"]) if data.get("baseRevision") is not None else page.revision
    except (TypeError, ValueError):
        raise ApiError("baseRevision must be an integer", 400) from None
    try:
        tree, warnings = sanitize_tree(data.get("tree"))
    except SchemaError as exc:
        raise ApiError(f"Invalid page: {exc}", 400) from exc
    own, header, footer = split_page(tree)
    values = {"tree": own, "revision": Page.revision + 1, "updated_at": utcnow()}
    if isinstance(data.get("seo"), dict):
        values["seo"] = {"title": str(data["seo"].get("title", ""))[:70],
                         "description": str(data["seo"].get("description", ""))[:170]}
    # Atomic optimistic concurrency: succeeds only if nobody saved since `base`.
    updated = s.execute(update(Page).where(Page.id == page.id, Page.revision == base).values(**values)).rowcount
    if updated != 1:
        s.rollback()
        current = s.scalar(select(Page.revision).where(Page.id == page.id))
        raise ApiError("This page was changed elsewhere. Reload to get the latest version.", 409, revision=current)
    layout = dict(project.layout or {})
    changed = False
    for key, node in (("header", header), ("footer", footer)):
        if node is not None and layout.get(key) != node:
            layout[key], changed = node, True
    project_values = {"revision": Project.revision + 1, "updated_at": utcnow()}
    if changed:
        project_values["layout"] = layout
    s.execute(update(Project).where(Project.id == project.id).values(**project_values))
    if data.get("checkpoint"):
        s.expire(project)
        versions.snapshot(s, project, str(data.get("checkpoint"))[:120], "manual", current_user.id)
    s.commit()
    return jsonify(revision=base + 1, warnings=warnings[:20])


@bp.post("/projects/<project_id>/pages")
@jwt_required()
def add_page(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    limits.check_page_quota(s, project.id)
    data = json_body()
    name = str(data.get("name", "")).strip()[:60]
    route = str(data.get("route", "")).strip().lower().rstrip("/") or "/"
    if not name or not ROUTE_RE.match(route):
        raise ApiError("A page needs a name and a route like /about", 400)
    if any(p.route == route for p in project.pages):
        raise ApiError("A page with that route already exists", 409)
    ctx = {"name": project.name, "about_title": name, "about_text": "Describe this page here."}
    tree, _ = sanitize_tree({"type": "page", "name": name, "children": [templates.build_section("about", ctx)]})
    page = Page(project_id=project.id, name=name, route=route, position=len(project.pages), tree=tree,
                seo={"title": f"{name} | {project.name}"[:70], "description": ""})
    s.add(page)
    project.revision += 1
    s.commit()
    return jsonify(page=page_dict(page, project)), 201


@bp.patch("/projects/<project_id>/pages/<page_id>")
@jwt_required()
def update_page_meta(project_id, page_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    page = get_page(project, page_id)
    data = json_body()
    if "name" in data:
        page.name = str(data["name"]).strip()[:60] or page.name
    if "route" in data:
        route = str(data["route"]).strip().lower().rstrip("/") or "/"
        if not ROUTE_RE.match(route) or any(p.route == route and p.id != page.id for p in project.pages):
            raise ApiError("Invalid or duplicate route", 400)
        page.route = route
    if isinstance(data.get("seo"), dict):
        page.seo = {"title": str(data["seo"].get("title", ""))[:70],
                    "description": str(data["seo"].get("description", ""))[:170]}
    s.commit()
    return jsonify(page=page_dict(page, project, with_tree=False))


@bp.delete("/projects/<project_id>/pages/<page_id>")
@jwt_required()
def delete_page(project_id, page_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    page = get_page(project, page_id)
    if len(project.pages) <= 1:
        raise ApiError("A project needs at least one page", 400)
    versions.snapshot(s, project, f"Before deleting page {page.route}", "auto-edit", current_user.id)
    s.delete(page)
    project.revision += 1
    s.commit()
    return jsonify(success=True)


@bp.post("/projects/<project_id>/preview")
@jwt_required()
def preview(project_id):
    """Compile a (possibly unsaved) page tree into a sandbox-ready document."""
    s = get_session()
    project = get_owned_project(project_id, s)
    data = json_body()
    page = get_page(project, str(data.get("pageId", "")))
    tree = compose_page(project.layout, page.tree)
    if data.get("tree") is not None:
        try:
            tree, _ = sanitize_tree(data["tree"])
        except SchemaError as exc:
            raise ApiError(f"Invalid page: {exc}", 400) from exc
    mode = "interact" if data.get("mode") == "interact" else "edit"
    html = preview_document(tree, project.tokens or {}, title=page.name, records=preview_records(s, project),
                            editor=True, api_base=api_base(), mode=mode)
    return jsonify(html=html)


# ------------------------------------------------------------ section palette
@bp.get("/studio/palette")
@jwt_required()
def palette():
    return jsonify(templates.palette())


@bp.post("/projects/<project_id>/build-node")
@jwt_required()
def build_node(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    data = json_body()
    key, kind = str(data.get("key", "")), data.get("kind", "section")
    entity = next((e for e in project.entities if e.name == data.get("entity")), None) or \
        (project.entities[0] if project.entities else None)
    ctx = {"name": project.name, "nav": [{"label": p.name, "href": p.route} for p in project.pages],
           "entity": entity_dict(entity) | {"sample_data": entity.sample_data} if entity else None,
           "contact_entity": "contact_message"}
    try:
        node = templates.build_section(key, ctx) if kind == "section" else templates.build_element(key)
    except KeyError:
        raise ApiError("Unknown component", 400) from None
    if key == "contact_form" and not any(e.name == "contact_message" for e in project.entities):
        ent = sanitize_entity({"name": "contact_message", "label": "Contact messages",
                               "fields": [{"name": "name", "type": "string", "required": True},
                                          {"name": "email", "type": "email", "required": True},
                                          {"name": "message", "type": "text", "required": True}],
                               "permissions": {"read": "admin", "create": "public"}})
        s.add(Entity(project_id=project.id, name=ent["name"], label=ent["label"], fields=ent["fields"],
                     permissions=ent["permissions"], position=len(project.entities)))
        s.commit()
    clean, _ = sanitize_subtree(node)
    return jsonify(node=clean)


# ------------------------------------------------------------------ entities
@bp.post("/projects/<project_id>/entities")
@jwt_required()
def add_entity(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    try:
        ent = sanitize_entity(json_body())
    except SchemaError as exc:
        raise ApiError(str(exc), 400) from exc
    if any(e.name == ent["name"] for e in project.entities):
        raise ApiError("A data model with that name already exists", 409)
    row = Entity(project_id=project.id, name=ent["name"], label=ent["label"], fields=ent["fields"],
                 permissions=ent["permissions"], sample_data=ent["sample_data"], position=len(project.entities))
    s.add(row)
    project.revision += 1
    memory.remember(s, project.id, "decision", f"Added data model {ent['label']}")
    s.commit()
    return jsonify(entity=entity_dict(row)), 201


@bp.put("/projects/<project_id>/entities/<entity_id>")
@jwt_required()
def update_entity(project_id, entity_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    row = next((e for e in project.entities if e.id == entity_id), None)
    if row is None:
        raise ApiError("Data model not found", 404)
    body = json_body()
    body["name"] = row.name  # renaming would break bound forms/collections
    try:
        ent = sanitize_entity(body)
    except SchemaError as exc:
        raise ApiError(str(exc), 400) from exc
    versions.snapshot(s, project, f"Before editing data model {row.label}", "auto-edit", current_user.id)
    row.label, row.fields, row.permissions, row.sample_data = ent["label"], ent["fields"], ent["permissions"], \
        ent["sample_data"]
    project.revision += 1
    s.commit()
    return jsonify(entity=entity_dict(row))


@bp.delete("/projects/<project_id>/entities/<entity_id>")
@jwt_required()
def delete_entity(project_id, entity_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    row = next((e for e in project.entities if e.id == entity_id), None)
    if row is None:
        raise ApiError("Data model not found", 404)
    versions.snapshot(s, project, f"Before deleting data model {row.label}", "auto-edit", current_user.id)
    s.delete(row)
    project.revision += 1
    s.commit()
    return jsonify(success=True)


# ------------------------------------------- preview data (generated API contract)
@bp.route("/projects/<project_id>/data/<entity>", methods=["GET", "POST"])
@jwt_required()
def preview_data(project_id, entity):
    s = get_session()
    project = get_owned_project(project_id, s)
    if entity in ("auth_login", "auth_register"):
        raise ApiError("Sign-in forms call the generated app's own auth API. They work in the exported app; "
                       "the preview does not create accounts.", 400)
    ent = next((e for e in project.entities if e.name == entity), None)
    if ent is None:
        raise ApiError(f"Unknown data model '{entity}'", 404)
    if request.method == "GET":
        rows = s.scalars(select(PreviewRecord).where(PreviewRecord.project_id == project.id,
                                                     PreviewRecord.entity == entity)
                         .order_by(PreviewRecord.created_at.desc()).limit(100)).all()
        return jsonify(items=[{"id": r.id, **r.data, "created_at": r.created_at.isoformat()} for r in rows])
    count = s.scalar(select(func.count(PreviewRecord.id)).where(PreviewRecord.project_id == project.id))
    if count >= MAX_PREVIEW_RECORDS:
        raise ApiError("Preview data limit reached. Delete some records first.", 400)
    try:
        record = validate_record(ent.fields, json_body())
    except SchemaError as exc:
        raise ApiError(f"Validation failed: {exc}", 400) from exc
    row = PreviewRecord(project_id=project.id, entity=entity, data=record)
    s.add(row)
    s.commit()
    return jsonify(item={"id": row.id, **record}), 201


@bp.delete("/projects/<project_id>/data/<entity>/<record_id>")
@jwt_required()
def delete_preview_record(project_id, entity, record_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    row = s.get(PreviewRecord, record_id)
    if row is None or row.project_id != project.id or row.entity != entity:
        raise ApiError("Record not found", 404)
    s.delete(row)
    s.commit()
    return jsonify(success=True)


# ------------------------------------------------------------------ versions
@bp.get("/projects/<project_id>/versions")
@jwt_required()
def list_versions(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    rows = s.scalars(select(ProjectVersion).where(ProjectVersion.project_id == project.id)
                     .order_by(ProjectVersion.number.desc()).limit(100)).all()
    return jsonify(versions=[{"id": v.id, "number": v.number, "label": v.label, "reason": v.reason,
                              "createdAt": v.created_at.isoformat()} for v in rows])


@bp.post("/projects/<project_id>/versions")
@jwt_required()
def create_version(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    label = str(json_body().get("label") or "Checkpoint").strip()[:120]
    version = versions.snapshot(s, project, label, "manual", current_user.id)
    s.commit()
    return jsonify(version={"id": version.id, "number": version.number, "label": version.label}), 201


def _get_version(s, project, version_id):
    v = s.get(ProjectVersion, version_id)
    if v is None or v.project_id != project.id:
        raise ApiError("Version not found", 404)
    return v


@bp.get("/projects/<project_id>/versions/<version_id>/diff")
@jwt_required()
def version_diff(project_id, version_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    v = _get_version(s, project, version_id)
    return jsonify(diff=versions.diff(v.snapshot, versions.capture(project)))


@bp.post("/projects/<project_id>/versions/<version_id>/restore")
@jwt_required()
def restore_version(project_id, version_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    orchestrator.ensure_idle(s, project.id)
    v = _get_version(s, project, version_id)
    versions.restore(s, project, v, current_user.id)
    memory.remember(s, project.id, "decision", f"Restored version {v.number} ({v.label})")
    audit(s, current_user.id, "project.restore", project.id, version=v.number)
    s.commit()
    s.refresh(project)
    return jsonify(project=project_dict(project, s))


# ---------------------------------------------------------------- runs & chat
@bp.get("/projects/<project_id>/runs")
@jwt_required()
def list_runs(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    rows = s.scalars(select(AgentRun).where(AgentRun.project_id == project.id)
                     .order_by(AgentRun.created_at.desc()).limit(30)).all()
    return jsonify(runs=[run_dict(r) for r in rows])


@bp.get("/runs/<run_id>")
@jwt_required()
def get_run(run_id):
    s = get_session()
    run = s.get(AgentRun, run_id)
    if run is None:
        raise ApiError("Run not found", 404)
    get_owned_project(run.project_id, s)
    return jsonify(run=run_dict(run))


@bp.post("/runs/<run_id>/cancel")
@jwt_required()
def cancel_run(run_id):
    s = get_session()
    run = s.get(AgentRun, run_id)
    if run is None:
        raise ApiError("Run not found", 404)
    get_owned_project(run.project_id, s)  # ownership check
    state = jobs.cancel(s, run)
    audit(s, current_user.id, "run.cancel", run.id)
    s.commit()
    return jsonify(status=state)


@bp.get("/projects/<project_id>/messages")
@jwt_required()
def list_messages(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    rows = s.scalars(select(ChatMessage).where(ChatMessage.project_id == project.id)
                     .order_by(ChatMessage.created_at.desc()).limit(100)).all()
    return jsonify(messages=[{"id": m.id, "role": m.role, "content": m.content, "meta": m.meta or {},
                              "createdAt": m.created_at.isoformat()} for m in reversed(rows)])


@bp.post("/projects/<project_id>/assistant")
@jwt_required()
@rate_limit("assistant", limit=12, window=60, per_user=True)
def assistant(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    data = json_body()
    message = str(data.get("message", "")).strip()
    if not message:
        raise ApiError("Message is required", 400)
    if len(message) > 4000:
        raise ApiError("Message is too long (max 4000 characters)", 400)
    selection = data.get("selection") if isinstance(data.get("selection"), dict) else None
    _ensure_ai_capacity()
    quota_id = limits.consume(s, current_user.id, "modify")
    s.add(ChatMessage(project_id=project.id, role="user", content=message,
                      meta={"selection": selection.get("nodeId")} if selection else {}))
    s.commit()

    if selection and isinstance(selection.get("node"), dict):
        # Visual Editing agent: returns a modified subtree; the studio applies it
        # as one undoable edit and autosaves (so nothing is written here).
        try:
            node, _ = sanitize_subtree(selection["node"])
        except SchemaError as exc:
            raise ApiError(f"Invalid selection: {exc}", 400) from exc
        node["id"] = str(selection["node"].get("id"))[:40]
        page_ids = set()
        if selection.get("pageId"):
            page = get_page(project, str(selection["pageId"]))
            page_ids = all_ids(compose_page(project.layout, page.tree))
        context = memory.build_context(s, project, message, include_outline=False, limit_chars=2500)
        try:
            result = editing.edit_node(node, message, project.tokens or {}, orchestrator.entity_dicts(project.entities),
                                       context, page_ids=page_ids, user_id=current_user.id, project_id=project.id)
        except Exception:
            limits.refund(quota_id)  # failed AI work does not count against the user's quota
            raise
        reply = result["summary"] or "Updated the selected element."
        s.add(ChatMessage(project_id=project.id, role="assistant", content=reply, meta={"edit": node["id"]}))
        memory.remember(s, project.id, "instruction", f"Edit '{node.get('name')}': {message[:300]}")
        s.commit()
        return jsonify(mode="edit", node=result["node"], reply=reply)

    run = _submit_or_refund(s, quota_id, project.id, current_user.id, "feature", "feature",
                            project.id, current_user.id, message)
    return jsonify(mode="feature", run=run_dict(run)), 202


# -------------------------------------------------------------- checks/export
@bp.post("/projects/<project_id>/checks")
@jwt_required()
def run_project_checks(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    report = checks.run_checks(project, project.pages, project.entities)
    s.add(AgentRun(project_id=project.id, user_id=current_user.id, kind="checks",
                   status="succeeded", progress=100, message=f"{report['summary']}", result=report))
    s.commit()
    return jsonify(report=report)


def _export(project, s):
    ids = referenced_asset_ids(project, project.pages)
    assets = {a.id: a for a in s.scalars(select(Asset).where(Asset.project_id == project.id,
                                                             Asset.id.in_(ids)))} if ids else {}
    return build_export(project, project.pages, project.entities, assets)


@bp.post("/projects/<project_id>/repair")
@jwt_required()
@rate_limit("repair", limit=6, window=300, per_user=True)
def repair_project(project_id):
    """Queue the bounded validate-and-repair loop for this project."""
    s = get_session()
    project = get_owned_project(project_id, s)
    _ensure_ai_capacity()
    quota_id = limits.consume(s, current_user.id, "modify")
    s.commit()
    run = _submit_or_refund(s, quota_id, project.id, current_user.id, "feature", "repair",
                            project.id, current_user.id)
    return jsonify(run=run_dict(run)), 202


@bp.get("/projects/<project_id>/export")
@jwt_required()
def export_project(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    limits.consume(s, current_user.id, "export")
    s.commit()
    data, _paths, _files = _export(project, s)
    audit(s, current_user.id, "project.export", project.id)
    s.commit()
    slug = re.sub(r"[^a-z0-9-]+", "-", project.name.lower()).strip("-") or "aidevs-app"
    return Response(data, mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'})


@bp.get("/projects/<project_id>/export/files")
@jwt_required()
def export_files(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    _data, paths, files = _export(project, s)
    return jsonify(files={p: files[p] for p in paths if len(files[p]) < 200_000})


@bp.get("/usage")
@jwt_required()
def usage():
    from datetime import datetime, timedelta, timezone

    from models import UsageRecord
    s = get_session()
    since = datetime.now(timezone.utc) - timedelta(days=1)
    count, tokens = s.execute(select(
        func.count(UsageRecord.id),
        func.coalesce(func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens), 0))
        .where(UsageRecord.user_id == current_user.id, UsageRecord.created_at >= since)).one()
    active_jobs = s.scalar(select(func.count(AgentRun.id)).where(AgentRun.user_id == current_user.id,
                                                                 AgentRun.status.in_(["queued", "running"])))
    projects = s.scalar(select(func.count(Project.id)).where(Project.owner_id == current_user.id))
    lim = limits.all_limits()
    return jsonify(requests=count, tokens=int(tokens), requestLimit=lim["ai_daily_requests"],
                   tokenLimit=lim["ai_daily_tokens"], activeJobs=active_jobs,
                   jobLimit=lim["max_concurrent_jobs_per_user"], projects=projects,
                   projectLimit=lim["max_projects_per_user"],
                   storageBytes=limits.storage_used(s, current_user.id),
                   storageLimitBytes=lim["max_storage_mb_per_user"] * 1024 * 1024,
                   today=limits.usage_today(s, current_user.id),
                   dailyLimits={"generate": lim["ai_generations_per_day"], "modify": lim["ai_modifications_per_day"],
                                "export": lim["exports_per_day"]},
                   aiCapacity=_capacity_public())


def _capacity_public():
    from services import ai_capacity
    status = ai_capacity.capacity_status()
    return {"available": status["available"], "retryAfterSeconds": status["retryAfterSeconds"]}


@bp.get("/public-status")
def public_status():
    """Unauthenticated, cacheable status used by the frontend during cold starts."""
    return jsonify(api="up", ai=_capacity_public())
