import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import database
from app.content import genres
from app.dependencies import get_db
from app.schemas import AbilityLearn, UseAbility
from app.services import abilities, gamelog, llm

router = APIRouter(prefix="/abilities", tags=["abilities"])

# Механику внебоевой способности сервер уже применил сам. Числовые HP/XP в
# ответе ИИ вырезаем, иначе лечение или урон могли бы посчитаться дважды.
# ENEMY_HP/ENEMY_DEAD не трогаем: появление врага — законное изменение мира.
_NUMERIC_EFFECT_RE = re.compile(
    r'(?<![A-Za-z_])(?:HP|XP)\s*:\s*[+-]?\d+\s*,?', re.IGNORECASE
)


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

    # Отыгрыш способности вне боя: ИИ получает её описание, жанр и контекст сцены
    # и обыгрывает действие строго по описанию. Механику сервер уже применил
    # (``notes``), поэтому ИИ её только описывает и не считает числа сам.
    profile = genres.profile_for(
        db_player.genre or genres.DEFAULT_GENRE,
        db_player.genre_secondary or None,
    )
    history = list(db_player.history or [])
    recent_history = "\n".join(history[-6:]) if history else "Начало пути."
    outcome = "; ".join(notes) if notes else "внешних изменений нет"
    target_line = f"\nЦель способности: {payload.target}." if payload.target else ""

    prompt = f"""Ты — талантливый писатель и Мастер Игры.
Игрок {db_player.name} применяет способность «{ability['name']}» вне боя.
ОПИСАНИЕ СПОСОБНОСТИ (обыграй строго по нему): {ability['description']}

ЖАНР КАМПАНИИ: {profile['display_name']}
ТОН ПОВЕСТВОВАНИЯ: {profile['tone']}
ЧТО СЧИТАЕТСЯ ПРОГРЕССОМ: {profile['progress_hint']}

СОСТОЯНИЕ ИГРОКА:
HP: {db_player.hp}/{db_player.max_hp}, Локация: {db_player.location}
Инвентарь: {db_player.inventory}
Отношения: {db_player.relationships}{target_line}
МЕХАНИЧЕСКИЙ РЕЗУЛЬТАТ (уже применён сервером, не пересчитывай): {outcome}

ПОСЛЕДНИЕ СОБЫТИЯ:
{recent_history}

ПРАВИЛА:
1. Опиши применение способности от ВТОРОГО лица: как герой её применяет и что происходит. Строго по описанию способности и в тоне жанра, 2-3 абзаца, без чисел.
2. Механику способности сервер уже учёл: НЕ добавляй теги HP, XP и ENEMY_HP — просто опиши результат словами.
3. Если по итогу сцены в мире что-то меняется, допиши новой строкой блок [EFFECTS]: ITEM: Название, REMOVE_ITEM: Название, LOCATION: Название, REPUTATION: +5, TITLE: Название, FACTION: Название. Если изменений нет — [EFFECTS] NONE.
4. Если применение способности стало значимым событием, добавь ровно ОДИН тег события с новой строки:
   [EVENT] type=discovery|social|relationship|growth|obstacle|risk|quest|milestone, result=success|partial|fail, tier=minor|standard|major, target="объект"
   Обычное действие НЕ размечай.
5. Пиши только на русском. Не описывай механику игры (очки, ранги, перезарядки).
"""
    try:
        raw_text = llm.call_llm(prompt, max_tokens=320)
        raw_text = _NUMERIC_EFFECT_RE.sub("", raw_text)
        full_text, effects_list = llm.parse_effects(raw_text, db_player)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    effects_list = notes + effects_list

    # Результат становится частью истории: следующий ход его помнит, а окно
    # рассказа его показывает (loadPlayer рисует последние записи истории).
    action_line = f"применяет способность «{ability['name']}»"
    if payload.target:
        action_line += f" → {payload.target}"
    history.append(f"Игрок: {action_line}")
    if full_text.strip():
        history.append(f"Мастер: {full_text}")
    db_player.history = history[-15:]
    db.commit()

    gamelog.log_turn(
        db_player,
        "ability_use",
        action=f"способность «{ability['name']}»"
        + (f" → {payload.target}" if payload.target else ""),
        raw=raw_text,
        text=full_text,
        effects=effects_list,
    )

    return {"story": full_text, "effects": effects_list, "ability_points": db_player.ability_points}
