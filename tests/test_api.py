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


def test_stat_whitelist_rejects_non_stats():
    response = client.post("/player/1/upgrade", json={"stat_name": "level"})
    assert response.status_code in (400, 404)
