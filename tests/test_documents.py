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


def test_export_document_html(client, auth_header, doc_factory):
    doc = doc_factory("Sprint Notes")
    rich_content = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Release Plan"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Ship the "},
                    {"type": "text", "text": "export", "marks": [{"type": "bold"}]},
                    {"type": "text", "text": " flow."},
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "HTML download"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Text download"}],
                            }
                        ],
                    },
                ],
            },
            {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "print('ready')"}],
            },
        ],
    }
    update = client.put(
        f"/documents/{doc['id']}",
        json={"content": rich_content},
        headers=auth_header,
    )
    assert update.status_code == 200

    r = client.get(f"/documents/{doc['id']}/export?format=html", headers=auth_header)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'attachment; filename="sprint-notes.html"' == r.headers["content-disposition"]
    assert "<h1>Sprint Notes</h1>" in r.text
    assert "<h2>Release Plan</h2>" in r.text
    assert "<strong>export</strong>" in r.text
    assert "<ul>" in r.text
    assert "print(&#x27;ready&#x27;)" in r.text


def test_export_document_txt_allows_viewer(client, auth_user, user_factory, doc_factory):
    doc = doc_factory("Shared")
    viewer = user_factory(email="viewer@example.com")
    share = client.post(
        f"/documents/{doc['id']}/permissions",
        json={"user_id": viewer["id"], "role": "viewer"},
        headers=auth_user["headers"],
    )
    assert share.status_code == 201

    doc_id = doc["id"]
    content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Read-only users can export."}],
            },
            {
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Open document"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Download copy"}],
                            }
                        ],
                    },
                ],
            },
        ],
    }
    update = client.put(
        f"/documents/{doc_id}",
        json={"content": content},
        headers=auth_user["headers"],
    )
    assert update.status_code == 200

    r = client.get(
        f"/documents/{doc_id}/export?format=txt",
        headers=viewer["headers"],
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "Shared" in r.text
    assert "Read-only users can export." in r.text
    assert "1. Open document" in r.text
    assert "2. Download copy" in r.text


def test_export_document_requires_access(client, doc_factory, user_factory, auth_header):
    doc = doc_factory("Secret")
    outsider = user_factory(email="outsider@example.com")
    r = client.get(
        f"/documents/{doc['id']}/export?format=txt",
        headers=outsider["headers"],
    )
    assert r.status_code == 403


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
