"""WebSocket: auth, init payload, update broadcast, typing broadcast."""

import json

from starlette.websockets import WebSocketDisconnect


def _connect(client, doc_id, token):
    return client.websocket_connect(f"/ws/documents/{doc_id}?token={token}")


def test_ws_rejects_invalid_token(client, doc_factory):
    doc = doc_factory("WS")
    try:
        with client.websocket_connect(f"/ws/documents/{doc['id']}?token=nope"):
            pass
    except WebSocketDisconnect as e:
        assert e.code == 4001
    else:
        raise AssertionError("expected close 4001 for invalid token")


def test_ws_init_payload(client, auth_user, doc_factory):
    doc = doc_factory("WS2")
    with _connect(client, doc["id"], auth_user["access_token"]) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "init"
        assert msg["title"] == "WS2"
        assert msg["role"] == "owner"
        assert isinstance(msg["active_users"], list)


def test_ws_update_broadcasts_to_other_clients(
    client, auth_user, user_factory, doc_factory
):
    doc = doc_factory("WS3")
    editor = user_factory(email="wse@example.com")
    # Owner shares with editor
    client.post(
        f"/documents/{doc['id']}/permissions",
        json={"user_id": editor["id"], "role": "editor"},
        headers=auth_user["headers"],
    )

    with _connect(client, doc["id"], auth_user["access_token"]) as ws_owner, \
         _connect(client, doc["id"], editor["access_token"]) as ws_editor:
        # Consume init frames from both
        ws_owner.receive_json()
        ws_editor.receive_json()
        # Also consume user_joined broadcast the second connection triggers
        # (delivered to the first socket)
        try:
            ws_owner.receive_json()
        except Exception:
            pass

        new_content = {"type": "doc", "content": [{"type": "paragraph"}]}
        ws_owner.send_text(json.dumps({"type": "update", "content": new_content}))

        # Editor should see the broadcast.
        msg = None
        for _ in range(5):
            try:
                msg = ws_editor.receive_json()
            except Exception:
                break
            if msg.get("type") == "update":
                break
        assert msg is not None
        assert msg["type"] == "update"
        assert msg["content"] == new_content


def test_ws_typing_broadcast(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("WS4")
    editor = user_factory(email="wst@example.com")
    client.post(
        f"/documents/{doc['id']}/permissions",
        json={"user_id": editor["id"], "role": "editor"},
        headers=auth_user["headers"],
    )

    with _connect(client, doc["id"], auth_user["access_token"]) as ws_owner, \
         _connect(client, doc["id"], editor["access_token"]) as ws_editor:
        ws_owner.receive_json()  # init
        ws_editor.receive_json()  # init
        try:
            ws_owner.receive_json()  # user_joined
        except Exception:
            pass

        ws_owner.send_text(json.dumps({"type": "typing"}))

        msg = None
        for _ in range(5):
            try:
                msg = ws_editor.receive_json()
            except Exception:
                break
            if msg.get("type") == "typing":
                break
        assert msg is not None
        assert msg["type"] == "typing"
        assert msg["user"]["id"] == auth_user["id"]
