"""Эмбеддинги для поиска по книге (RAG).

На десктопе векторы считает локальная Ollama (например, bge-m3). На Android
Ollama недоступна, поэтому эмбеддинги там отключаются (TEXTRPG_NO_EMBED=1),
а поиск по книге честно работает по словам.

Модуль намеренно не импортирует ollama на верхнем уровне: на телефоне этого
пакета просто нет, и обычный import уронил бы всё приложение.
"""

import os

# Явный выключатель: если он взведён, эмбеддинги не пробуем даже искать.
_DISABLED = os.getenv("TEXTRPG_NO_EMBED", "").strip().lower() in ("1", "true", "yes", "on")

# None — ещё не проверяли; True/False — доступность пакета ollama.
_available: bool | None = None


def available() -> bool:
    """Есть ли смысл считать эмбеддинги (установлена ли ollama)."""
    global _available
    if _DISABLED:
        return False
    if _available is None:
        try:
            import ollama  # noqa: F401
            _available = True
        except Exception:
            _available = False
    return _available


def embed(text: str):
    """Вектор текста или None, если эмбеддинги недоступны.

    Если Ollama доступна, но запрос упал — исключение пробрасывается наружу,
    чтобы вызывающий код мог решить, что делать (на десктопе это ошибка).
    """
    if not available():
        return None

    import ollama  # ленивый импорт: нужен только когда эмбеддинги реально доступны

    from app.config import EMBED_MODEL

    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]
