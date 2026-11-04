from sqlalchemy import JSON, Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DB_PATH

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    next_level_xp = Column(Integer, default=100)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)

    strength = Column(Integer, default=5)
    agility = Column(Integer, default=5)
    vitality = Column(Integer, default=5)
    intelligence = Column(Integer, default=5)
    perception = Column(Integer, default=5)
    luck = Column(Integer, default=5)

    stat_points = Column(Integer, default=0)
    ability_points = Column(Integer, default=0)

    inventory = Column(JSON, default=list)
    abilities = Column(JSON, default=list)
    equipment = Column(JSON, default=dict)
    quests = Column(JSON, default=list)
    history = Column(JSON, default=list)
    location = Column(String, default="Неизвестно")

    # Описания предметов, полученные от Мастера Игры: {"Название": "описание"}.
    item_notes = Column(JSON, default=dict)

    enemy = Column(JSON, default=dict)
    book_file = Column(String, default="")

    user_token = Column(String, index=True, default="")

    # Жанровая кампания
    genre = Column(String, default="")
    genre_secondary = Column(String, default="")
    genre_weights = Column(JSON, default=dict)

    # Звание, фракция и репутация — заполняются по сюжету (теги REPUTATION/TITLE/FACTION)
    reputation = Column(Integer, default=0)
    title = Column(String, default="")
    faction = Column(String, default="")

    # События, отношения и способности
    relationships = Column(JSON, default=dict)
    xp_ledger = Column(JSON, default=dict)
    ability_cooldowns = Column(JSON, default=dict)
    ability_ranks = Column(JSON, default=dict)
    custom_abilities = Column(JSON, default=dict)
    statuses = Column(JSON, default=dict)
    turn = Column(Integer, default=0)


class GameSave(Base):
    __tablename__ = "game_saves"
    id = Column(Integer, primary_key=True, index=True)
    user_token = Column(String, index=True, default="")
    source_player_id = Column(Integer, default=0)
    name = Column(String, default="")
    level = Column(Integer, default=1)
    book_file = Column(String, default="")
    genre = Column(String, default="")
    genre_secondary = Column(String, default="")
    created_at = Column(String, default="")
    snapshot = Column(JSON, default=dict)


Base.metadata.create_all(bind=engine)


def _ensure_columns() -> None:
    """Достраивает колонки, появившиеся уже после первого создания базы.

    create_all создаёт только отсутствующие таблицы, но не добавляет поля в
    существующие. Для SQLite делаем простой ALTER: данных не теряем.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "players" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("players")}
    additions = {
        "item_notes": "JSON",
        "reputation": "INTEGER DEFAULT 0",
        "title": "VARCHAR DEFAULT ''",
        "faction": "VARCHAR DEFAULT ''",
    }

    with engine.begin() as connection:
        for name, ddl in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE players ADD COLUMN {name} {ddl}"))


_ensure_columns()
