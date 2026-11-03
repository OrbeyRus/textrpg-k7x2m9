import json
import re

from app.services import abilities, progression, xp

EVENT_RE = re.compile(r'\[EVENT\]\s*([^\n]*)', re.IGNORECASE)


def _parse_event_line(line: str) -> dict:
    event = {}
    for part in re.split(r',\s*', line):
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        event[key.strip().lower()] = value.strip().strip('"').strip("'")
    return event


def _extract_events(full_text: str) -> tuple:
    """Вынимает теги [EVENT] из текста. Возвращает (события, очищенный текст)."""
    events = [_parse_event_line(line) for line in EVENT_RE.findall(full_text)]
    cleaned = EVENT_RE.sub('', full_text)
    return [e for e in events if e.get("type")], cleaned


def parse_effects(full_text, db_player, allow_xp=True):
    effects_list = []

    # События и сюжетные способности вынимаем до остальной обработки.
    events, full_text = _extract_events(full_text)
    unlocks, full_text = abilities.extract_unlocks(full_text)
    enemy_max_hp = 0
    if db_player.enemy:
        enemy_max_hp = int(db_player.enemy.get("max_hp") or db_player.enemy.get("hp") or 0)

    # 1. Появление врага
    enemy_match = re.search(r'\[ENEMY\]\s*(\{.*?\})', full_text, re.DOTALL | re.IGNORECASE)
    if enemy_match:
        try:
            enemy_json = json.loads(enemy_match.group(1))
            db_player.enemy = {
                "name": enemy_json.get("name", "Неизвестный"),
                "hp": enemy_json.get("hp", 10),
                "max_hp": enemy_json.get("hp", 10)
            }
            enemy_max_hp = int(db_player.enemy["max_hp"])
            effects_list.append(f"⚔️ Появился враг: {db_player.enemy['name']} ({db_player.enemy['hp']} HP)")
        except: 
            pass
        full_text = full_text.replace(enemy_match.group(0), '').strip()
    
    # 2. Обработка эффектов (урон врагу, смерть)
    effects_match = re.search(r'\[EFFECTS\](.*?)(?:\n|$)', full_text, re.IGNORECASE | re.DOTALL)
    if effects_match:
        effects_str = effects_match.group(1).strip()
        full_text = full_text.replace(effects_match.group(0), '').strip()
        
        if "NONE" not in effects_str.upper():
            # Урон врагу
            enemy_hp_match = re.search(r'ENEMY_HP:\s*([+-]?\d+)', effects_str)
            if enemy_hp_match and db_player.enemy:
                val = int(enemy_hp_match.group(1))

                # Прилив сил усиливает урон игрока.
                if val < 0:
                    rage = _active_status(db_player, "rage")
                    if rage:
                        bonus = int(rage["value"])
                        val -= bonus
                        effects_list.append(f"🔥 Прилив сил: +{bonus} к урону")

                # КОСТЫЛЬ ДЛЯ SQLALCHEMY: Пересоздаем словарь, чтобы база увидела изменения
                new_enemy = dict(db_player.enemy)
                new_enemy["hp"] = max(0, new_enemy.get("hp", 0) + val)
                db_player.enemy = new_enemy
                
                effects_list.append(f"⚔️ Урон врагу: {-val} HP")
                
                # Если враг умер
                if new_enemy["hp"] <= 0:
                    effects_list.append(f"💀 Враг {new_enemy['name']} повержен!")
                    db_player.enemy = {} # Очищаем врага
            
            # Принудительная очистка врага (если бой закончился)
            if "ENEMY_DEAD" in effects_str.upper():
                if db_player.enemy:
                    effects_list.append(f"💀 Враг {db_player.enemy['name']} повержен!")
                    db_player.enemy = {}

            # Урон игроку (HP:, но НЕ ENEMY_HP:)
            hp_match = re.search(r'(?<![A-Za-z_])HP:\s*([+-]?\d+)', effects_str)
            if hp_match: 
                val = int(hp_match.group(1))

                # Щит гасит часть входящего урона.
                if val < 0:
                    guard = _active_status(db_player, "guard")
                    if guard:
                        absorbed = min(int(guard["value"]), -val)
                        val += absorbed
                        effects_list.append(f"🛡️ Щит поглотил {absorbed} урона")

                db_player.hp = max(0, min(db_player.max_hp, db_player.hp + val))
                effects_list.append(f"❤️ HP: {'+' if val > 0 else ''}{val}")

            # Предметы
            item_match = re.search(r'ITEM:\s*([^\n,]+)', effects_str)
            remove_match = re.search(r'REMOVE_ITEM:\s*([^\n,]+)', effects_str)
            
            if item_match and remove_match and item_match.group(1).strip().lower() == remove_match.group(1).strip().lower():
                item_match = None

            if item_match:
                item_name = item_match.group(1).strip()
                inv = list(db_player.inventory) if db_player.inventory else []
                inv.append(item_name)
                db_player.inventory = inv
                effects_list.append(f"🎒 Получено: {item_name}")
                
            if remove_match:
                item_to_remove = remove_match.group(1).strip()
                if db_player.inventory and item_to_remove in db_player.inventory:
                    inv = list(db_player.inventory)
                    inv.remove(item_to_remove)
                    db_player.inventory = inv
                
                if db_player.equipment:
                    eq = dict(db_player.equipment)
                    for slot, item in list(eq.items()):
                        if item == item_to_remove: del eq[slot]; break
                    db_player.equipment = eq
                effects_list.append(f"🗑️ Выброшено: {item_to_remove}")

            # Локация
            loc_match = re.search(r'LOCATION:\s*([^\[\n,]+)', effects_str)
            if loc_match: 
                loc_name = loc_match.group(1).strip()
                db_player.location = loc_name
                effects_list.append(f"📍 Локация: {loc_name}")

            # Старый тег опыта: совместимость, но с потолком.
            if not events and allow_xp:
                xp_match = re.search(r'(?<![A-Za-z_])XP:\s*([+-]?\d+)', effects_str)
                if xp_match:
                    xp_gained = xp.clamp_legacy_xp(int(xp_match.group(1)))
                    if xp_gained > 0:
                        db_player.xp = max(0, db_player.xp + xp_gained)
                        effects_list.append(f"✨ Опыт: +{xp_gained}")
                        for new_level in progression.apply_level_up(db_player):
                            effects_list.append(
                                f"🆙 Уровень {new_level}! "
                                f"+{progression.stat_points_for_level(new_level)} очк. характеристик, "
                                f"+{progression.ability_points_for_level(new_level)} очк. способностей"
                            )
    
    # 3. Квесты
    quests_list = list(db_player.quests) if db_player.quests else []
    new_quest_match = re.search(r'\[NEW_QUEST\]\s*(\{.*?\})', full_text, re.DOTALL | re.IGNORECASE)
    if new_quest_match:
        try:
            quest_json = json.loads(new_quest_match.group(1))
            quest_json["status"] = "active"
            quests_list.append(quest_json)
            effects_list.append(f"📜 Новый квест: {quest_json.get('title', 'Без названия')}")
        except: pass
        full_text = full_text.replace(new_quest_match.group(0), '').strip()

    done_quest_match = re.search(r'\[QUEST_DONE\]\s*(.*?)(?:\n|$)', full_text, re.IGNORECASE)
    if done_quest_match:
        quest_title = done_quest_match.group(1).strip()
        for q in quests_list:
            if q.get("title", "").lower() == quest_title.lower():
                q["status"] = "completed"
                effects_list.append(f"✅ Квест выполнен: {q['title']}")
                break
        full_text = full_text.replace(done_quest_match.group(0), '').strip()

    db_player.quests = quests_list

    # 4. Сюжетные способности
    for unlock in unlocks:
        granted = abilities.grant(
            db_player,
            unlock.get("name"),
            description=unlock.get("description", ""),
            effect=unlock.get("effect", "insight"),
            tier=_to_int(unlock.get("tier"), 2),
            cooldown=_to_int(unlock.get("cooldown"), 2),
        )
        if granted:
            effects_list.append(f"🌟 Новая способность: {granted['name']}")

    # 5. Опыт за события (после всех изменений состояния)
    if events and allow_xp:
        _, xp_lines = xp.award_events(db_player, events, {"enemy_max_hp": enemy_max_hp})
        effects_list.extend(xp_lines)

    # 6. Победа в бою закрывает врага, даже если LLM забыл прислать ENEMY_DEAD.
    if db_player.enemy:
        won = any(
            (e.get("type") or "").strip().lower() == "combat_win"
            and (e.get("result") or "success").strip().lower() != "fail"
            for e in events
        )
        if won:
            effects_list.append(f"💀 Враг {db_player.enemy.get('name', '?')} повержен!")
            db_player.enemy = {}

# --- ЧИСТИЛЬЩИК ТЕГОВ ---
    # Удаляем ошибочно оставленные теги из текста (например, [LOCATION] Улица)
    # Это регулярное выражение найдет [LOCATION] или [ENEMY] без JSON и удалит их.
    full_text = re.sub(r'\[LOCATION\]\s*', '', full_text)
    full_text = re.sub(r'\[ENEMY\](?!\s*\{)', '', full_text) 
    # (ENEMY удаляем только если после него нет фигурной скобки {, чтобы не сломать реальные теги врагов)

    return full_text, effects_list


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _active_status(player, key: str):
    status = (getattr(player, "statuses", None) or {}).get(key)
    if not status or int(status.get("turns", 0)) <= 0 or int(status.get("value", 0)) <= 0:
        return None
    return status
