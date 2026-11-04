"""Встроенные книги: каталог, наличие текстов и запуск кампании по книге."""

from collections import Counter

from fastapi.testclient import TestClient

import main
from app import database
from app.content import library
from app.services import rag

client = TestClient(main.app)


def test_every_genre_has_two_builtin_books():
    counts = Counter(book["genre"] for book in library.BOOKS)
    for code, amount in counts.items():
        assert amount >= 2, f"для жанра {code} меньше двух книг"
    # В каталоге нет выдуманных жанров.
    from app.content import genres

    assert all(code in genres.GENRES for code in counts)


def test_builtin_book_files_exist_and_have_text():
    for book in library.BOOKS:
        text = library.load_text(book["id"])
        assert text, f"нет текста для {book['id']}"
        # Отсекаем случайно пустые/битые страницы.
        assert len(text) > 2000, f"слишком мало текста для {book['id']}"


def test_library_endpoint_lists_books_without_text():
    response = client.get("/library")
    assert response.status_code == 200
    books = response.json()["books"]
    assert len(books) == len(library.BOOKS)
    for book in books:
        assert book["title"] and book["author"] and book["genre"]
        # Текст по сети не отдаём — только метаданные.
        assert "text" not in book and "filename" not in book


def test_open_unknown_book_returns_404():
    response = client.post("/library/1/open", json={"book_id": "нет-такой-книги"})
    assert response.status_code == 404


def test_open_builtin_book_starts_campaign(tmp_path, monkeypatch):
    # Пишем книгу во временную папку и отключаем эмбеддинги: тест не должен
    # зависеть от локальной Ollama и не трогать реальные данные.
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    monkeypatch.setattr(rag, "BOOKS_DIR", books_dir)
    monkeypatch.setattr(rag.embeddings, "available", lambda: False)

    created = client.post(
        "/player/", json={"user_token": "test-library", "name": "Читатель"}
    )
    assert created.status_code == 200
    player_id = created.json()["id"]

    try:
        response = client.post(
            f"/library/{player_id}/open", json={"book_id": "fatalist"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["chunks"] > 0
        assert data["book"]["title"] == "Фаталист"
        assert data["genre"]["code"] == "mystery"
        assert (books_dir / f"book_{player_id}.json").exists()

        session = database.SessionLocal()
        player = (
            session.query(database.Player)
            .filter(database.Player.id == player_id)
            .first()
        )
        assert player.book_file == f"book_{player_id}.json"
        assert player.genre == "mystery"
        session.close()
    finally:
        session = database.SessionLocal()
        session.query(database.Player).filter(
            database.Player.id == player_id
        ).delete()
        session.commit()
        session.close()
