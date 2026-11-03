"""Лёгкие миграции SQLite без Alembic.

Добавляет недостающие колонки в таблицу players. Запуск:
    python scripts/migrate.py

Скрипт идемпотентный: повторный запуск ничего не меняет.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "rpg.db"

# колонка -> SQL-описание для ALTER TABLE
NEW_COLUMNS = {
    "genre": "TEXT DEFAULT ''",
    "genre_secondary": "TEXT DEFAULT ''",
    "genre_weights": "TEXT DEFAULT '{}'",
    "relationships": "TEXT DEFAULT '{}'",
    "xp_ledger": "TEXT DEFAULT '{}'",
    "ability_cooldowns": "TEXT DEFAULT '{}'",
    "turn": "INTEGER DEFAULT 0",
    "user_token": "TEXT DEFAULT ''",
}


def existing_columns(cursor: sqlite3.Cursor) -> set:
    cursor.execute("PRAGMA table_info(players)")
    return {row[1] for row in cursor.fetchall()}


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"База не найдена: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    columns = existing_columns(cursor)
    added = []

    for name, definition in NEW_COLUMNS.items():
        if name in columns:
            continue
        cursor.execute(f"ALTER TABLE players ADD COLUMN {name} {definition}")
        added.append(name)

    connection.commit()
    connection.close()

    if added:
        print("Добавлены колонки:", ", ".join(added))
    else:
        print("Схема уже актуальна, изменений нет.")


if __name__ == "__main__":
    main()
