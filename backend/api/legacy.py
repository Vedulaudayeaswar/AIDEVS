"""v1 "classic builder" endpoints, kept for backwards compatibility.

They now use the authenticated user id, the centralized AI key and no longer
accept/forward per-user API keys. New work happens in the Studio API.
"""
import io
import logging

from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import current_user, jwt_required

from api.common import json_body, rate_limit

bp = Blueprint("legacy", __name__, url_prefix="/api")
log = logging.getLogger("aidevs.legacy")
_orchestrator = None
_rag = None


def orchestrator():
    global _orchestrator, _rag
    if _orchestrator is None:
        from agents.orchestrator import AIDevsOrchestrator
        from utils.rag_manager import RAGManager
        _rag = RAGManager()
        _orchestrator = AIDevsOrchestrator(_rag)
    return _orchestrator


def _session_id():
    return f"{current_user.id}_session"


@bp.post("/chat")
@jwt_required()
@rate_limit("legacy-chat", limit=20, window=60, per_user=True)
def chat():
    message = str(json_body().get("message", "")).strip()
    if not message:
        return jsonify(success=False, error="Message is required"), 400
    orch = orchestrator()
    for agent in (orch.frontend_agent, orch.backend_agent, orch.test_agent):
        agent.user_id = current_user.id
    session = orch.sessions.get(_session_id())
    if session:
        session["lead_agent"].user_id = current_user.id
    response = orch.process_message(message[:4000], _session_id())
    orch.sessions[_session_id()]["lead_agent"].user_id = current_user.id
    return jsonify(success=True, response=response["message"], stage=response["stage"],
                   has_preview=response["has_preview"], using_default_key=True)


@bp.post("/preview")
@jwt_required()
def preview():
    code = orchestrator().get_preview_code(_session_id())
    return jsonify(success=True, html=code.get("html", ""), css="", js="")


@bp.post("/status")
@jwt_required()
def status():
    session = orchestrator().sessions.get(_session_id())
    if not session:
        return jsonify(success=True, has_session=False, frontend_ready=False, backend_ready=False,
                       download_ready=False)
    has_frontend = bool(session.get("frontend_code"))
    has_backend = len(session.get("backend_code", "") or "") > 100
    return jsonify(success=True, has_session=True, frontend_ready=has_frontend, backend_ready=has_backend,
                   download_ready=has_frontend and has_backend, current_stage=session.get("current_stage"),
                   sections_completed=list(session.get("frontend_code", {}).keys()))


@bp.post("/download")
@jwt_required()
def download():
    orch = orchestrator()
    session = orch.sessions.get(_session_id())
    if not session or not session.get("frontend_code"):
        return jsonify(success=False, error="No website built yet."), 404
    if len(session.get("backend_code", "") or "") < 100:
        return jsonify(success=False, error="Backend code is still being generated.", backend_ready=False), 400
    filename = orch.generate_download_package(_session_id())
    import os
    with open(os.path.join("downloads", filename), "rb") as fh:
        data = fh.read()
    os.remove(os.path.join("downloads", filename))
    return send_file(io.BytesIO(data), mimetype="application/zip", as_attachment=True,
                     download_name="aidevs_website.zip")


@bp.post("/reset")
@jwt_required()
def reset():
    orch = orchestrator()
    orch.sessions.pop(_session_id(), None)
    if _rag:
        _rag.clear_session(_session_id())
    return jsonify(success=True,
                   message="Session reset! Let's build something new. What kind of website would you like to create?")
