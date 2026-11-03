import json
import math
import re
from collections import Counter
from pathlib import Path

from fastapi import HTTPException, UploadFile

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

async def process_book_upload(file: UploadFile, player_id: int, db):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404, detail="Игрок не найден")

    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Только .txt файлы")

    book_filename = f"book_{player_id}.json"
    book_path = BOOKS_DIR / book_filename

    # На Android эмбеддинги отключены: книга сохраняется как набор кусков текста,
    # а поиск идёт по словам (BM25).
    use_embeddings = embeddings.available()

    try:
        content = await file.read()
        text = content.decode('utf-8', errors='ignore')
        chunks = split_text(text)

        new_book_data = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            if DEBUG:
                print(f"Обработка куска {i+1} из {len(chunks)}...")
            item = {"text": chunk}
            if use_embeddings:
                try:
                    item["embedding"] = embeddings.embed(chunk)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Ошибка Ollama: {e}")
            new_book_data.append(item)

        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(new_book_data, f, ensure_ascii=False)

        db_player.book_file = book_filename
        db.commit()
        return {"status": "success", "chunks": len(new_book_data), "embeddings": use_embeddings}
    except HTTPException:
        raise
    except Exception as e:
        if DEBUG:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise HTTPException(status_code=500, detail=str(e))
