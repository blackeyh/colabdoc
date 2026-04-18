"""ACL checks across the four roles: owner, editor, commenter, viewer."""

import pytest


@pytest.fixture
def shared_setup(client, auth_user, user_factory, doc_factory):
    """Owner creates a doc; three other users get editor/commenter/viewer roles."""
    doc = doc_factory("Shared")
    editor = user_factory(email="editor@example.com")
    commenter = user_factory(email="commenter@example.com")
    viewer = user_factory(email="viewer@example.com")
    for u, role in [(editor, "editor"), (commenter, "commenter"), (viewer, "viewer")]:
        r = client.post(
            f"/documents/{doc['id']}/permissions",
            json={"user_id": u["id"], "role": role},
            headers=auth_user["headers"],
        )
        assert r.status_code == 201
    return {
        "doc": doc,
        "owner": auth_user,
        "editor": editor,
        "commenter": commenter,
        "viewer": viewer,
    }


def test_owner_can_update(client, shared_setup):
    r = client.put(
        f"/documents/{shared_setup['doc']['id']}",
        json={"title": "renamed"},
        headers=shared_setup["owner"]["headers"],
    )
    assert r.status_code == 200


def test_editor_can_update(client, shared_setup):
    r = client.put(
        f"/documents/{shared_setup['doc']['id']}",
        json={"title": "by-editor"},
        headers=shared_setup["editor"]["headers"],
    )
    assert r.status_code == 200


def test_commenter_cannot_update(client, shared_setup):
    r = client.put(
        f"/documents/{shared_setup['doc']['id']}",
        json={"title": "by-commenter"},
        headers=shared_setup["commenter"]["headers"],
    )
    assert r.status_code == 403


def test_viewer_cannot_update(client, shared_setup):
    r = client.put(
        f"/documents/{shared_setup['doc']['id']}",
        json={"title": "by-viewer"},
        headers=shared_setup["viewer"]["headers"],
    )
    assert r.status_code == 403


def test_viewer_can_read(client, shared_setup):
    r = client.get(
        f"/documents/{shared_setup['doc']['id']}",
        headers=shared_setup["viewer"]["headers"],
    )
    assert r.status_code == 200


def test_only_owner_can_delete(client, shared_setup):
    r = client.delete(
        f"/documents/{shared_setup['doc']['id']}",
        headers=shared_setup["editor"]["headers"],
    )
    assert r.status_code == 403


def test_only_owner_can_grant(client, shared_setup, user_factory):
    stranger = user_factory(email="stranger@example.com")
    r = client.post(
        f"/documents/{shared_setup['doc']['id']}/permissions",
        json={"user_id": stranger["id"], "role": "viewer"},
        headers=shared_setup["editor"]["headers"],
    )
    assert r.status_code == 403


def test_invalid_role_rejected(client, shared_setup, user_factory):
    stranger = user_factory(email="stranger2@example.com")
    r = client.post(
        f"/documents/{shared_setup['doc']['id']}/permissions",
        json={"user_id": stranger["id"], "role": "admin"},
        headers=shared_setup["owner"]["headers"],
    )
    assert r.status_code == 400


def test_revoke_removes_access(client, shared_setup):
    doc_id = shared_setup["doc"]["id"]
    viewer_id = shared_setup["viewer"]["id"]
    r = client.delete(
        f"/documents/{doc_id}/permissions/{viewer_id}",
        headers=shared_setup["owner"]["headers"],
    )
    assert r.status_code == 200
    r2 = client.get(f"/documents/{doc_id}", headers=shared_setup["viewer"]["headers"])
    assert r2.status_code == 403


def test_update_role_promotes_viewer_to_editor(client, shared_setup):
    doc_id = shared_setup["doc"]["id"]
    viewer_id = shared_setup["viewer"]["id"]
    r = client.put(
        f"/documents/{doc_id}/permissions/{viewer_id}",
        json={"role": "editor"},
        headers=shared_setup["owner"]["headers"],
    )
    assert r.status_code == 200
    # Now can update the doc
    r2 = client.put(
        f"/documents/{doc_id}",
        json={"title": "promoted"},
        headers=shared_setup["viewer"]["headers"],
    )
    assert r2.status_code == 200
