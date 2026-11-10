"""Bounded validation-and-repair loop.

1. Run checks and capture error-level issues.
2. Apply deterministic fixes (they are exact and need no model):
   missing required form fields, links/bindings with an obvious intended target,
   images without alt text.
3. For remaining errors, ask the Error Analysis agent for a *targeted* fix of only
   the affected top-level section, with the issue list and project context.
4. Validate every proposal (schema sanitizer + contract checks), apply it, re-run
   checks, and keep it only if the number of errors decreased.
5. Stop after REPAIR_MAX_ATTEMPTS AI attempts. A snapshot is taken before any change,
   so the whole repair can be rolled back from Versions.

The loop never regenerates whole pages or touches sections without issues.
"""
import copy
import difflib
import logging
import os

from services import checks, versions
from services.jobs import JobCancelled
from services.schema import BINDING_RE, walk

log = logging.getLogger("aidevs.repair")
MAX_ATTEMPTS = int(os.getenv("REPAIR_MAX_ATTEMPTS", "2"))
INPUT_TYPES = {"email": "email", "integer": "number", "number": "number", "url": "url", "image": "url",
               "date": "date", "datetime": "text"}


def _errors(report):
    return [i for i in report["issues"] if i["severity"] == "error"]


def _find_with_parent(tree, node_id):
    for node, parent in walk(tree):
        if node["id"] == node_id:
            return node, parent
    return None, None


def _tree_for(project, route, node_id):
    if route in ("(shared header)", "(shared footer)"):
        key = "header" if "header" in route else "footer"
        return project.layout.get(key), ("layout", key)
    page = next((p for p in project.pages if p.route == route), None)
    return (page.tree, ("page", page)) if page else (None, None)


def _store(project, owner, tree):
    kind, ref = owner
    if kind == "layout":
        layout = copy.deepcopy(project.layout)
        layout[ref] = tree
        project.layout = layout
    else:
        ref.tree = tree
        ref.revision += 1


def _new_id(tree):
    from services.schema import all_ids, new_node_id
    taken = all_ids(tree)
    nid = new_node_id()
    while nid in taken:
        nid = new_node_id()
    return nid


def deterministic_fixes(project, report):
    """Exact fixes for well-understood issues. Returns a list of descriptions."""
    entity_map = {e.name: e for e in project.entities}
    routes = [p.route for p in project.pages]
    fixed = []
    for issue in _errors(report) + [i for i in report["issues"] if i["category"] == "accessibility"]:
        if not issue.get("nodeId") or not issue.get("route"):
            continue
        tree, owner = _tree_for(project, issue["route"], issue["nodeId"])
        if tree is None:
            continue
        tree = copy.deepcopy(tree)
        node, _parent = _find_with_parent(tree, issue["nodeId"])
        if node is None:
            continue
        msg = issue["message"]
        changed = False
        if issue["category"] == "contract" and "missing required field" in msg and node["type"] == "form":
            field_name = msg.split("missing required field '")[1].split("'")[0]
            ent = entity_map.get(node["props"].get("entity"))
            field = next((f for f in (ent.fields if ent else []) if f["name"] == field_name), None)
            if field:
                ctype = "textarea" if field["type"] == "text" else "input"
                props = {"label": field.get("label") or field_name.replace("_", " ").title(), "name": field_name,
                         "required": True}
                if ctype == "input":
                    props["inputType"] = INPUT_TYPES.get(field["type"], "text")
                template = next((c for c in node["children"] if c["type"] in ("input", "textarea")), None)
                new = {"id": _new_id(tree), "type": ctype, "name": f"{props['label']} Field", "tag": "label",
                       "props": props, "styles": copy.deepcopy(template["styles"]) if template else
                       {"base": {}, "tablet": {}, "mobile": {}}, "children": []}
                submit = next((i for i, c in enumerate(node["children"]) if c["type"] == "button"), None)
                node["children"].insert(submit if submit is not None else len(node["children"]), new)
                changed = True
        elif issue["category"] == "links" and "points to missing page" in msg:
            href = node["props"].get("href", "")
            match = difflib.get_close_matches(href, routes, n=1, cutoff=0.6)
            node["props"]["href"] = match[0] if match else "/"
            changed = True
        elif issue["category"] == "contract" and "has no such field" in msg:
            ent = entity_map.get(node["props"].get("entity"))
            names = [f["name"] for f in ent.fields] if ent else []
            for n, _ in walk(node):
                for key in ("text", "src", "alt", "href"):
                    value = n["props"].get(key)
                    if isinstance(value, str) and BINDING_RE.search(value):
                        def fix(m, names=names):
                            if m.group(1) in names:
                                return m.group(0)
                            close = difflib.get_close_matches(m.group(1), names, n=1, cutoff=0.6)
                            return "{{" + close[0] + "}}" if close else ""
                        n["props"][key] = BINDING_RE.sub(fix, value)
            changed = True
        elif issue["category"] == "accessibility" and node["type"] == "image" and not node["props"].get("alt"):
            node["props"]["alt"] = node.get("name") or "Image"
            changed = True
        if changed:
            _store(project, owner, tree)
            fixed.append(f"{issue['route']}: {msg}")
    return fixed


def _section_of(tree, node_id):
    for child in tree.get("children", []):
        if child["id"] == node_id or any(n["id"] == node_id for n, _ in walk(child)):
            return child
    return None


def ai_fix(session, project, report, user_id, step=None):
    """One targeted AI repair round. Returns description of applied fixes."""
    from agents.studio.editing import edit_node
    from agents.studio.orchestrator import entity_dicts
    from services.memory import build_context
    from services.schema import all_ids

    targets = {}
    for issue in _errors(report):
        if not issue.get("nodeId") or not issue.get("route"):
            continue
        tree, owner = _tree_for(project, issue["route"], issue["nodeId"])
        if tree is None:
            continue
        section = tree if owner[0] == "layout" else _section_of(tree, issue["nodeId"])
        if section is None:
            continue
        targets.setdefault((issue["route"], section["id"]), {"owner": owner, "issues": []})["issues"].append(
            issue["message"])
    applied = []
    context = build_context(session, project, "repair", include_outline=False, limit_chars=2500)
    for (route, section_id), info in list(targets.items())[:3]:
        tree, owner = _tree_for(project, route, section_id)
        section = tree if owner[0] == "layout" else _section_of(tree, section_id)
        instruction = ("Fix ONLY these validation errors, changing as little as possible and keeping all "
                       "content, ids and styles that are not involved:\n- " + "\n- ".join(info["issues"]))
        if step:
            step(f"Error analysis agent: repairing {len(info['issues'])} issue(s) in '{section.get('name')}' on {route}")
        result = edit_node(section, instruction, project.tokens or {}, entity_dicts(project.entities), context,
                           page_ids=all_ids(tree), user_id=user_id, project_id=project.id)
        new_tree = copy.deepcopy(tree)
        if owner[0] == "layout":
            new_tree = result["node"]
        else:
            new_tree["children"] = [result["node"] if c["id"] == section_id else c for c in new_tree["children"]]
        _store(project, owner, new_tree)
        applied.append(f"{route}: {result['summary'] or 'repaired section'}")
    return applied


def repair_project(session, project, user_id, *, use_ai=True, step=None, snapshot=True):
    """Run the bounded repair loop (commits progressively). Returns a report dict."""
    report = checks.run_checks(project, project.pages, project.entities)
    before = len(_errors(report))
    result = {"errorsBefore": before, "errorsAfter": before, "fixes": [], "aiAttempts": 0, "rolledBack": []}
    if before == 0:
        return result
    if snapshot:
        versions.snapshot(session, project, "Before automatic repair", "auto-repair", user_id)

    fixes = deterministic_fixes(project, report)
    session.commit()  # persist snapshot + exact fixes; never hold a write txn during model calls
    report = checks.run_checks(project, project.pages, project.entities)
    result["fixes"].extend(fixes)

    attempts = 0
    while use_ai and _errors(report) and attempts < MAX_ATTEMPTS:
        attempts += 1
        session.commit()
        saved = {"layout": copy.deepcopy(project.layout),
                 "pages": {p.id: copy.deepcopy(p.tree) for p in project.pages}}
        try:
            applied = ai_fix(session, project, report, user_id, step)
        except (JobCancelled, TimeoutError):
            raise  # user cancelled / job deadline: stop immediately
        except Exception as exc:  # AI unavailable/invalid: keep deterministic results
            log.warning("AI repair attempt failed", extra={"project_id": project.id, "error": str(exc)[:300]})
            result["rolledBack"].append(f"attempt {attempts}: {getattr(exc, 'user_message', str(exc))[:200]}")
            break
        session.flush()
        new_report = checks.run_checks(project, project.pages, project.entities)
        if len(_errors(new_report)) < len(_errors(report)):
            result["fixes"].extend(applied)
            report = new_report
        else:
            # Not an improvement: restore the exact pre-attempt state.
            project.layout = saved["layout"]
            for page in project.pages:
                page.tree = saved["pages"][page.id]
            session.flush()
            report = checks.run_checks(project, project.pages, project.entities)
            result["rolledBack"].append(f"attempt {attempts}: did not reduce errors")
    result["aiAttempts"] = attempts
    result["errorsAfter"] = len(_errors(report))
    result["report"] = report["summary"]
    log.info("repair finished", extra={"project_id": project.id, "status": f"{before}->{result['errorsAfter']}"})
    return result
