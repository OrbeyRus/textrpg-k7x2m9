from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import database
from app.dependencies import get_db
from app.schemas import AbilityLearn, UseAbility
from app.services import abilities, llm

router = APIRouter(prefix="/abilities", tags=["abilities"])


def _get_player(player_id: int, db: Session) -> database.Player:
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    return db_player


@router.get("/{player_id}")
def list_abilities(player_id: int, db: Session = Depends(get_db)):
    """Каталог способностей жанра и книжных способностей с их состоянием."""
    db_player = _get_player(player_id, db)
    return {
        "abilities": abilities.catalog_view(db_player),
        "ability_points": db_player.ability_points,
    }


@router.post("/{player_id}/learn")
def learn_ability(player_id: int, payload: AbilityLearn, db: Session = Depends(get_db)):
    db_player = _get_player(player_id, db)
    key = payload.ability_id or payload.ability_name or ""

    ok, message, view = abilities.learn(db_player, key)
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    db.commit()
    return {"status": "success", "message": message, "ability": view, "ability_points": db_player.ability_points}


@router.post("/{player_id}/use")
def use_ability(player_id: int, payload: UseAbility, db: Session = Depends(get_db)):
    db_player = _get_player(player_id, db)
    ability = abilities.resolve(db_player, payload.ability_id)
    if not ability:
        raise HTTPException(status_code=404, detail="Способность не найдена")
    if not abilities.is_learned(db_player, ability):
        raise HTTPException(status_code=400, detail="Способность не изучена")
    if not ability.get("field"):
        raise HTTPException(status_code=400, detail="Способность доступна только в бою")
    if not abilities.can_use(db_player, ability):
        raise HTTPException(status_code=400, detail="Способность ещё перезаряжается")

    abilities.tick(db_player)
    abilities.set_cooldown(db_player, ability)
    notes = abilities.apply_field_effect(db_player, ability, payload.target)

    prompt = f"""Ты — талантливый писатель и Мастер Игры.
Игрок {db_player.name} применяет способность «{ability['name']}» ({ability['description']}).
Место: {db_player.location}. Отношения: {db_player.relationships}.

Опиши результат в 1-2 абзаца от второго лица, живо и по жанру.
НЕ пиши в ответе числа и служебные теги, кроме одного тега события с новой строки, если это уместно:
[EVENT] type=growth|social|relationship|discovery, result=success, tier=minor|standard, target="объект"
"""
    try:
        full_text = llm.call_llm(prompt, max_tokens=220)
        full_text, effects_list = llm.parse_effects(full_text, db_player)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    effects_list = notes + effects_list
    db.commit()
    return {"story": full_text, "effects": effects_list, "ability_points": db_player.ability_points}
