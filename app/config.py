"""Пути проекта и настройки окружения.

Все остальные модули берут пути отсюда, чтобы не зависеть от текущей
рабочей директории и не дублировать строки вида "data/...".
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"
SOURCE_DIR = DATA_DIR / "source"
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "index.html"

DB_PATH = DATA_DIR / "rpg.db"
DEBUG_LOG = DATA_DIR / "debug.log"


def _load_env_file() -> None:
    """Читает .env без внешних зависимостей, не перетирая уже заданные переменные."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

PROXYAPI_KEY = os.getenv("PROXYAPI_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-v3.2")

# Модель эмбеддингов для поиска по книге (через локальный Ollama).
# nomic-embed-text слабо различает русский текст — при желании замените на
# мультиязычную модель (например, bge-m3) и переиндексируйте книги:
#   ollama pull bge-m3
#   set EMBED_MODEL=bge-m3   (или в .env)
#   python scripts/reindex_books.py
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Отладочные логи (RAG, разбор тегов и т.п.) в консоль сервера.
DEBUG = os.getenv("DEBUG", "").strip().lower() in ("1", "true", "yes", "on")

# Каталоги нужны ещё до подключения к базе.
DATA_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR.mkdir(parents=True, exist_ok=True)
