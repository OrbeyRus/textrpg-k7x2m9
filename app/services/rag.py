import json
import re
from pathlib import Path

import numpy as np
import ollama
from fastapi import HTTPException, UploadFile

from app import database
from app.config import BOOKS_DIR, DEBUG, EMBED_MODEL

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


def get_relevant_context(book_data, query, top_k=1, max_chars=2500):
    """Гибридный поиск по книге: смысловое сходство + совпадение слов.

    Возвращает несколько наиболее подходящих кусков (top_k), без дублей,
    с ограничением по длине.
    """
    if not book_data:
        return "Информация о мире недоступна."
    try:
        query_emb = np.array(
            ollama.embeddings(model=EMBED_MODEL, prompt=query)['embedding']
        )
        q_norm = float(np.linalg.norm(query_emb)) or 1.0
        q_tokens = _tokens(query)

        scored = []
        for item in book_data:
            emb = np.array(item['embedding'])
            denom = q_norm * (float(np.linalg.norm(emb)) or 1.0)
            similarity = float(np.dot(query_emb, emb) / denom) if denom else 0.0

            chunk_tokens = _tokens(item.get('text', ''))
            lexical = (
                len(q_tokens & chunk_tokens) / (len(q_tokens) + 1) if q_tokens else 0.0
            )
            scored.append((0.72 * similarity + 0.28 * lexical, item.get('text', '')))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        chosen, seen = [], set()
        for _, text in scored:
            if not text:
                continue
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
    except Exception as e:
        if DEBUG:
            print(f"ОШИБКА ПОИСКА: {e}")
        return "Ошибка поиска."

async def process_book_upload(file: UploadFile, player_id: int, db):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404, detail="Игрок не найден")

    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Только .txt файлы")
    
    book_filename = f"book_{player_id}.json"
    book_path = BOOKS_DIR / book_filename
    
    try:
        content = await file.read()
        text = content.decode('utf-8', errors='ignore')
        chunks = split_text(text)
        
        new_book_data = []
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            if DEBUG:
                print(f"Обработка куска {i+1} из {len(chunks)}...")
            try:
                emb = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)['embedding']
                new_book_data.append({"text": chunk, "embedding": emb})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка Ollama: {e}")
        
        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(new_book_data, f, ensure_ascii=False)
        
        db_player.book_file = book_filename
        db.commit()
        return {"status": "success", "chunks": len(new_book_data)}
    except Exception as e:
        if DEBUG:
            print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise HTTPException(status_code=500, detail=str(e))