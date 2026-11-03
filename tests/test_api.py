from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_index_page_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Text RPG" in response.text


def test_static_assets_are_served():
    for path in (
        "/static/css/base.css",
        "/static/css/layout.css",
        "/static/css/components.css",
        "/static/js/app.js",
        "/static/icons/weapon.svg",
        "/static/fantasy-background.jpg",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.content


def test_unknown_player_returns_404():
    response = client.get("/player/999999")
    assert response.status_code == 404


def test_genres_endpoint_returns_catalog():
    response = client.get("/genres")
    assert response.status_code == 200
    genres = response.json()["genres"]
    assert len(genres) >= 8
    assert all("stat_labels" in g for g in genres)


def test_stat_whitelist_rejects_non_stats():
    response = client.post("/player/1/upgrade", json={"stat_name": "level"})
    assert response.status_code in (400, 404)


def test_upload_rejects_unknown_genre_before_processing():
    files = {"file": ("book.txt", b"hello", "text/plain")}
    response = client.post("/upload_book/1", files=files, data={"genre": "nonsense"})
    assert response.status_code in (400, 404)


def test_reset_requires_post():
    # GET больше не поддерживается: сброс меняет состояние, значит POST.
    assert client.get("/reset/999999").status_code == 405


def test_reset_unknown_player_is_noop():
    response = client.post("/reset/999999")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
