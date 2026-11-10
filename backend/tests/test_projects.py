"""Acceptance tests for projects, generation, visual editing, export, versions and isolation."""
import copy
import io
import json
import zipfile


from services.schema import walk
from tests.conftest import PASSWORD, auth, register


def create_generated_project(client, headers):
    plan = client.post("/api/projects/plan", json={"prompt": "Build a modern e-commerce website for a premium "
                                                             "sneaker brand."}, headers=headers)
    assert plan.status_code == 200, plan.get_json()
    spec = plan.get_json()["spec"]
    created = client.post("/api/projects", json={"spec": spec, "prompt": "sneakers"}, headers=headers)
    assert created.status_code == 201, created.get_json()
    body = created.get_json()
    return body["project"]["id"], body["run"]


def load_page(client, headers, project_id, route="/"):
    project = client.get(f"/api/projects/{project_id}", headers=headers).get_json()["project"]
    page = next(p for p in project["pages"] if p["route"] == route)
    return client.get(f"/api/projects/{project_id}/pages/{page['id']}", headers=headers).get_json()["page"]


def save(client, headers, project_id, page, tree):
    resp = client.put(f"/api/projects/{project_id}/pages/{page['id']}",
                      json={"tree": tree, "baseRevision": page["revision"]}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def export_files(client, headers, project_id):
    resp = client.get(f"/api/projects/{project_id}/export", headers=headers)
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.data))
    return {name.split("/", 1)[1]: zf.read(name).decode("utf-8", "replace") for name in zf.namelist()}


def by_name(tree, name):
    return next(n for n, _ in walk(tree) if n.get("name") == name)


# ---------------------------------------------------------------- TEST 3 + 13
def test_single_prompt_generates_multi_page_app_with_one_central_key(client, headers, fake_ai):
    project_id, run = create_generated_project(client, headers)
    assert run["status"] == "succeeded", run
    project = client.get(f"/api/projects/{project_id}", headers=headers).get_json()["project"]
    assert project["status"] == "ready"
    assert [p["route"] for p in project["pages"]] == ["/", "/shop", "/contact"]
    names = {e["name"] for e in project["entities"]}
    assert names == {"product", "contact_message"}  # contact model auto-added for the form
    home = load_page(client, headers, project_id)
    shared = [c.get("shared") for c in home["tree"]["children"]]
    assert shared[0] == "header" and shared[-1] == "footer"
    assert any(n["type"] == "collection" for n, _ in walk(home["tree"]))
    # All AI calls went through the single platform client; usage was accounted per user.
    kinds = [c["kind"] for c in fake_ai.calls]
    assert kinds.count("plan") == 1 and kinds.count("page") == 3
    usage = client.get("/api/usage", headers=headers).get_json()
    assert usage["requests"] == 4 and usage["tokens"] > 0
    versions = client.get(f"/api/projects/{project_id}/versions", headers=headers).get_json()["versions"]
    assert versions[0]["label"] == "Initial generation"


def test_invalid_ai_page_falls_back_to_section_library(client, headers, fake_ai):
    fake_ai.overrides["page"] = "this is not json"
    project_id, run = create_generated_project(client, headers)
    assert run["status"] == "succeeded"
    assert run["result"]["fallbackPages"] == 3
    assert any(s["level"] == "warning" for s in run["steps"])
    home = load_page(client, headers, project_id)
    assert len(home["tree"]["children"]) >= 3


# ---------------------------------------------------------------- TEST 2 + 12
def test_projects_persist_and_are_isolated_between_users(client):
    alice = register(client, "Alice", "Smith", "alice@example.com")
    project = client.post("/api/projects", json={"blank": True, "name": "Alice site"},
                          headers=auth(alice)).get_json()["project"]
    client.post("/api/auth/logout", json={"refreshToken": alice["refreshToken"]}, headers=auth(alice))
    again = client.post("/api/auth/login", json={"identifier": "alice@example.com", "password": PASSWORD}).get_json()
    listed = client.get("/api/projects", headers=auth(again)).get_json()["projects"]
    assert [p["id"] for p in listed] == [project["id"]]

    bob = auth(register(client, "Bob", "Jones", "bob@example.com"))
    assert client.get("/api/projects", headers=bob).get_json()["projects"] == []
    pid, page_id = project["id"], project["pages"][0]["id"]
    for method, url in [("get", f"/api/projects/{pid}"), ("get", f"/api/projects/{pid}/pages/{page_id}"),
                        ("put", f"/api/projects/{pid}/pages/{page_id}"), ("get", f"/api/projects/{pid}/export"),
                        ("get", f"/api/projects/{pid}/versions"), ("delete", f"/api/projects/{pid}"),
                        ("post", f"/api/projects/{pid}/assistant"), ("get", f"/api/projects/{pid}/messages"),
                        ("post", f"/api/projects/{pid}/data/contact_message"),
                        ("post", f"/api/projects/{pid}/preview")]:
        resp = getattr(client, method)(url, json={"message": "hi", "tree": {}, "pageId": page_id}, headers=bob)
        assert resp.status_code == 404, (method, url, resp.status_code)
    assert client.get(f"/api/projects/{pid}", headers=auth(again)).status_code == 200


# ------------------------------------------------------------ TEST 5, 6, 7, 8
def test_visual_edits_sync_to_exported_source(client, headers):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    tree = copy.deepcopy(page["tree"])

    # TEST 5: edit hero heading text / font size / colour
    heading = by_name(tree, "Hero Heading")
    heading["props"]["text"] = "Run The Night"
    heading["styles"]["base"].update(fontSize="72px", color="#f97316")
    # TEST 6: drag the CTA button above the heading (reorder in its container)
    hero = by_name(tree, "Hero Section")
    cta = by_name(tree, "Shop CTA")
    hero["children"] = [cta] + [c for c in hero["children"] if c["id"] != cta["id"]]
    # TEST 7: delete the product grid section
    grid = by_name(tree, "Product Grid")
    tree["children"] = [c for c in tree["children"] if c["id"] != grid["id"]]
    # TEST 8: desktop change must not destroy the mobile override
    heading["styles"]["base"]["fontSize"] = "80px"
    save(client, headers, project_id, page, tree)

    files = export_files(client, headers, project_id)
    hero_file = next(src for path, src in files.items() if path.startswith("frontend/src/components/Hero"))
    assert '"Run The Night"' in hero_file
    assert hero_file.index("Shop now") < hero_file.index("Run The Night")
    css = files["frontend/src/styles/app.css"]
    assert f".n-{heading['id']} {{" in css and "font-size: 80px" in css and "color: #f97316" in css
    mobile_block = css[css.index("@media (max-width: 640px)"):]
    assert f".n-{heading['id']} {{ font-size: 36px; }}" in mobile_block
    home_page = files["frontend/src/pages/HomePage.jsx"]
    assert "ProductGrid" not in home_page
    sourcemap = json.loads(files["aidevs.sourcemap.json"])
    assert grid["id"] not in sourcemap and heading["id"] in sourcemap
    assert sourcemap[heading["id"]]["file"].startswith("frontend/src/components/Hero")


def test_stale_save_is_rejected(client, headers):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    save(client, headers, project_id, page, page["tree"])
    stale = client.put(f"/api/projects/{project_id}/pages/{page['id']}",
                       json={"tree": page["tree"], "baseRevision": page["revision"]}, headers=headers)
    assert stale.status_code == 409


def test_shared_header_edit_applies_to_every_page(client, headers):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    tree = copy.deepcopy(page["tree"])
    logo = by_name(tree, "Logo")
    logo["props"]["text"] = "STRIDE"
    save(client, headers, project_id, page, tree)
    shop = load_page(client, headers, project_id, "/shop")
    assert by_name(shop["tree"], "Logo")["props"]["text"] == "STRIDE"


# ---------------------------------------------------------------- security
def test_preview_is_sanitized_and_sandbox_ready(client, headers):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    tree = copy.deepcopy(page["tree"])
    heading = by_name(tree, "Hero Heading")
    heading["props"]["text"] = "<script>alert(1)</script>"
    heading["styles"]["base"]["background"] = "url(javascript:alert(1))"
    heading["props"]["onclick"] = "alert(1)"
    by_name(tree, "Shop CTA")["props"]["href"] = "javascript:alert(1)"
    tree["children"][1]["children"].append({"type": "script", "props": {"text": "x"}})
    html = client.post(f"/api/projects/{project_id}/preview", json={"pageId": page["id"], "tree": tree},
                       headers=headers).get_json()["html"]
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "javascript:" not in html and "onclick" not in html
    import re
    scripts = re.findall(r"<script[^>]*>", html)
    nonce = re.search(r"'nonce-([A-Za-z0-9_-]+)'", html.replace("&#x27;", "'")).group(1)
    assert len(scripts) == 2  # editor bridge + font loader, both platform-authored
    assert all(f'nonce="{nonce}"' in tag for tag in scripts)  # nothing else can run under the CSP
    assert "Content-Security-Policy" in html and "connect-src &#x27;none&#x27;" in html
    assert "Aero Runner" in html  # collection rendered from sample data


# ------------------------------------------------------------- TEST 4 (preview)
def test_preview_forms_write_through_generated_api_contract(client, headers):
    project_id, _ = create_generated_project(client, headers)
    url = f"/api/projects/{project_id}/data/contact_message"
    bad = client.post(url, json={"name": "Sam", "email": "nope"}, headers=headers)
    assert bad.status_code == 400 and "email" in bad.get_json()["error"]
    ok = client.post(url, json={"name": "Sam", "email": "sam@example.com", "message": "Hi!"}, headers=headers)
    assert ok.status_code == 201
    assert client.get(url, headers=headers).get_json()["items"][0]["message"] == "Hi!"
    product = client.post(f"/api/projects/{project_id}/data/product",
                          json={"title": "Night Glide", "price": "210"}, headers=headers)
    assert product.status_code == 201 and product.get_json()["item"]["price"] == 210.0
    page = load_page(client, headers, project_id)
    html = client.post(f"/api/projects/{project_id}/preview", json={"pageId": page["id"]},
                       headers=headers).get_json()["html"]
    assert "Night Glide" in html


# ------------------------------------------------------------ TEST 10, 14, 15
WISHLIST_PLAN = {
    "reply": "Added a wishlist: signed-in users can save products and view them on /wishlist.",
    "entities": [{"op": "add", "name": "wishlist_item", "label": "Wishlist items",
                  "fields": [{"name": "product_title", "type": "string", "required": True},
                             {"name": "note", "type": "text"}],
                  "permissions": {"read": "owner", "create": "auth", "update": "owner", "delete": "owner"}}],
    "pages": [{"op": "add", "name": "Wishlist", "route": "/wishlist", "sections": [
        {"type": "section", "name": "Wishlist", "children": [
            {"type": "heading", "tag": "h1", "name": "Wishlist heading", "props": {"text": "Your wishlist"}},
            {"type": "collection", "name": "Saved items", "props": {"entity": "wishlist_item"}, "children": [
                {"type": "container", "name": "Saved card", "children": [
                    {"type": "heading", "tag": "h3", "name": "Saved title", "props": {"text": "{{product_title}}"}}]}]},
            {"type": "form", "name": "Save form", "props": {"entity": "wishlist_item"}, "children": [
                {"type": "input", "name": "Product", "props": {"label": "Product", "name": "product_title",
                                                                "required": True}},
                {"type": "button", "name": "Save", "props": {"text": "Save"}}]}]}]}],
    "nav": [{"label": "Wishlist", "href": "/wishlist"}],
    "remember": ["Wishlist is per-user (owner permissions)"],
}


def test_ai_feature_request_adds_wishlist_without_touching_unrelated_pages(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    before_shop = load_page(client, headers, project_id, "/shop")["tree"]
    fake_ai.overrides["feature"] = WISHLIST_PLAN
    resp = client.post(f"/api/projects/{project_id}/assistant", json={"message": "Add a wishlist feature"},
                       headers=headers)
    assert resp.status_code == 202
    run = resp.get_json()["run"]
    run = client.get(f"/api/runs/{run['id']}", headers=headers).get_json()["run"]
    assert run["status"] == "succeeded", run
    project = client.get(f"/api/projects/{project_id}", headers=headers).get_json()["project"]
    assert "wishlist_item" in {e["name"] for e in project["entities"]}
    assert "/wishlist" in [p["route"] for p in project["pages"]]
    after_shop = load_page(client, headers, project_id, "/shop")["tree"]
    strip = lambda t: [c for c in t["children"] if not c.get("shared")]  # noqa: E731
    assert strip(after_shop) == strip(before_shop)
    header_links = [n["props"].get("href") for n, _ in walk(after_shop["children"][0]) if n["type"] == "link"]
    assert "/wishlist" in header_links
    files = export_files(client, headers, project_id)
    assert "class WishlistItem(db.Model)" in files["backend/models.py"]
    assert '"wishlist_item": "wishlist_items"' in files["frontend/src/api.js"]
    assert "def test_wishlist_item_crud" in files["backend/tests/test_api.py"]
    messages = client.get(f"/api/projects/{project_id}/messages", headers=headers).get_json()["messages"]
    assert "wishlist" in messages[-1]["content"].lower()


def test_failed_ai_change_does_not_corrupt_project(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    before = client.get(f"/api/projects/{project_id}?trees=1", headers=headers).get_json()["project"]
    fake_ai.overrides["feature"] = {"reply": "x", "pages": [{"op": "add_sections", "route": "/nope",
                                                             "sections": []}]}
    resp = client.post(f"/api/projects/{project_id}/assistant", json={"message": "break it"}, headers=headers)
    run = client.get(f"/api/runs/{resp.get_json()['run']['id']}", headers=headers).get_json()["run"]
    assert run["status"] == "failed"
    after = client.get(f"/api/projects/{project_id}?trees=1", headers=headers).get_json()["project"]
    assert after["pages"] == before["pages"] and after["entities"] == before["entities"]
    assert after["revision"] == before["revision"]
    messages = client.get(f"/api/projects/{project_id}/messages", headers=headers).get_json()["messages"]
    assert "not modified" in messages[-1]["content"]


def test_restore_previous_version(client, headers):
    project_id, _ = create_generated_project(client, headers)
    versions = client.get(f"/api/projects/{project_id}/versions", headers=headers).get_json()["versions"]
    initial = versions[0]
    page = load_page(client, headers, project_id)
    tree = copy.deepcopy(page["tree"])
    tree["children"] = [c for c in tree["children"] if c.get("shared")]  # wipe all own sections
    save(client, headers, project_id, page, tree)
    diff = client.get(f"/api/projects/{project_id}/versions/{initial['id']}/diff", headers=headers).get_json()["diff"]
    assert diff["pagesChanged"] and diff["pagesChanged"][0]["route"] == "/"
    restored = client.post(f"/api/projects/{project_id}/versions/{initial['id']}/restore", headers=headers)
    assert restored.status_code == 200
    page = load_page(client, headers, project_id)
    assert by_name(page["tree"], "Hero Heading")
    labels = [v["label"] for v in client.get(f"/api/projects/{project_id}/versions",
                                             headers=headers).get_json()["versions"]]
    assert labels[0].startswith("Before restoring")


# ---------------------------------------------------------- visual edit agent
def test_ai_edit_of_selected_element_returns_validated_node(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    heading = by_name(page["tree"], "Hero Heading")
    fake_ai.overrides["edit"] = {"node": {**heading, "props": {"text": "Bigger & bolder"},
                                          "styles": {"base": {"fontSize": "96px", "behavior": "url(x)"}}},
                                 "summary": "Made the heading bigger."}
    resp = client.post(f"/api/projects/{project_id}/assistant", headers=headers, json={
        "message": "make it bigger", "selection": {"pageId": page["id"], "nodeId": heading["id"],
                                                   "node": heading}})
    body = resp.get_json()
    assert resp.status_code == 200 and body["mode"] == "edit"
    assert body["node"]["id"] == heading["id"]
    assert body["node"]["styles"]["base"] == {"fontSize": "96px"}


def test_feature_request_with_selected_element_runs_as_feature(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    heading = by_name(page["tree"], "Hero Heading")
    resp = client.post(f"/api/projects/{project_id}/assistant", headers=headers, json={
        "message": "Add a notifications feature where each user can mark their own notifications as read",
        "selection": {"pageId": page["id"], "nodeId": heading["id"], "node": heading}})
    assert resp.status_code == 202 and resp.get_json()["mode"] == "feature", ([c["kind"] for c in fake_ai.calls], resp.get_json())
    assert not any(c["kind"] == "edit" for c in fake_ai.calls)


def test_visual_edit_that_needs_new_data_falls_back_to_feature(client, headers, fake_ai):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id)
    heading = by_name(page["tree"], "Hero Heading")
    fake_ai.overrides["edit"] = {"reply": "plan", "entities": [{"op": "add", "name": "alert"}]}  # not {"node"}
    resp = client.post(f"/api/projects/{project_id}/assistant", headers=headers, json={
        "message": "show the latest alerts here", "selection": {"pageId": page["id"], "nodeId": heading["id"],
                                                                "node": heading}})
    assert resp.status_code == 202 and resp.get_json()["mode"] == "feature", resp.get_json()
    assert any(c["kind"] == "feature" for c in fake_ai.calls)


# --------------------------------------------------------------- checks/assets
def test_checks_find_contract_errors(client, headers):
    project_id, _ = create_generated_project(client, headers)
    page = load_page(client, headers, project_id, "/contact")
    tree = copy.deepcopy(page["tree"])
    form = next(n for n, _ in walk(tree) if n["type"] == "form")
    form["children"] = [c for c in form["children"] if c["props"].get("name") != "email"]
    save(client, headers, project_id, page, tree)
    report = client.post(f"/api/projects/{project_id}/checks", headers=headers).get_json()["report"]
    assert not report["passed"]
    assert any("missing required field 'email'" in i["message"] for i in report["issues"])


def test_asset_upload_validation(client, headers):
    from PIL import Image
    project = client.post("/api/projects", json={"blank": True}, headers=headers).get_json()["project"]
    buf = io.BytesIO()
    Image.new("RGB", (4, 3), "red").save(buf, "PNG")
    up = client.post(f"/api/projects/{project['id']}/assets", headers=headers,
                     data={"file": (io.BytesIO(buf.getvalue()), "logo.png")}, content_type="multipart/form-data")
    assert up.status_code == 201
    asset = up.get_json()["asset"]
    assert asset["width"] == 4 and asset["contentType"] == "image/png"
    served = client.get(asset["url"])
    assert served.status_code == 200 and served.headers["X-Content-Type-Options"] == "nosniff"
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    bad = client.post(f"/api/projects/{project['id']}/assets", headers=headers,
                      data={"file": (io.BytesIO(svg), "x.svg")}, content_type="multipart/form-data")
    assert bad.status_code == 400


def test_export_jsx_is_well_formed_for_generated_layout(client, headers):
    """Regression: unsanitized layout nodes produced `<None>` tags in exported JSX."""
    import re
    project_id, _ = create_generated_project(client, headers)
    files = export_files(client, headers, project_id)
    jsx = {p: s for p, s in files.items() if p.endswith(".jsx")}
    assert "frontend/src/components/layout/SiteHeader.jsx" in jsx
    for path, src in jsx.items():
        assert "None" not in src, path
        for tag in re.findall(r"<([A-Za-z][A-Za-z0-9.]*)[\s>/]", src):
            assert tag[0].isupper() or tag in {
                "header", "footer", "section", "nav", "main", "div", "article", "aside", "ul", "li", "h1", "h2",
                "h3", "h4", "h5", "h6", "p", "span", "small", "blockquote", "strong", "a", "button", "img", "hr",
                "label", "input", "textarea", "select", "option", "form"}, (path, tag)


def test_generated_backend_tests_handle_booleans_and_nulls(tmp_path):
    """Regression found by the real-Groq run: JSON literals (false/null) were embedded in Python tests."""
    import subprocess
    import sys

    from services.export_backend import backend_files
    from services.schema import sanitize_entity
    task = sanitize_entity({"name": "task", "fields": [
        {"name": "title", "type": "string", "required": True}, {"name": "completed", "type": "boolean"},
        {"name": "notes", "type": "text"}], "permissions": {"read": "owner", "create": "auth",
                                                           "update": "owner", "delete": "owner"},
        "sample_data": [{"title": "Ship it", "completed": False}]})
    for path, content in backend_files("Bools", [task]).items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:asyncio", "-p", "no:cacheprovider"],
                            cwd=tmp_path / "backend", capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout[-2000:]
