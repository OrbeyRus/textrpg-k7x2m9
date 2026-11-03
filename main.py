from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import INDEX_FILE, STATIC_DIR
from app.routers import abilities, books, combat, game, player, saves, settings, update

app = FastAPI(title="Text RPG Server")

# Главную страницу не кэшируем: она ссылается на версии CSS/JS, и после
# обновления приложения браузер/WebView не должен показывать старую вёрстку.
# Заголовок ставим прямо на ответ: BaseHTTPMiddleware (app.middleware) местами
# ломает большие multipart-загрузки, а он тут ни к чему.
_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(player.router)
app.include_router(books.router)
app.include_router(game.router)
app.include_router(combat.router)
app.include_router(abilities.router)
app.include_router(saves.router)
app.include_router(settings.router)
app.include_router(update.router)


@app.get("/")
def read_root():
    return FileResponse(INDEX_FILE, headers=_NO_CACHE)
