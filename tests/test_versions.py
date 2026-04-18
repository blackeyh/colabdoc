"""Version history: list, fetch, and restore."""

from datetime import datetime

import pytest

import models


@pytest.fixture
def seed_version(db_session):
    def _seed(doc_id: int, user_id: int, version_number: int, content: dict):
        v = models.Version(
            document_id=doc_id,
            content=content,
            version_number=version_number,
            created_by=user_id,
            created_at=datetime.utcnow(),
        )
        db_session.add(v)
        db_session.commit()
    return _seed


def test_list_versions_empty(client, auth_header, doc_factory):
    doc = doc_factory("V")
    r = client.get(f"/documents/{doc['id']}/versions", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["versions"] == []


def test_list_versions_shows_entries(client, auth_header, auth_user, doc_factory, seed_version):
    doc = doc_factory("V2")
    seed_version(doc["id"], auth_user["id"], 1, {"type": "doc", "content": []})
    seed_version(doc["id"], auth_user["id"], 2, {"type": "doc", "content": []})
    r = client.get(f"/documents/{doc['id']}/versions", headers=auth_header)
    assert r.status_code == 200
    versions = r.json()["versions"]
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[1]["version_number"] == 1


def test_get_specific_version(client, auth_header, auth_user, doc_factory, seed_version):
    doc = doc_factory("V3")
    content = {"type": "doc", "content": [{"type": "paragraph"}]}
    seed_version(doc["id"], auth_user["id"], 1, content)
    r = client.get(f"/documents/{doc['id']}/versions/1", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["content"] == content


def test_restore_version_replaces_content(
    client, auth_header, auth_user, doc_factory, seed_version
):
    doc = doc_factory("V4")
    old_content = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "v1"}]}],
    }
    seed_version(doc["id"], auth_user["id"], 1, old_content)
    client.put(
        f"/documents/{doc['id']}",
        json={"content": {"type": "doc", "content": [{"type": "paragraph"}]}},
        headers=auth_header,
    )
    r = client.post(f"/documents/{doc['id']}/versions/restore/1", headers=auth_header)
    assert r.status_code == 200
    r2 = client.get(f"/documents/{doc['id']}", headers=auth_header)
    assert r2.json()["content"] == old_content


def test_restore_creates_snapshot_of_current(
    client, auth_header, auth_user, doc_factory, seed_version
):
    doc = doc_factory("V5")
    seed_version(doc["id"], auth_user["id"], 1, {"type": "doc", "content": []})
    client.put(
        f"/documents/{doc['id']}",
        json={"content": {"type": "doc", "content": [{"type": "paragraph"}]}},
        headers=auth_header,
    )
    client.post(f"/documents/{doc['id']}/versions/restore/1", headers=auth_header)
    r = client.get(f"/documents/{doc['id']}/versions", headers=auth_header)
    assert len(r.json()["versions"]) == 2


def test_viewer_cannot_restore(
    client, auth_user, user_factory, doc_factory, seed_version
):
    doc = doc_factory("V6")
    seed_version(doc["id"], auth_user["id"], 1, {"type": "doc", "content": []})
    viewer = user_factory(email="vr@example.com")
    client.post(
        f"/documents/{doc['id']}/permissions",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=auth_user["headers"],
    )
    r = client.post(
        f"/documents/{doc['id']}/versions/restore/1",
        headers=viewer["headers"],
    )
    assert r.status_code == 403
