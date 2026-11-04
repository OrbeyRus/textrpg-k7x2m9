import json
import math
import os
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

# numpy нужен только для быстрого косинуса, когда доступны эмбеддинги (десктоп).
# На Android numpy не нужен: эмбеддингов там нет, а без него обходимся обычной
# математикой — так сборка APK не тянет ни одного нативного пакета.
try:
    import numpy as np
except Exception:  # pragma: no cover - зависит от окружения
    np = None

from app import database
from app.config import BOOKS_DIR, DEBUG
from app.services import embeddings

# Сколько кусков книги отправлять в Ollama одновременно. На десктопе это
# заметно ускоряет обработку большой книги (раньше куски шли строго по одному).
EMBED_WORKERS = max(1, int(os.getenv("EMBED_WORKERS", "6")))

# Прогресс обработки книги по каждому игроку. Телефон опрашивает его, чтобы
# показать «идёт обработка, N%» вместо бесконечного ожидания.
_PROGRESS: dict = {}
_PROGRESS_LOCK = threading.Lock()


def _set_progress(player_id: int, **fields) -> None:
    with _PROGRESS_LOCK:
        state = _PROGRESS.setdefault(player_id, {})
        state.update(fields)


def get_progress(player_id: int):
    """Снимок прогресса обработки книги или None, если обработки не было."""
    with _PROGRESS_LOCK:
        state = _PROGRESS.get(player_id)
        return dict(state) if state else None


def _build_book_data(text: str, player_id: int, use_embeddings: bool) -> list:
    """Нарезает книгу на куски и (опционально) считает эмбеддинги.

    Функция синхронная и рассчитана на запуск в отдельном потоке: на телефоне
    она не должна занимать event loop сервера.
    """
    chunks = [c for c in split_text(text) if c.strip()]
    total = len(chunks)
    _set_progress(player_id, stage="chunks", done=0, total=total, percent=5, error=None)

    if not use_embeddings:
        data = [{"text": c} for c in chunks]
        _set_progress(player_id, stage="saving", done=total, total=total, percent=90)
        return data

    data = [None] * total
    counter = {"done": 0}
    counter_lock = threading.Lock()

    def embed_one(index: int) -> None:
        item = {"text": chunks[index]}
        try:
            item["embedding"] = embeddings.embed(chunks[index])
        except Exception as e:  # ошибку Ollama покажем наверху
            raise RuntimeError(f"Ошибка Ollama: {e}")
        data[index] = item
        with counter_lock:
            counter["done"] += 1
            done = counter["done"]
        percent = 5 + int(85 * done / total) if total else 90
        _set_progress(player_id, stage="embedding", done=done, total=total, percent=percent)

    if total:
        with ThreadPoolExecutor(max_workers=min(EMBED_WORKERS, total)) as pool:
            list(pool.map(embed_one, range(total)))

    _set_progress(player_id, stage="saving", done=total, total=total, percent=90)
    return data


def split_text(text, chunk_size=1000, overlap=200):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

def get_player_book(player_id: int, db):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player or not db_player.book_file:
        return []

    book_path = BOOKS_DIR / Path(db_player.book_file).name
    if not book_path.exists():
        return []

    with open(book_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Слова, которые не несут смысла для поиска по книге.
_WORDS_RE = re.compile(r"[а-яёa-z0-9]{3,}")
_STOPWORDS = {
    "это", "как", "что", "его", "ее", "её", "для", "или", "они", "был", "была",
    "было", "быть", "есть", "уже", "если", "так", "все", "всё", "при", "над",
    "под", "про", "без", "через", "когда", "где", "кто", "чем", "эти", "этот",
    "эта", "того", "себя", "меня", "тебя", "нам", "вам", "них", "него", "нее",
    "неё", "мой", "моя", "мне", "еще", "ещё", "только", "очень", "себе", "там",
    "тут", "здесь", "потом", "потому", "чтобы", "которые", "который", "которая",
    "свой", "свои", "один", "одна", "одно", "эту", "этим", "ею", "ими",
}

# Грубые русские окончания для сведения словоформ к общей основе.
# Нужны, чтобы «Яна», «Яне», «Янке» считались одним словом при лексическом поиске.
_ENDINGS = tuple(sorted({
    "иями", "ями", "ами", "ией", "иях", "ях", "ов", "ев", "ий", "ый", "ой",
    "ем", "ом", "ам", "ям", "ах", "ию", "ью", "ия", "ья", "ые", "ая", "ое",
    "ому", "ему", "ешь", "ете", "ишь", "ите", "ют", "ут", "ат", "ят", "ла",
    "ло", "ли", "ть", "ся", "сь", "а", "я", "у", "ю", "о", "е", "ы", "и", "й", "ь",
}, key=len, reverse=True))


def _stem(word: str) -> str:
    for ending in _ENDINGS:
        if len(word) - len(ending) >= 4 and word.endswith(ending):
            return word[: -len(ending)]
    return word


def _tokens(text: str) -> set:
    return {
        _stem(w)
        for w in _WORDS_RE.findall((text or "").lower())
        if w not in _STOPWORDS
    }


def _token_counts(text: str) -> Counter:
    """Частоты основ слов в тексте — нужны для BM25."""
    return Counter(
        _stem(w)
        for w in _WORDS_RE.findall((text or "").lower())
        if w not in _STOPWORDS
    )


def _bm25_scores(query_tokens: set, book_data: list, k1: float = 1.2, b: float = 0.75) -> list:
    """Лексические оценки кусков книги (BM25), нормированные в диапазон ~0..1.

    Работает без всяких моделей — это основной поиск на устройстве, где
    эмбеддинги недоступны.
    """
    n = len(book_data)
    if n == 0:
        return []

    counts = [_token_counts(item.get("text", "")) for item in book_data]
    if not query_tokens:
        return [0.0] * n

    df = Counter()
    for chunk in counts:
        for term in chunk:
            if term in query_tokens:
                df[term] += 1

    avgdl = sum(sum(chunk.values()) for chunk in counts) / n or 1.0
    idf = {
        term: math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
        for term in query_tokens
    }
    max_possible = sum(idf.values()) or 1.0

    scores = []
    for chunk in counts:
        dl = sum(chunk.values()) or 1.0
        score = 0.0
        for term in query_tokens:
            freq = chunk.get(term, 0)
            if not freq:
                continue
            score += idf[term] * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avgdl))
        scores.append(score / max_possible)
    return scores


def _as_vector(values):
    """Список чисел → вектор (numpy, если он есть, иначе обычный список)."""
    if np is not None:
        return np.asarray(values, dtype=float)
    return [float(v) for v in values]


def _norm(vector) -> float:
    if np is not None:
        return float(np.linalg.norm(vector))
    return math.sqrt(sum(v * v for v in vector))


def _dot(a, b) -> float:
    if np is not None:
        return float(np.dot(a, b))
    return float(sum(x * y for x, y in zip(a, b)))


def get_relevant_context(book_data, query, top_k=1, max_chars=2500):
    """Гибридный поиск по книге: смысловое сходство + совпадение слов.

    Если эмбеддинги доступны (Ollama на десктопе) — комбинируем оба сигнала.
    Если нет (Android) — ищем по словам (BM25). Возвращает несколько наиболее
    подходящих кусков без дублей, с ограничением по длине.
    """
    if not book_data:
        return "Информация о мире недоступна."

    q_tokens = _tokens(query)

    query_emb = None
    q_norm = 1.0
    if embeddings.available():
        try:
            vector = embeddings.embed(query)
            if vector is not None:
                query_emb = _as_vector(vector)
                q_norm = _norm(query_emb) or 1.0
        except Exception as e:
            if DEBUG:
                print(f"ЭМБЕДДИНГ НЕДОСТУПЕН, ИЩУ ПО СЛОВАМ: {e}")
            query_emb = None

    lexical_scores = _bm25_scores(q_tokens, book_data)

    scored = []
    for index, item in enumerate(book_data):
        text = item.get("text", "")
        if not text:
            continue

        lexical = lexical_scores[index]
        score = lexical

        # Смысловое сходство учитываем только когда есть и вектор запроса,
        # и вектор куска. Иначе остаётся честный лексический поиск.
        if query_emb is not None and item.get("embedding"):
            emb = _as_vector(item["embedding"])
            denom = q_norm * (_norm(emb) or 1.0)
            similarity = (_dot(query_emb, emb) / denom) if denom else 0.0
            score = 0.72 * similarity + 0.28 * lexical

        scored.append((score, text))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    chosen, seen = [], set()
    for _, text in scored:
        key = text[:80]
        if key in seen:
            continue
        seen.add(key)
        chosen.append(text)
        if len(chosen) >= max(1, int(top_k)):
            break

    if not chosen:
        return "Информация о мире недоступна."
    return "\n\n".join(chosen)[:max_chars]

async def _store_book_text(text: str, player_id: int, db) -> dict:
    """Готовит книгу из уже прочитанного текста и сохраняет куски для поиска.

    Общий путь и для загруженного файла, и для встроенной книги: чтобы оба
    источника обрабатывались одинаково (нарезка, эмбеддинги, прогресс).
    """
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    book_filename = f"book_{player_id}.json"
    book_path = BOOKS_DIR / book_filename

    # На Android эмбеддинги отключены: книга сохраняется как набор кусков текста,
    # а поиск идёт по словам (BM25).
    use_embeddings = embeddings.available()

    _set_progress(player_id, stage="splitting", done=0, total=0, percent=5, error=None)
    try:
        # Нарезка и эмбеддинги — в отдельном потоке, чтобы не блокировать
        # event loop: иначе на телефоне встаёт и интерфейс, и опрос прогресса.
        new_book_data = await run_in_threadpool(_build_book_data, text, player_id, use_embeddings)

        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(new_book_data, f, ensure_ascii=False)

        db_player.book_file = book_filename
        db.commit()
        _set_progress(
            player_id, stage="done", percent=100,
            done=len(new_book_data), total=len(new_book_data),
        )
        return {"status": "success", "chunks": len(new_book_data), "embeddings": use_embeddings}
    except HTTPException as e:
        _set_progress(player_id, stage="error", error=str(e.detail))
        raise
    except Exception as e:
        if DEBUG:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        _set_progress(player_id, stage="error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def process_book_text(text: str, player_id: int, db) -> dict:
    """Обрабатывает готовый текст (например, встроенную книгу из каталога)."""
    _set_progress(player_id, stage="reading", done=0, total=0, percent=2, error=None)
    return await _store_book_text(text, player_id, db)


async def process_book_upload(file: UploadFile, player_id: int, db):
    filename = file.filename or ""
    if not filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="Только .txt файлы")

    _set_progress(player_id, stage="reading", done=0, total=0, percent=2, error=None)
    content = await file.read()
    text = content.decode('utf-8', errors='ignore')
    return await _store_book_text(text, player_id, db)
