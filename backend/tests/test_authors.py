"""Happy-path tests for GET /api/authors."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_REQUIRED_FIELDS = {"id", "name", "slug", "has_style_profile", "n_documents"}


def test_list_authors_returns_three_seeded():
    resp = client.get("/api/authors")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert {a["id"] for a in data} == {"austen", "dickens", "poe"}


def test_list_authors_matches_contract_shape():
    data = client.get("/api/authors").json()
    for author in data:
        assert _REQUIRED_FIELDS.issubset(author.keys())
        assert author["slug"] == author["id"]
        assert author["has_style_profile"] is False
        assert isinstance(author["n_documents"], int)
        assert author["n_documents"] >= 0


def test_list_authors_names():
    by_id = {a["id"]: a["name"] for a in client.get("/api/authors").json()}
    assert by_id == {
        "austen": "Jane Austen",
        "dickens": "Charles Dickens",
        "poe": "Edgar Allan Poe",
    }
