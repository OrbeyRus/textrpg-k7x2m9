"""Служебный скрипт: строит эмбеддинги для локальной книги.

Запускается вручную, приложение его не импортирует.
    python scripts/build_book_index.py
"""

import json
from pathlib import Path

import ollama

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = BASE_DIR / "data" / "source" / "book.txt"
INDEX_PATH = BASE_DIR / "data" / "book_index.json"


def split_text(text, chunk_size=1000, overlap=200):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks


print("Читаем книгу...")
if not SOURCE_PATH.exists():
    raise SystemExit(f"Ошибка: файл {SOURCE_PATH} не найден!")

with open(SOURCE_PATH, "r", encoding="utf-8") as f:
    book_text = f.read()

chunks = split_text(book_text)
print(f"Книга разбита на {len(chunks)} кусков. Начинаем создавать эмбеддинги (это займет время)...")

data = []
for i, chunk in enumerate(chunks):
    response = ollama.embeddings(model="nomic-embed-text", prompt=chunk)
    data.append({"text": chunk, "embedding": response["embedding"]})
    if (i + 1) % 10 == 0:
        print(f"Обработано {i + 1} из {len(chunks)} кусков...")

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Готово! Создан файл {INDEX_PATH}.")
