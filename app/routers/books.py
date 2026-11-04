from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import database
from app.content import genres, library
from app.dependencies import get_db
from app.schemas import LibraryOpen
from app.services import campaign, gamelog, rag

router = APIRouter(tags=["books"])


@router.get("/genres")
def list_genres():
    """Список жанров для выбора при загрузке книги."""
    return {"genres": genres.public_list()}


@router.get("/library")
def list_library():
    """Готовые книги, которые можно открыть без загрузки файла."""
    return {"books": library.public_list()}


@router.post("/library/{player_id}/open")
async def open_library_book(
    player_id: int,
    payload: LibraryOpen,
    db: Session = Depends(get_db),
):
    """Начинает кампанию по встроенной книге (текст берётся из приложения)."""
    book = library.get(payload.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    text = library.load_text(payload.book_id)
    if not text or not text.strip():
        raise HTTPException(status_code=500, detail="Текст книги недоступен")

    result = await rag.process_book_text(text, player_id, db)

    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    profile = campaign.start_new_campaign(db_player, book["genre"])
    db.commit()

    gamelog.log_note(
        db_player,
        "book",
        f"Открыта встроенная книга «{book['title']}» ({book['author']}), "
        f"жанр: {profile['display_name']}",
    )

    return {
        **result,
        "book": {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
        },
        "genre": {
            "code": profile["code"],
            "secondary": profile["secondary"],
            "display_name": profile["display_name"],
        },
    }


@router.get("/book_status")
def book_status(player_id: int, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player or not db_player.book_file:
        return {"has_book": False}
    return {"has_book": True}


@router.get("/upload_progress/{player_id}")
def upload_progress(player_id: int):
    """Прогресс обработки книги (опрашивается интерфейсом во время загрузки)."""
    state = rag.get_progress(player_id)
    if not state:
        return {"active": False}
    return {"active": state.get("stage") not in ("done", "error"), **state}


@router.post("/upload_book/{player_id}")
async def upload_book(
    player_id: int,
    file: UploadFile = File(...),
    genre: str = Form(genres.DEFAULT_GENRE),
    genre_secondary: str = Form(""),
    db: Session = Depends(get_db),
):
    if genre not in genres.GENRES:
        raise HTTPException(status_code=400, detail="Неизвестный жанр")
    if genre_secondary and genre_secondary not in genres.GENRES:
        raise HTTPException(status_code=400, detail="Неизвестный дополнительный жанр")

    result = await rag.process_book_upload(file, player_id, db)

    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    profile = campaign.start_new_campaign(db_player, genre, genre_secondary or None)
    db.commit()

    gamelog.log_note(
        db_player,
        "book",
        f"Загружена книга «{file.filename}», жанр: {profile['display_name']}",
    )

    return {
        **result,
        "genre": {
            "code": profile["code"],
            "secondary": profile["secondary"],
            "display_name": profile["display_name"],
        },
    }
