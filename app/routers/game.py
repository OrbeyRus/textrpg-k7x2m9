from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import database
from app.config import DEBUG_LOG
from app.content import genres
from app.dependencies import get_db
from app.services import campaign, llm, progression, rag

router = APIRouter(tags=["game"])


@router.get("/reset/{player_id}")
def reset_player(player_id: int, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if db_player:
        campaign.start_new_campaign(
            db_player,
            db_player.genre or genres.DEFAULT_GENRE,
            db_player.genre_secondary or None,
        )
        db.commit()
    return {"status": "ok"}

@router.get("/story/{player_id}")
def get_story(player_id: int, choice: str = Query(None), db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)
    
    book_data = rag.get_player_book(player_id, db)
    
    history = list(db_player.history) if db_player.history else []
    if choice: history.append(f"Игрок: {choice}")
    recent_history = "\n".join(history[-6:]) if history else "Начало пути."
    
    is_start = False
    if not choice or "Начать приключение" in str(choice) or len(history) <= 1:
        is_start = True
        
    if is_start:
        if len(book_data) >= 2:
            lore_context = book_data[0]['text'] + "\n" + book_data[1]['text']
        elif len(book_data) == 1:
            lore_context = book_data[0]['text']
        else:
            lore_context = "Информация о мире недоступна."
    else:
        search_query = f"Локация: {db_player.location}. Персонажи: {db_player.name}. Действие: {choice}. Атмосфера: начало книги."
        lore_context = rag.get_relevant_context(book_data, search_query, top_k=1)

        # --- ОТЛАДКА RAG ---
        print("\n" + "="*50)
        print(f"ИГРОК СПРОСИЛ: {choice}")
        print(f"НАЙДЕНО В КНИГЕ: {lore_context[:300]}...") # Показываем первые 300 символов
        print("="*50 + "\n")

    if is_start:
        start_instruction = f"""ЭТО САМОЕ НАЧАЛО ИГРЫ. Твоя задача — литературно пересказать отрывок из книги, чтобы начать сюжет.
ВОТ ТЕКСТ ИЗ КНИГИ, С КОТОРОГО НУЖНО НАЧАТЬ (используй его строго, не придумывай отсебятину):
---
{lore_context}
---

Напиши вступление от ВТОРОГО лица, описывая эту сцену. 
В САМОМ КОНЦЕ ответа ты ОБЯЗАН добавить тег: [EFFECTS] LOCATION: Название_локации_на_русском (например: Квартира, Лес, Улица)."""
    else:
        start_instruction = f"""ЛОР МИРА:
{lore_context}"""

    profile = genres.profile_for(
        db_player.genre or genres.DEFAULT_GENRE,
        db_player.genre_secondary or None,
    )
    stat_labels = profile["stat_labels"]
    stats_line = ", ".join(
        f"{stat_labels.get(key, key)} {getattr(db_player, key)}"
        for key in progression.STAT_KEYS
    )

    prompt = f"""Ты — талантливый писатель и Мастер Игры.
{start_instruction}

ЖАНР КАМПАНИИ: {profile['display_name']}
ТОН ПОВЕСТВОВАНИЯ: {profile['tone']}
ЧТО СЧИТАЕТСЯ ПРОГРЕССОМ: {profile['progress_hint']}

СОСТОЯНИЕ ИГРОКА:
Имя: {db_player.name}, HP: {db_player.hp}/{db_player.max_hp}, Локация: {db_player.location}
Характеристики: {stats_line}
Экипировка: {db_player.equipment}
Инвентарь: {db_player.inventory}
Способности: {db_player.abilities}
Отношения: {db_player.relationships}
Активные квесты: {db_player.quests}
Текущий враг: {db_player.enemy}

ПОСЛЕДНИЕ СОБЫТИЯ:
{recent_history}

ПРАВИЛА:
1. Пиши от ВТОРОГО лица. Опиши результат действия игрока.
2. ОБЯЗАТЕЛЬНО используй факты из текста книги. Но если предложенный отрывок не соответствует текущей локации, действию или персонажам (например, в книге описаны бургеры, а герой в квартире с женой), ПРОИГНОРИРУЙ этот отрывок и пиши, опираясь на последние события и общую логику лора.
3. Объем: 2-3 абзаца (6-10 предложений). Только на русском.
4. СИСТЕМА ЭФФЕКТОВ: Ты — игровой движок. Если в мире происходят изменения, ты ОБЯЗАН добавить в самом конце скрытый тег [EFFECTS].
5. ФОРМАТ ЭФФЕКТОВ: Пиши строго так: [EFFECTS] HP: -5, XP: +20, ITEM: Название, REMOVE_ITEM: Название, LOCATION: Название.
6. ИСПОЛЬЗОВАНИЕ ПРЕДМЕТОВ: Если игрок отдает или использует предмет — используй ТОЛЬКО REMOVE_ITEM.
7. Опыт (XP) давай за значимый прогресс по жанру: победа или преодоление опасности, важное открытие или разгадка, развитие отношений или доверия, продвижение и завершение квеста. За обычные повторяющиеся действия пиши [EFFECTS] NONE.
8. КВЕСТЫ: Если игроку дают новое задание, добавь тег: [NEW_QUEST] {{"title": "Название", "description": "Описание", "giver": "Кто дал", "location": "Где"}}. Если игрок выполнил квест, добавь тег: [QUEST_DONE] Название.
9. ВСЕ ЛОКАЦИИ ПИШИ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.
10. ВРАГИ: Если начинается бой, создавай врага тегом: [ENEMY] {{"name": "Имя", "hp": 30}}.
11. Если игрок атакует, нанеси урон врагу: [EFFECTS] ENEMY_HP: -10. Учитывай оружие игрока.
12. Если враг атакует игрока, нанеси урон игроку: [EFFECTS] HP: -5.
13. ВАЖНО: Если в "ПОСЛЕДНИХ СОБЫТИЯХ" было описано сражение, учти это. Опиши последствия. НЕ возвращай игрока в старые локации.
14. КАТЕГОРИЧЕСКИЙ ЗАПРЕТ: Никогда не пиши теги вроде [LOCATION] или [ENEMY] открытым текстом внутри описания. Все команды должны быть либо в блоке [EFFECTS], либо в формате [ENEMY] {{...}}.
15. ФОРМАТИРОВАНИЕ: Каждый тег (LOCATION, ENEMY, EFFECTS) пиши СТРОГО С НОВОЙ СТРОКИ. Никогда не сливай их в одну строку.
16. ИГРОВЫЕ ЭЛЕМЕНТЫ: Если в книге есть игровой интерфейс (восклицательные знаки, системные окна), используй их, но только для тех персонажей и событий, которые уже произошли в книге. Не выдумывай новых NPC с квестами, если их не было в тексте.
17. ДЕТАЛИЗАЦИЯ: Описывай не только действия, но и ощущения, запахи, звуки, внутренние мысли героя. Сделай сцену живой и кинематографичной.

ПРИМЕРЫ ПРАВИЛЬНОГО ОТВЕТА:
Игрок: "Бросаю гранату"
Твой ответ: Ты швыряешь гранату. Взрыв. [EFFECTS] HP: -10, XP: +50, REMOVE_ITEM: Граната

Игрок: "Иду в лес"
Твой ответ: Ты входишь под темные своды. Ветки хлещут по лицу.
[EFFECTS] LOCATION: Темный лес
"""

    try:
        full_text = llm.call_llm(prompt)
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n--- ИГРОК {player_id} ---\n" + full_text + "\n---\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    full_text, effects_list = llm.parse_effects(full_text, db_player)
    db.commit()

    history.append(f"Мастер: {full_text}")
    db_player.history = history[-15:]
    db.commit()
    
    return {"story": full_text, "effects": effects_list}