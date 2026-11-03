import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app import database
from app.dependencies import get_db
from app.services import saves


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    main.app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


def _make_player(db, name="Герой", token="tok", book="book_1.json", genre="fantasy"):
    player = database.Player(
        name=name, user_token=token, book_file=book, genre=genre, level=3
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def test_create_save_snapshots_player(db):
    player = _make_player(db)

    save = saves.create_save(db, player, user_token="tok")

    assert save.id
    assert save.snapshot["name"] == "Герой"
    assert save.snapshot["level"] == 3
    assert save.snapshot["book_file"] == "book_1.json"
    assert saves.save_summary(save)["genre"] == "fantasy"


def test_list_saves_is_scoped_to_user(db):
    for name, token in [("A", "u1"), ("B", "u2"), ("C", "u1")]:
        player = _make_player(db, name=name, token=token)
        saves.create_save(db, player, user_token=token)

    assert len(saves.list_saves(db, "u1")) == 2
    assert len(saves.list_saves(db, "u2")) == 1
    assert saves.list_saves(db, "") == []


def test_new_game_saves_session_and_creates_fresh_player(client, db):
    created = client.post("/player/", json={"name": "Старый", "user_token": "tok"}).json()
    player_id = created["id"]

    response = client.post(f"/player/{player_id}/new_game", json={"user_token": "tok"})
    assert response.status_code == 200
    data = response.json()

    assert data["saved_player_id"] == player_id
    assert data["player_id"] != player_id

    fresh = db.get(database.Player, data["player_id"])
    assert fresh.name == ""
    assert fresh.user_token == "tok"
    assert fresh.book_file == ""

    save = db.get(database.GameSave, data["save_id"])
    assert save.snapshot["name"] == "Старый"


def test_name_endpoint_fills_fresh_player(client, db):
    created = client.post("/player/", json={"name": "", "user_token": "tok"}).json()

    response = client.post(f"/player/{created['id']}/name", json={"name": "  Новый  "})
    assert response.status_code == 200
    assert response.json()["name"] == "Новый"

    assert db.get(database.Player, created["id"]).name == "Новый"


def test_name_endpoint_rejects_blank(client, db):
    created = client.post("/player/", json={"name": "", "user_token": "tok"}).json()
    response = client.post(f"/player/{created['id']}/name", json={"name": "   "})
    assert response.status_code == 400


def test_saves_endpoint_lists_for_token(client, db):
    player = _make_player(db, token="tok")
    saves.create_save(db, player, user_token="tok")

    response = client.get("/saves", params={"user_token": "tok"})
    assert response.status_code == 200
    assert len(response.json()["saves"]) == 1

    empty = client.get("/saves")
    assert empty.json()["saves"] == []
