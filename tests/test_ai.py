"""End-to-end AI flow using the NullProvider (AI_PROVIDER=null)."""

import os

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
