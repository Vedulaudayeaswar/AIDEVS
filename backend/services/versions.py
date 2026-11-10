"""Project snapshots, restore and change comparison."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from models import Entity, Page, ProjectVersion
from services.schema import count_nodes

MAX_AUTO_VERSIONS = 60


def capture(project):
    return {
        "name": project.name, "description": project.description, "spec": project.spec or {},
        "spec_version": project.spec_version, "tokens": project.tokens or {}, "layout": project.layout or {},
        "pages": [{"id": p.id, "name": p.name, "route": p.route, "position": p.position,
                   "tree": p.tree, "seo": p.seo or {}} for p in project.pages],
        "entities": [{"name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
                      "sample_data": e.sample_data or [], "position": e.position} for e in project.entities],
    }


def snapshot(session, project, label, reason="manual", user_id=None):
    """Store a full snapshot. Concurrent snapshots of the same project race for the
    next number; the unique (project_id, number) constraint makes the loser retry."""
    session.flush()
    data = capture(project)
    for _attempt in range(5):
        number = (session.scalar(select(func.max(ProjectVersion.number))
                                 .where(ProjectVersion.project_id == project.id)) or 0) + 1
        version = ProjectVersion(project_id=project.id, number=number, label=label[:200], reason=reason,
                                 snapshot=data, created_by=user_id)
        try:
            with session.begin_nested():
                session.add(version)
                session.flush()
            break
        except IntegrityError:
            continue
    else:
        raise RuntimeError("Could not allocate a version number; please retry.")
    if reason != "manual":
        autos = session.scalars(select(ProjectVersion).where(
            ProjectVersion.project_id == project.id, ProjectVersion.reason != "manual")
            .order_by(ProjectVersion.number.desc()).offset(MAX_AUTO_VERSIONS)).all()
        for old in autos:
            session.delete(old)
    return version


def apply_snapshot(session, project, snap):
    project.spec = snap.get("spec") or {}
    project.tokens = snap.get("tokens") or {}
    project.layout = snap.get("layout") or {}
    project.revision += 1
    for page in list(project.pages):
        session.delete(page)
    for entity in list(project.entities):
        session.delete(entity)
    session.flush()
    for p in snap.get("pages", []):
        session.add(Page(project_id=project.id, name=p["name"], route=p["route"], position=p.get("position", 0),
                         tree=p["tree"], seo=p.get("seo") or {}))
    for e in snap.get("entities", []):
        session.add(Entity(project_id=project.id, name=e["name"], label=e["label"], fields=e["fields"],
                           permissions=e["permissions"], sample_data=e.get("sample_data") or [],
                           position=e.get("position", 0)))
    session.flush()
    session.expire(project, ["pages", "entities"])


def restore(session, project, version, user_id=None):
    snapshot(session, project, f"Before restoring v{version.number}", "auto-restore", user_id)
    apply_snapshot(session, project, version.snapshot)


def diff(old, new):
    old_pages = {p["route"]: p for p in old.get("pages", [])}
    new_pages = {p["route"]: p for p in new.get("pages", [])}
    old_ent = {e["name"]: e for e in old.get("entities", [])}
    new_ent = {e["name"]: e for e in new.get("entities", [])}
    changed = []
    for route in sorted(set(old_pages) & set(new_pages)):
        if old_pages[route]["tree"] != new_pages[route]["tree"]:
            changed.append({"route": route, "nodesBefore": count_nodes(old_pages[route]["tree"]),
                            "nodesAfter": count_nodes(new_pages[route]["tree"])})
    return {
        "pagesAdded": sorted(set(new_pages) - set(old_pages)),
        "pagesRemoved": sorted(set(old_pages) - set(new_pages)),
        "pagesChanged": changed,
        "entitiesAdded": sorted(set(new_ent) - set(old_ent)),
        "entitiesRemoved": sorted(set(old_ent) - set(new_ent)),
        "entitiesChanged": sorted(n for n in set(old_ent) & set(new_ent) if old_ent[n] != new_ent[n]),
        "tokensChanged": old.get("tokens") != new.get("tokens"),
        "layoutChanged": old.get("layout") != new.get("layout"),
    }
