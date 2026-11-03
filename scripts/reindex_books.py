"""Переиндексация книг под текущую модель эмбеддингов.

Нужна после смены EMBED_MODEL: старые векторы несовместимы с новой моделью.
Текст кусков уже хранится в data/books/*.json, поэтому исходный .txt не нужен.

Запуск:
    python scripts/reindex_books.py
"""

import json
import sys
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BOOKS_DIR, EMBED_MODEL  # noqa: E402


def reindex_book(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    for i, item in enumerate(data, start=1):
        text = item.get("text", "")
        if not text:
            continue
        item["embedding"] = ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]
        print(f"  {path.name}: кусок {i}/{len(data)}", end="\r")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"  {path.name}: {len(data)} кусков переиндексировано           ")
    return len(data)


def main() -> None:
    books = sorted(BOOKS_DIR.glob("*.json"))
    if not books:
        raise SystemExit(f"Нет книг в {BOOKS_DIR}")

    print(f"Модель эмбеддингов: {EMBED_MODEL}")
    total = 0
    for path in books:
        total += reindex_book(path)
    print(f"Готово. Обработано книг: {len(books)}, кусков: {total}.")


if __name__ == "__main__":
    main()
