from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import saves

router = APIRouter(prefix="/saves", tags=["saves"])


@router.get("")
def list_saves(user_token: str = Query(""), db: Session = Depends(get_db)):
    """Сохранённые сессии пользователя (снимки на момент смены книги)."""
    if not user_token:
        return {"saves": []}
    return {"saves": [saves.save_summary(save) for save in saves.list_saves(db, user_token)]}
