"""Сохранение игровых сессий.

Сессия — это снимок состояния игрока на момент смены книги.
Позже из этих записей можно сделать экран «Сохранения».
"""

from datetime import datetime, timezone

from app import database

PLAYER_COLUMNS = [column.name for column in database.Player.__table__.columns]


def snapshot_player(player) -> dict:
    """Полный снимок полей игрока."""
    snapshot = {}
    for name in PLAYER_COLUMNS:
        value = getattr(player, name, None)
        snapshot[name] = value
    return snapshot


def create_save(db, player, user_token: str = ""):
    """Сохраняет текущую сессию игрока. Возвращает запись GameSave."""
    save = database.GameSave(
        user_token=user_token or getattr(player, "user_token", "") or "",
        source_player_id=player.id,
        name=player.name or "",
        level=player.level or 1,
        book_file=player.book_file or "",
        genre=player.genre or "",
        genre_secondary=player.genre_secondary or "",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        snapshot=snapshot_player(player),
    )
    db.add(save)
    db.commit()
    db.refresh(save)
    return save


def list_saves(db, user_token: str) -> list:
    if not user_token:
        return []
    return (
        db.query(database.GameSave)
        .filter(database.GameSave.user_token == user_token)
        .order_by(database.GameSave.id.desc())
        .all()
    )


def save_summary(save) -> dict:
    return {
        "id": save.id,
        "name": save.name,
        "level": save.level,
        "book_file": save.book_file,
        "genre": save.genre,
        "genre_secondary": save.genre_secondary,
        "created_at": save.created_at,
    }
