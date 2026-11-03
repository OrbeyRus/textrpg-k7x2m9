# Text RPG

Текстовая RPG по загруженной книге: сюжет и бой ведёт LLM, прогрессия и правила считаются на сервере.

## Запуск

```powershell
cd C:\TextRPG
uvicorn main:app --port 8001 --reload
```

Или двойным кликом по `Start Server.cmd`. Игра: http://127.0.0.1:8001

## Структура

```
main.py                  точка входа FastAPI
index.html               интерфейс
app/
  config.py              пути и настройки из .env
  database.py            подключение к SQLite и модели
  dependencies.py        зависимость get_db
  schemas.py             Pydantic-схемы запросов
  routers/               HTTP-эндпоинты
  services/              бизнес-логика
    llm/                 клиент LLM и разбор игровых тегов
    progression.py       уровни, опыт, характеристики
    rag.py               загрузка книги и поиск по тексту
  content/               жанры и каталог способностей (данные)
static/
  css/                   base, layout, components
  js/                    клиентская логика
  icons/                 иконки экипировки
data/                    runtime-данные (в git не попадают)
  rpg.db                 база игроков
  books/                 обработанные книги
  source/                исходные .txt
scripts/                 служебные скрипты
tests/                   pytest
```

## Настройки

Ключ proxyapi хранится в `.env` (файл в git не попадает):

```
PROXYAPI_KEY=ваш_ключ
```

Образец — `.env.example`.

## Тесты

```powershell
python -m pytest -q
```

## Данные

- `data/rpg.db` — база игроков;
- `data/books/book_<id>.json` — книга, разбитая на фрагменты с эмбеддингами;
- `data/source/` — исходные тексты;
- `data/debug.log` — последние ответы LLM.
