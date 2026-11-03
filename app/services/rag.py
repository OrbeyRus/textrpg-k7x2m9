import json
from pathlib import Path

import numpy as np
import ollama
from fastapi import HTTPException, UploadFile

from app import database
from app.config import BOOKS_DIR

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

def get_relevant_context(book_data, query, top_k=1):
    if not book_data: return "Информация о мире недоступна."
    try:
        query_emb = ollama.embeddings(model='nomic-embed-text', prompt=query)['embedding']
        query_emb = np.array(query_emb)
        scores = []
        for item in book_data:
            chunk_emb = np.array(item['embedding'])
            score = np.dot(query_emb, chunk_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(chunk_emb))
            scores.append((score, item['text']))
        scores.sort(key=lambda x: x[0], reverse=True)
        return "\n\n".join([text for score, text in scores[:top_k]])
    except Exception as e:
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
            print(f"Обработка куска {i+1} из {len(chunks)}...")
            try:
                emb = ollama.embeddings(model='nomic-embed-text', prompt=chunk)['embedding']
                new_book_data.append({"text": chunk, "embedding": emb})
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ошибка Ollama: {e}")
        
        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(new_book_data, f, ensure_ascii=False)
        
        db_player.book_file = book_filename
        db.commit()
        return {"status": "success", "chunks": len(new_book_data)}
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise HTTPException(status_code=500, detail=str(e))