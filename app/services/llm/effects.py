import json
import re

from app.services import progression


def parse_effects(full_text, db_player):
    effects_list = []
    
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
                
                # КОСТЫЛЬ ДЛЯ SQLALCHEMY: Пересоздаем словарь, чтобы база увидела изменения
                new_enemy = dict(db_player.enemy)
                new_enemy["hp"] = max(0, new_enemy.get("hp", 0) + val)
                db_player.enemy = new_enemy
                
                effects_list.append(f"⚔️ Урон врагу: {val} HP")
                
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
                db_player.hp = max(0, min(db_player.max_hp, db_player.hp + val))
                effects_list.append(f"❤️ HP: {'+' if val > 0 else ''}{val}")
            
            # Опыт
            xp_match = re.search(r'(?<![A-Za-z_])XP:\s*([+-]?\d+)', effects_str)
            if xp_match:
                xp_gained = int(xp_match.group(1))
                if xp_gained != 0:
                    db_player.xp = max(0, db_player.xp + xp_gained)
                    effects_list.append(f"✨ Опыт: {'+' if xp_gained > 0 else ''}{xp_gained}")
                    for new_level in progression.apply_level_up(db_player):
                        effects_list.append(
                            f"🆙 Уровень {new_level}! "
                            f"+{progression.stat_points_for_level(new_level)} очк. характеристик, "
                            f"+{progression.ability_points_for_level(new_level)} очк. способностей"
                        )

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

# --- ЧИСТИЛЬЩИК ТЕГОВ ---
    # Удаляем ошибочно оставленные теги из текста (например, [LOCATION] Улица)
    # Это регулярное выражение найдет [LOCATION] или [ENEMY] без JSON и удалит их.
    full_text = re.sub(r'\[LOCATION\]\s*', '', full_text)
    full_text = re.sub(r'\[ENEMY\](?!\s*\{)', '', full_text) 
    # (ENEMY удаляем только если после него нет фигурной скобки {, чтобы не сломать реальные теги врагов)

    return full_text, effects_list