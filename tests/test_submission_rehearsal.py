"""Submission-style integration rehearsal covering the main grading path."""

from __future__ import annotations

import json


def _connect(client, doc_id, token):
    return client.websocket_connect(f"/ws/documents/{doc_id}?token={token}")


def _receive_until(ws, expected_type, limit=10):
    for _ in range(limit):
        msg = ws.receive_json()
        if msg.get("type") == expected_type:
            return msg
    raise AssertionError(f"expected {expected_type} within {limit} frames")


def test_assignment_2_submission_rehearsal(client, auth_user, user_factory, doc_factory):
    owner = auth_user
    editor = user_factory(name="Eddie", email="editor@example.com")
    viewer = user_factory(name="Vera", email="viewer@example.com")
    commenter = user_factory(name="Cara", email="commenter@example.com")

    refresh = client.post("/auth/refresh", json={"refresh_token": owner["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]

    doc = doc_factory("Final Demo")
    rich_content = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": "Final Demo"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "This document is used for the final rehearsal."}],
            },
        ],
    }
    update = client.put(
        f"/documents/{doc['id']}",
        json={"content": rich_content},
        headers=owner["headers"],
    )
    assert update.status_code == 200

    for user, role in ((editor, "editor"), (viewer, "viewer"), (commenter, "commenter")):
        grant = client.post(
            f"/documents/{doc['id']}/permissions",
            json={"user_id": user["id"], "role": role},
            headers=owner["headers"],
        )
        assert grant.status_code == 201

    permissions = client.get(f"/documents/{doc['id']}/permissions", headers=owner["headers"])
    assert permissions.status_code == 200
    roles = {entry["user_id"]: entry["role"] for entry in permissions.json()["permissions"]}
    assert roles[editor["id"]] == "editor"
    assert roles[viewer["id"]] == "viewer"
    assert roles[commenter["id"]] == "commenter"

    with _connect(client, doc["id"], owner["access_token"]) as ws_owner, \
         _connect(client, doc["id"], editor["access_token"]) as ws_editor:
        owner_init = ws_owner.receive_json()
        editor_init = ws_editor.receive_json()
        assert owner_init["type"] == "init"
        assert owner_init["role"] == "owner"
        assert editor_init["role"] == "editor"

        joined = _receive_until(ws_owner, "user_joined")
        assert joined["user"]["id"] == editor["id"]
        sync_request = _receive_until(ws_owner, "sync_request")
        assert sync_request["requester"]["id"] == editor["id"]

        ws_owner.send_text(json.dumps({
            "type": "crdt_snapshot",
            "snapshot": "seed-snapshot",
            "target_user_id": editor["id"],
        }))
        replay = _receive_until(ws_editor, "crdt_snapshot")
        assert replay["snapshot"] == "seed-snapshot"

        ws_owner.send_text(json.dumps({
            "type": "typing",
        }))
        typing_msg = _receive_until(ws_editor, "typing")
        assert typing_msg["user"]["id"] == owner["id"]

        ws_owner.send_text(json.dumps({
            "type": "cursor",
            "position": {"start": 1, "end": 8},
        }))
        cursor_msg = _receive_until(ws_editor, "cursor")
        assert cursor_msg["position"]["start"] == 1
        assert cursor_msg["position"]["end"] == 8

        ws_owner.send_text(json.dumps({
            "type": "crdt_update",
            "update": "delta-1",
            "snapshot": "snapshot-1",
        }))
        live_update = _receive_until(ws_editor, "crdt_update")
        assert live_update["update"] == "delta-1"
        assert live_update["user"]["id"] == owner["id"]

        saved_content = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Final Demo"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Editors can persist shared work."}],
                },
            ],
        }
        ws_owner.send_text(json.dumps({
            "type": "persist",
            "content": saved_content,
            "save_version": True,
        }))

    doc_after_persist = client.get(f"/documents/{doc['id']}", headers=owner["headers"])
    assert doc_after_persist.status_code == 200
    assert doc_after_persist.json()["content"] == saved_content

    versions = client.get(f"/documents/{doc['id']}/versions", headers=owner["headers"])
    assert versions.status_code == 200
    assert versions.json()["versions"][0]["version_number"] == 1

    viewer_ai = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "shared work", "action": "rewrite"},
        headers=viewer["headers"],
    )
    commenter_ai = client.post(
        f"/documents/{doc['id']}/ai/assist",
        json={"selected_text": "shared work", "action": "rewrite"},
        headers=commenter["headers"],
    )
    assert viewer_ai.status_code == 403
    assert commenter_ai.status_code == 403

    with client.stream(
        "POST",
        f"/documents/{doc['id']}/ai/assist/stream",
        json={"selected_text": "Editors can persist shared work.", "action": "summarize"},
        headers={**editor["headers"], "Accept": "text/event-stream"},
    ) as response:
        assert response.status_code == 200
        stream_payload = "".join(response.iter_text())

    assert "event: meta" in stream_payload
    assert "event: delta" in stream_payload
    assert "event: done" in stream_payload

    history = client.get(
        f"/documents/{doc['id']}/ai/history?limit=5&offset=0",
        headers=viewer["headers"],
    )
    assert history.status_code == 200
    assert history.json()["total"] == 1
    interaction = history.json()["history"][0]
    assert interaction["user_name"] == "Eddie"
    assert interaction["provider_name"] == "null"

    resolve = client.post(
        f"/documents/{doc['id']}/ai/interactions/{interaction['id']}/resolve",
        json={"user_action": "accepted"},
        headers=editor["headers"],
    )
    assert resolve.status_code == 200
    assert resolve.json()["user_action"] == "accepted"

    export = client.get(
        f"/documents/{doc['id']}/export?format=txt",
        headers=viewer["headers"],
    )
    assert export.status_code == 200
    assert "Final Demo" in export.text
    assert "Editors can persist shared work." in export.text

    second_content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Version two content"}],
            }
        ],
    }
    mutate = client.put(
        f"/documents/{doc['id']}",
        json={"content": second_content},
        headers=owner["headers"],
    )
    assert mutate.status_code == 200

    restore = client.post(
        f"/documents/{doc['id']}/versions/restore/1",
        headers=owner["headers"],
    )
    assert restore.status_code == 200
    restored_doc = client.get(f"/documents/{doc['id']}", headers=owner["headers"])
    assert restored_doc.status_code == 200
    assert restored_doc.json()["content"] == saved_content
