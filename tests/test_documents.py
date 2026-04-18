"""Document CRUD happy path."""


def test_create_document(client, auth_header):
    r = client.post("/documents", json={"title": "My Doc"}, headers=auth_header)
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "My Doc"
    assert "id" in body


def test_create_document_requires_title(client, auth_header):
    r = client.post("/documents", json={"title": ""}, headers=auth_header)
    assert r.status_code == 400


def test_list_documents_includes_owned(client, auth_header, doc_factory):
    doc_factory("A")
    doc_factory("B")
    r = client.get("/documents", headers=auth_header)
    assert r.status_code == 200
    titles = sorted(d["title"] for d in r.json()["documents"])
    assert titles == ["A", "B"]


def test_get_document_owner(client, auth_header, doc_factory):
    doc = doc_factory("D")
    r = client.get(f"/documents/{doc['id']}", headers=auth_header)
    assert r.status_code == 200
    assert r.json()["id"] == doc["id"]


def test_get_document_not_found(client, auth_header):
    r = client.get("/documents/99999", headers=auth_header)
    assert r.status_code == 404


def test_update_document_content(client, auth_header, doc_factory):
    doc = doc_factory("E")
    new_content = {"type": "doc", "content": [{"type": "paragraph"}]}
    r = client.put(
        f"/documents/{doc['id']}",
        json={"content": new_content, "title": "E2"},
        headers=auth_header,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "E2"
    assert body["content"] == new_content


def test_delete_document_owner(client, auth_header, doc_factory):
    doc = doc_factory("F")
    r = client.delete(f"/documents/{doc['id']}", headers=auth_header)
    assert r.status_code == 200
    r2 = client.get(f"/documents/{doc['id']}", headers=auth_header)
    assert r2.status_code == 404


def test_unauthorized_access(client):
    r = client.get("/documents")
    # Missing Authorization header
    assert r.status_code in (401, 403)
