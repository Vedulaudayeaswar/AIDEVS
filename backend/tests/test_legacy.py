"""The v1 classic builder still works, per user, on the central AI client."""


def test_classic_builder_chat_status_reset(client, headers, fake_ai):
    resp = client.post("/api/chat", json={"message": "hello"}, headers=headers)
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["success"] and body["response"] and body["stage"] == "initial"
    assert fake_ai.calls and fake_ai.calls[-1]["kind"] == "chat"
    status = client.post("/api/status", headers=headers).get_json()
    assert status["has_session"] is True and status["download_ready"] is False
    assert client.post("/api/reset", headers=headers).get_json()["success"]
    assert client.post("/api/chat", json={"message": "x"}).status_code == 401
