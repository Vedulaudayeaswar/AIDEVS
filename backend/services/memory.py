"""Persistent project memory + relevant-context assembly for AI calls.

Authoritative state (spec, tokens, pages, entities) always comes from the
relational tables. Free-text memory items and chat history are ranked by
simple keyword overlap with the current request so each AI call receives only
compact, relevant context instead of the whole history.
"""
import json
import re

from sqlalchemy import select

from models import ChatMessage, MemoryItem

WORD = re.compile(r"[a-z0-9]{3,}")


def remember(session, project_id, kind, content):
    content = (content or "").strip()
    if content:
        session.add(MemoryItem(project_id=project_id, kind=kind, content=content[:2000]))


def _score(text, query_words):
    words = set(WORD.findall(text.lower()))
    return len(words & query_words)


def outline(tree, depth=0, max_depth=2):
    lines = []
    for child in tree.get("children", []):
        lines.append("  " * depth + f"- {child.get('name')} [{child['type']}#{child['id']}]")
        if depth + 1 < max_depth:
            lines.extend(outline(child, depth + 1, max_depth))
    return lines


def build_context(session, project, query="", include_outline=True, limit_chars=6000):
    query_words = set(WORD.findall((query or "").lower()))
    spec = project.spec or {}
    parts = [
        f"PROJECT: {project.name}",
        f"Purpose: {spec.get('summary') or project.description or project.prompt[:300]}",
        f"Audience: {spec.get('audience', 'n/a')} | Type: {spec.get('site_type', 'n/a')}",
        f"Brand voice: {spec.get('brand', {}).get('voice', 'n/a') if isinstance(spec.get('brand'), dict) else 'n/a'}",
        "Design tokens: " + json.dumps(project.tokens or {}),
        "Pages: " + ", ".join(f"{p.name} ({p.route})" for p in project.pages),
        "Data models: " + "; ".join(
            f"{e.name}({', '.join(f['name'] + ':' + f['type'] for f in e.fields)}) perms={e.permissions}"
            for e in project.entities) if project.entities else "Data models: none",
    ]
    if include_outline:
        for page in project.pages[:8]:
            parts.append(f"Page {page.route} sections:\n" + "\n".join(outline(page.tree, max_depth=1)))

    memories = session.scalars(select(MemoryItem).where(
        MemoryItem.project_id == project.id, MemoryItem.resolved.is_(False))
        .order_by(MemoryItem.created_at.desc()).limit(80)).all()
    ranked = sorted(memories, key=lambda m: (_score(m.content, query_words), m.created_at), reverse=True)
    if ranked:
        parts.append("Remembered decisions & instructions:\n" + "\n".join(
            f"- ({m.kind}) {m.content[:300]}" for m in ranked[:10]))

    recent = session.scalars(select(ChatMessage).where(ChatMessage.project_id == project.id)
                             .order_by(ChatMessage.created_at.desc()).limit(6)).all()
    if recent:
        parts.append("Recent conversation:\n" + "\n".join(
            f"{m.role}: {m.content[:300]}" for m in reversed(recent)))
    text = "\n".join(parts)
    return text[:limit_chars]
