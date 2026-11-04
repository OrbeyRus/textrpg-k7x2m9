from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app import database
from app.dependencies import get_db
from app.schemas import (
    AbilityLearn,
    EquipItem,
    NameUpdate,
    NewGameRequest,
    PlayerCreate,
    StatUpgrade,
)
from app.services import abilities, combat, gamelog, items, progression, saves

router = APIRouter(prefix="/player", tags=["player"])


def _fresh_player(user_token: str, name: str = "") -> database.Player:
    return database.Player(
        name=name,
        user_token=user_token or "",
        level=progression.START_LEVEL,
        next_level_xp=progression.xp_to_next(progression.START_LEVEL),
        stat_points=progression.START_STAT_POINTS,
        ability_points=progression.START_ABILITY_POINTS,
    )


@router.post("/")
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    db_player = _fresh_player(player.user_token, name=player.name)
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    gamelog.log_note(
        db_player,
        "create",
        f"Создан герой: {db_player.name}" if db_player.name else "Создан герой без имени",
    )
    return db_player

@router.get("/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404, detail="Нет персонажа")
    # Полное состояние игрока + описания предметов для интерфейса.
    data = {
        column.name: getattr(db_player, column.name)
        for column in database.Player.__table__.columns
    }
    data["item_descriptions"] = items.describe_all(db_player)
    # Подсказка, в какой слот логичнее надеть предмет (для кнопок в карточке).
    data["item_slots"] = items.slots_all(db_player)
    # Производные боевые значения: считает сервер, окно персонажа их показывает.
    data["derived"] = combat.derived_stats(db_player)
    return data

@router.post("/{player_id}/name")
def set_player_name(player_id: int, payload: NameUpdate, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404, detail="Нет персонажа")

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Имя не может быть пустым")

    db_player.name = name
    db.commit()
    gamelog.log_note(db_player, "name", f"Персонаж назван: {name}")
    return {"status": "success", "name": name}

@router.post("/{player_id}/new_game")
def start_new_game(player_id: int, payload: NewGameRequest = None, db: Session = Depends(get_db)):
    """Сохраняет текущую сессию и начинает новую игру с чистого героя."""
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404, detail="Нет персонажа")

    token = (payload.user_token if payload else "") or db_player.user_token or ""
    if token and not db_player.user_token:
        db_player.user_token = token

    # Снимок текущей сессии: сохраняем, но саму строку игрока не трогаем —
    # это и есть «сохранённая сессия» пользователя.
    saved = saves.create_save(db, db_player, user_token=token)
    gamelog.log_note(
        db_player,
        "new_game",
        f"Начата новая игра; сессия сохранена (save_id={saved.id})",
    )

    fresh = _fresh_player(token, name="")
    db.add(fresh)
    db.commit()
    db.refresh(fresh)

    return {
        "status": "success",
        "player_id": fresh.id,
        "saved_player_id": db_player.id,
        "save_id": saved.id,
    }

@router.post("/{player_id}/upgrade")
def upgrade_stat(player_id: int, upgrade: StatUpgrade, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)

    # защита от подмены: повышать можно только реальные характеристики
    if upgrade.stat_name not in progression.STAT_KEYS:
        raise HTTPException(status_code=400, detail="Неизвестная характеристика")

    cost = progression.POINT_COST
    if db_player.stat_points < cost:
        raise HTTPException(status_code=400, detail="Нет очков характеристик")

    old_value = getattr(db_player, upgrade.stat_name)
    setattr(db_player, upgrade.stat_name, old_value + 1)
    db_player.stat_points -= cost
    hp_gain = progression.apply_stat_increase(db_player, upgrade.stat_name, old_value)

    db.commit()
    return {
        "status": "success",
        "stat": upgrade.stat_name,
        "value": old_value + 1,
        "cost": cost,
        "stat_points": db_player.stat_points,
        "hp_gain": hp_gain,
        "max_hp": db_player.max_hp,
        "hp": db_player.hp,
    }

@router.post("/{player_id}/learn_ability")
def learn_ability(player_id: int, ability: AbilityLearn, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)

    key = ability.ability_id or ability.ability_name or ""
    ok, message, view = abilities.learn(db_player, key)
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    db.commit()
    return {
        "status": "success",
        "message": message,
        "ability": view,
        "ability_points": db_player.ability_points,
    }

@router.post("/{player_id}/equip")
def equip_item(player_id: int, item: EquipItem, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)
    current_inv = list(db_player.inventory) if db_player.inventory else []
    current_eq = dict(db_player.equipment) if db_player.equipment else {}
    if item.item_name in current_inv:
        current_inv.remove(item.item_name)
        db_player.inventory = current_inv
        if item.slot in current_eq:
            current_inv.append(current_eq[item.slot])
            db_player.inventory = current_inv
        current_eq[item.slot] = item.item_name
        db_player.equipment = current_eq
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Предмет не найден")

@router.post("/{player_id}/unequip")
def unequip_item(player_id: int, item: EquipItem, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)
    current_eq = dict(db_player.equipment) if db_player.equipment else {}
    current_inv = list(db_player.inventory) if db_player.inventory else []
    if item.slot in current_eq:
        current_inv.append(current_eq[item.slot])
        db_player.inventory = current_inv
        del current_eq[item.slot]
        db_player.equipment = current_eq
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Слот пуст")

@router.post("/{player_id}/drop")
def drop_item(player_id: int, item: AbilityLearn, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)
    current_inv = list(db_player.inventory) if db_player.inventory else []
    if item.ability_name in current_inv:
        current_inv.remove(item.ability_name)
        db_player.inventory = current_inv
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Предмет не найден")


def _log_disposition(player_id: int, name: str) -> str:
    """Заголовок Content-Disposition для файла журнала.

    Имя персонажа может быть на кириллице, а HTTP-заголовки допускают только
    latin-1. Поэтому имя файла по умолчанию делаем ASCII («log_player_N.txt»),
    а красивое человекочитаемое передаём по RFC 5987 (``filename*``) в
    процентном кодировании. Иначе ответ падал бы с 500.
    """
    fallback = f"log_player_{player_id}.txt"
    pretty = quote(f"log_{name}_{player_id}.txt")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{pretty}'


@router.get("/{player_id}/log")
def export_log(player_id: int, db: Session = Depends(get_db)):
    """Выгружает журнал игры одним текстовым файлом.

    Внутри — читаемая «история приключения» и технический журнал: это то, что
    нужно, чтобы разобрать проблему в игре.
    """
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Нет персонажа")

    directory = gamelog.player_dir(db_player)
    chunks = []

    story = directory / "story.md"
    if story.exists():
        chunks.append("== ИСТОРИЯ ПРИКЛЮЧЕНИЯ ==\n\n" + story.read_text(encoding="utf-8"))

    game = directory / "game.log"
    if game.exists():
        chunks.append("== ТЕХНИЧЕСКИЙ ЖУРНАЛ ==\n\n" + game.read_text(encoding="utf-8"))

    if not chunks:
        chunks.append("Журнал пуст: сыграйте хотя бы один ход и повторите.")

    name = gamelog.safe_name(getattr(db_player, "name", "")) or "player"
    headers = {"Content-Disposition": _log_disposition(player_id, name)}
    return PlainTextResponse("\n\n".join(chunks), headers=headers)