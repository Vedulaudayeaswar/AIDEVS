"""Asset manager: validated image uploads stored in the database.

Images are decoded with Pillow to verify they really are images (magic bytes
alone can be spoofed); SVG is rejected because it can carry scripts. Files are
stored in the DB because Render's filesystem is ephemeral. Assets are served
from unguessable 128-bit ids without auth so <img> tags in the sandboxed
preview (which cannot send credentials) can load them.
"""
import io
import re

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import current_user, jwt_required
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from api.common import ApiError, get_owned_project, rate_limit
from db import get_session
from models import Asset
from services import limits

bp = Blueprint("assets", __name__, url_prefix="/api")
ALLOWED = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "WEBP": "image/webp"}
MAX_PIXELS = 40_000_000


def asset_dict(a):
    return {"id": a.id, "filename": a.filename, "contentType": a.content_type, "size": a.size,
            "width": a.width, "height": a.height, "url": f"/api/assets/{a.id}",
            "createdAt": a.created_at.isoformat()}


@bp.get("/projects/<project_id>/assets")
@jwt_required()
def list_assets(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    rows = s.scalars(select(Asset).where(Asset.project_id == project.id).order_by(Asset.created_at.desc())).all()
    return jsonify(assets=[asset_dict(a) for a in rows])


@bp.post("/projects/<project_id>/assets")
@jwt_required()
@rate_limit("asset-upload", limit=30, window=60, per_user=True)
def upload_asset(project_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    file = request.files.get("file")
    if file is None:
        raise ApiError("No file uploaded", 400)
    max_bytes = limits.get("max_asset_mb") * 1024 * 1024
    data = file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ApiError(f"File too large (max {limits.get('max_asset_mb')} MB)", 413)
    limits.check_storage_quota(s, current_user.id, len(data))
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise ApiError("Only PNG, JPEG, GIF and WebP images are supported", 400) from None
    if fmt not in ALLOWED:
        raise ApiError("Only PNG, JPEG, GIF and WebP images are supported", 400)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", file.filename or "image")[:120] or "image"
    asset = Asset(project_id=project.id, filename=name, content_type=ALLOWED[fmt], size=len(data),
                  width=width, height=height, data=data)
    s.add(asset)
    s.commit()
    return jsonify(asset=asset_dict(asset)), 201


@bp.delete("/projects/<project_id>/assets/<asset_id>")
@jwt_required()
def delete_asset(project_id, asset_id):
    s = get_session()
    project = get_owned_project(project_id, s)
    asset = s.get(Asset, asset_id)
    if asset is None or asset.project_id != project.id:
        raise ApiError("Asset not found", 404)
    s.delete(asset)
    s.commit()
    return jsonify(success=True)


@bp.get("/assets/<asset_id>")
def serve_asset(asset_id):
    if not re.fullmatch(r"[0-9a-f]{32}", asset_id):
        raise ApiError("Not found", 404)
    asset = get_session().get(Asset, asset_id)
    if asset is None:
        raise ApiError("Not found", 404)
    resp = Response(asset.data, mimetype=asset.content_type)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Content-Security-Policy"] = "default-src 'none'"
    resp.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    return resp
