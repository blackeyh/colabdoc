"""End-to-end AI flow using the NullProvider (AI_PROVIDER=null)."""

import os
import json

os.environ["AI_PROVIDER"] = "null"


def test_ai_assist_returns_canned_output_and_persists_interaction(
    client, auth_header, doc_factory
):
    doc = doc_factory("AIDoc")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "hello world", "action": "rewrite"},
        headers=auth_header,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["action"] == "rewrite"
    assert body["suggestion"].startswith("[null-provider]")
    assert isinstance(body["id"], int)

    history = client.get(
        f"/documents/{doc['id']}/ai/history?limit=5&offset=0",
        headers=auth_header,
    )
    assert history.status_code == 200
    entry = history.json()["history"][0]
    assert entry["selected_text"] == "hello world"
    assert entry["provider_name"] == "null"
    assert entry["model_name"] == "null-provider"
    assert "Text to rewrite:" in entry["prompt_text"]


def test_ai_assist_requires_non_empty_selection(client, auth_header, doc_factory):
    doc = doc_factory("X")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "   ", "action": "rewrite"},
        headers=auth_header,
    )
    assert r.status_code == 400


def test_ai_assist_rejects_unknown_action(client, auth_header, doc_factory):
    doc = doc_factory("X")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "foo", "action": "hallucinate"},
        headers=auth_header,
    )
    assert r.status_code == 400


def test_ai_assist_requires_permission(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("Private")
    stranger = user_factory(email="stranger@example.com")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "foo", "action": "summarize"},
        headers=stranger["headers"],
    )
    assert r.status_code == 403


def test_ai_assist_forbids_viewer_and_commenter(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("Restricted AI")
    viewer = user_factory(email="viewer-ai@example.com")
    commenter = user_factory(email="commenter-ai@example.com")
    for user, role in ((viewer, "viewer"), (commenter, "commenter")):
        grant = client.post(
            f"/documents/{doc['id']}/permissions",
            json={"user_id": user["id"], "role": role},
            headers=auth_user["headers"],
        )
        assert grant.status_code == 201

        r = client.post(
            f"/documents/{doc['id']}/ai/assist",
            json={"selected_text": "foo", "action": "summarize"},
            headers=user["headers"],
        )
        assert r.status_code == 403


def test_ai_stream_returns_sse_events_and_persists_completion(client, auth_header, doc_factory):
    doc = doc_factory("AI Stream")
    with client.stream(
        "POST",
        f"/documents/{doc['id']}/ai/assist/stream",
        json={"selected_text": "hello world", "action": "rewrite"},
        headers={**auth_header, "Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        payload = "".join(response.iter_text())

    assert "event: meta" in payload
    assert "event: delta" in payload
    assert "event: done" in payload
    assert '"status": "completed"' in payload or '"status":"completed"' in payload

    history = client.get(
        f"/documents/{doc['id']}/ai/history?limit=5&offset=0",
        headers=auth_header,
    )
    assert history.status_code == 200
    body = history.json()
    assert body["total"] == 1
    assert body["history"][0]["status"] == "completed"
    assert body["history"][0]["suggestion"]
    assert body["history"][0]["provider_name"] == "null"
    assert body["history"][0]["model_name"] == "null-provider"


def test_ai_resolve_accepted(client, auth_header, doc_factory):
    doc = doc_factory("R")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "hello", "action": "rewrite"},
        headers=auth_header,
    )
    interaction_id = r.json()["id"]
    r2 = client.post(
        f"/documents/{doc['id']}/ai/interactions/{interaction_id}/resolve",
        json={"user_action": "accepted"},
        headers=auth_header,
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["user_action"] == "accepted"
    assert body["final_text"] is not None


def test_ai_resolve_edited_stores_final_text(client, auth_header, doc_factory):
    doc = doc_factory("RE")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "hello", "action": "rewrite"},
        headers=auth_header,
    )
    interaction_id = r.json()["id"]
    r2 = client.post(
        f"/documents/{doc['id']}/ai/interactions/{interaction_id}/resolve",
        json={"user_action": "edited", "edited_text": "my custom edit"},
        headers=auth_header,
    )
    assert r2.status_code == 200
    assert r2.json()["final_text"] == "my custom edit"


def test_ai_resolve_rejected(client, auth_header, doc_factory):
    doc = doc_factory("RJ")
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "hello", "action": "rewrite"},
        headers=auth_header,
    )
    interaction_id = r.json()["id"]
    r2 = client.post(
        f"/documents/{doc['id']}/ai/interactions/{interaction_id}/resolve",
        json={"user_action": "rejected"},
        headers=auth_header,
    )
    assert r2.status_code == 200
    assert r2.json()["user_action"] == "rejected"
    assert r2.json()["final_text"] is None


def test_ai_resolve_wrong_user_forbidden(
    client, auth_user, user_factory, doc_factory
):
    doc = doc_factory("OW")
    # Owner creates an interaction
    r = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "hello", "action": "rewrite"},
        headers=auth_user["headers"],
    )
    interaction_id = r.json()["id"]
    # Another user (with access) tries to resolve it
    editor = user_factory(email="ed@example.com")
    client.post(
        f"/documents/{doc['id']}/permissions",
        json={"user_id": editor["id"], "role": "editor"},
        headers=auth_user["headers"],
    )
    r2 = client.post(
        f"/documents/{doc['id']}/ai/interactions/{interaction_id}/resolve",
        json={"user_action": "accepted"},
        headers=editor["headers"],
    )
    assert r2.status_code == 403


def test_ai_history_paginates(client, auth_header, doc_factory):
    doc = doc_factory("H")
    for i in range(3):
        client.post(
            f"/documents/{doc['id']}/ai/assist",
            json={"selected_text": f"text {i}", "action": "summarize"},
            headers=auth_header,
        )
    r = client.get(
        f"/documents/{doc['id']}/ai/history?limit=2&offset=0",
        headers=auth_header,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["history"]) == 2
    # Next page
    r2 = client.get(
        f"/documents/{doc['id']}/ai/history?limit=2&offset=2",
        headers=auth_header,
    )
    assert len(r2.json()["history"]) == 1


def test_ai_history_is_document_wide_and_visible_to_viewer(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("History ACL")
    editor = user_factory(email="editor-history@example.com")
    viewer = user_factory(email="viewer-history@example.com")
    for user, role in ((editor, "editor"), (viewer, "viewer")):
        grant = client.post(
            f"/documents/{doc['id']}/permissions",
            json={"user_id": user["id"], "role": role},
            headers=auth_user["headers"],
        )
        assert grant.status_code == 201

    owner_ai = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "owner text", "action": "summarize"},
        headers=auth_user["headers"],
    )
    assert owner_ai.status_code == 200
    editor_ai = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "editor text", "action": "rewrite"},
        headers=editor["headers"],
    )
    assert editor_ai.status_code == 200

    r = client.get(
        f"/documents/{doc['id']}/ai/history?limit=5&offset=0",
        headers=viewer["headers"],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    names = {entry["user_name"] for entry in body["history"]}
    assert names == {"Alice", "User1"}
    assert {entry["selected_text"] for entry in body["history"]} == {"owner text", "editor text"}


def test_ai_history_forbids_non_collaborator(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("History Private")
    stranger = user_factory(email="stranger-history@example.com")
    r = client.get(
        f"/documents/{doc['id']}/ai/history?limit=2&offset=0",
        headers=stranger["headers"],
    )
    assert r.status_code == 403
