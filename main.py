from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import INDEX_FILE, STATIC_DIR
from app.routers import abilities, books, combat, game, player, saves

app = FastAPI(title="Text RPG Server")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(player.router)
app.include_router(books.router)
app.include_router(game.router)
app.include_router(combat.router)
app.include_router(abilities.router)
app.include_router(saves.router)


@app.get("/")
def read_root():
    return FileResponse(INDEX_FILE)
