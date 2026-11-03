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


def test_log_disposition_is_ascii_safe():
    from app.routers import player as player_router

    header = player_router._log_disposition(7, "Андрей")
    header.encode("latin-1")  # HTTP-заголовки допускают только latin-1
    assert 'filename="log_player_7.txt"' in header
    assert "filename*=UTF-8''" in header


def test_log_export_works_with_cyrillic_name():
    from app import database

    created = client.post(
        "/player/", json={"user_token": "test-log-cyr", "name": "Иван Тестовый"}
    )
    assert created.status_code == 200
    player_id = created.json()["id"]
    try:
        response = client.get(f"/player/{player_id}/log")
        assert response.status_code == 200
        disposition = response.headers.get("Content-Disposition", "")
        disposition.encode("latin-1")  # заголовок не должен ломать кодировку
        assert "filename*=UTF-8''" in disposition
    finally:
        session = database.SessionLocal()
        session.query(database.Player).filter(database.Player.id == player_id).delete()
        session.commit()
        session.close()


def test_settings_endpoint_lists_providers_without_keys():
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()

    ids = {provider["id"] for provider in data["providers"]}
    assert {"gemini", "groq", "openrouter", "custom"} <= ids
    assert "has_key" in data["llm"]
    assert "key" not in data["llm"]
    assert "master" in data["sound"]
