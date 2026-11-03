import ollama
import json
import os

# Разбиваем текст на куски
def split_text(text, chunk_size=1000, overlap=200):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

print("Читаем книгу...")
if not os.path.exists("book.txt"):
    print("Ошибка: файл book.txt не найден в папке C:\\TextRPG!")
    exit()

with open("book.txt", "r", encoding="utf-8") as f:
    book_text = f.read()

chunks = split_text(book_text)
print(f"Книга разбита на {len(chunks)} кусков. Начинаем создавать эмбеддинги (это займет время)...")

data = []
for i, chunk in enumerate(chunks):
    # Просим Ollama превратить текст в вектор (числа)
    response = ollama.embeddings(model='nomic-embed-text', prompt=chunk)
    data.append({
        "text": chunk,
        "embedding": response["embedding"]
    })
    if (i + 1) % 10 == 0:
        print(f"Обработано {i + 1} из {len(chunks)} кусков...")

# Сохраняем результат в файл
with open("book_index.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

print("Готово! Создан файл book_index.json.")