from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routers import player, game, combat

app = FastAPI(title="Text RPG Server")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(player.router)
app.include_router(game.router)
app.include_router(combat.router)

@app.get("/")
def read_root(): return FileResponse("index.html")