from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import database
from app.content import genres
from app.dependencies import get_db
from app.services import abilities, llm, progression

router = APIRouter(prefix="/combat", tags=["combat"])

@router.post("/{player_id}/action")
def combat_action(player_id: int, action: str = Query(...), db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player or not db_player.enemy:
        raise HTTPException(status_code=400, detail="Нет активного боя")

    abilities.tick(db_player)

    enemy_name = db_player.enemy.get("name", "Враг")
    enemy_hp_before = db_player.enemy.get("hp", 0)
    
    weapon = db_player.equipment.get("weapon", "кулаки") if db_player.equipment else "кулаки"
    profile = genres.profile_for(
        db_player.genre or genres.DEFAULT_GENRE,
        db_player.genre_secondary or None,
    )
    
    prompt = f"""Ты — боевой движок текстовой JRPG. 
Жанр и тон: {profile['display_name']}. {profile['tone']}.
Бои в этом жанре: {profile['combat_hint']}.
Игрок {db_player.name} (HP: {db_player.hp}, Оружие: {weapon}) сражается с {enemy_name} (HP: {enemy_hp_before}).
Игрок использует действие: {action}.

Опиши ОДНО короткое предложение (максимум 2) с атакой игрока. 
Затем опиши ОДНО короткое предложение с ответной атакой врага (если он жив).

В САМОМ КОНЦЕ ответа ты ОБЯЗАН добавить теги эффектов!
Формат строго такой (каждый тег с новой строки!):
[EFFECTS] ENEMY_HP: -15, HP: -10
Если враг мертв, добавь с новой строки: ENEMY_DEAD, ITEM: Выпавший предмет
И ОБЯЗАТЕЛЬНО один тег события с новой строки:
[EVENT] type=combat_win, result=success, tier=standard, target="имя врага" — если враг побеждён
[EVENT] type=obstacle, result=success|partial|fail, tier=minor|standard|major, target="имя врага" — если бой продолжается
Числа опыта не пиши: опыт начисляет сервер.

ВНИМАНИЕ: НЕ МЕНЯЙ ЛОКАЦИЮ во время боя (не пиши LOCATION). Бой происходит там, где игрок уже находится.
"""

    try:
        full_text = llm.call_llm(prompt, max_tokens=300)
        full_text, effects_list = llm.parse_effects(full_text, db_player)
        
        # --- ЗАЩИТА ОТ ДУРАКА (Авто-урон) ---
        current_enemy_hp = db_player.enemy.get("hp", 0) if db_player.enemy else 0
        
        if db_player.enemy and current_enemy_hp == enemy_hp_before:
            has_weapon = any(w in weapon.lower() for w in ["нож", "меч", "топор", "кинжал", "пистолет"])
            damage = progression.attack_power(db_player.strength) + (7 if has_weapon else 0)
            new_enemy = dict(db_player.enemy)
            new_enemy["hp"] = max(0, enemy_hp_before - damage)
            db_player.enemy = new_enemy
            effects_list.append(f"⚔️ Урон врагу: {damage} HP")
            
            if new_enemy["hp"] <= 0:
                effects_list.append(f"💀 Враг {enemy_name} повержен!")
                db_player.enemy = {}
        
        # ВАЖНО: Сохраняем события боя в общую историю игрока!
        history = list(db_player.history) if db_player.history else []
        history.append(f"Бой: {full_text}")
        db_player.history = history[-15:]

        # Сохраняем изменения в базу
        db.commit()
        
        return {
            "text": full_text, 
            "effects": effects_list,
            "enemy": db_player.enemy,
            "player_hp": db_player.hp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{player_id}/ability")
def combat_ability(player_id: int, ability_id: str = Query(...), db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player or not db_player.enemy:
        raise HTTPException(status_code=400, detail="Нет активного боя")

    ability = abilities.resolve(db_player, ability_id)
    if not ability:
        raise HTTPException(status_code=404, detail="Способность не найдена")
    if not abilities.is_learned(db_player, ability):
        raise HTTPException(status_code=400, detail="Способность не изучена")
    if not ability.get("combat"):
        raise HTTPException(status_code=400, detail="Способность недоступна в бою")
    if not abilities.can_use(db_player, ability):
        raise HTTPException(status_code=400, detail="Способность ещё перезаряжается")

    enemy_name = db_player.enemy.get("name", "Враг")
    abilities.tick(db_player)
    abilities.set_cooldown(db_player, ability)
    notes, killed = abilities.apply_combat_effect(db_player, ability)

    prompt = f"""Ты — боевой движок текстовой JRPG.
Игрок {db_player.name} (HP: {db_player.hp}) применяет способность «{ability['name']}» против {enemy_name}.
Способность: {ability['description']}.

Опиши ОДНО-ДВА коротких предложения с эффектом способности{"" if killed else " и ОДНО предложение с ответной атакой врага"}.
НЕ пиши тег [EFFECTS] с числами: сервер уже применил эффект.
При желании добавь с новой строки тег события, если бой завершён:
[EVENT] type=combat_win, result=success, tier=standard, target="{enemy_name}"
"""
    try:
        full_text = llm.call_llm(prompt, max_tokens=220)
        full_text, effects_list = llm.parse_effects(full_text, db_player)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))

    effects_list = notes + effects_list

    history = list(db_player.history) if db_player.history else []
    history.append(f"Бой: {full_text}")
    db_player.history = history[-15:]
    db.commit()

    return {
        "text": full_text,
        "effects": effects_list,
        "enemy": db_player.enemy,
        "player_hp": db_player.hp,
    }