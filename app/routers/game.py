from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import database
from app.config import DEBUG, DEBUG_LOG
from app.content import genres
from app.dependencies import get_db
from app.services import abilities, campaign, gamelog, llm, progression, rag

router = APIRouter(tags=["game"])


@router.post("/reset/{player_id}")
def reset_player(player_id: int, db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if db_player:
        campaign.start_new_campaign(
            db_player,
            db_player.genre or genres.DEFAULT_GENRE,
            db_player.genre_secondary or None,
        )
        db.commit()
        gamelog.log_note(db_player, "reset", "Кампания сброшена до начального состояния")
    return {"status": "ok"}

@router.get("/story/{player_id}")
def get_story(player_id: int, choice: str = Query(None), db: Session = Depends(get_db)):
    db_player = db.query(database.Player).filter(database.Player.id == player_id).first()
    if not db_player: raise HTTPException(status_code=404)

    abilities.tick(db_player)

    book_data = rag.get_player_book(player_id, db)

    prior_history = list(db_player.history) if db_player.history else []
    # Вступление уже показано, если в истории есть хотя бы один ответ Мастера.
    has_opening = any(str(line).startswith("Мастер:") for line in prior_history)

    history = prior_history
    if choice:
        history.append(f"Игрок: {choice}")
    recent_history = "\n".join(history[-6:]) if history else "Начало пути."

    is_start = not has_opening

    if is_start:
        if len(book_data) >= 2:
            lore_context = book_data[0]['text'] + "\n" + book_data[1]['text']
        elif len(book_data) == 1:
            lore_context = book_data[0]['text']
        else:
            lore_context = "Информация о мире недоступна."
    else:
        last_scene = next(
            (
                str(line)[len("Мастер:"):].strip()
                for line in reversed(prior_history)
                if str(line).startswith("Мастер:")
            ),
            "",
        )
        search_query = (
            f"Локация: {db_player.location}. Действие игрока: {choice}. "
            f"Текущая сцена: {last_scene[-400:]}"
        )
        lore_context = rag.get_relevant_context(book_data, search_query, top_k=3)

        if DEBUG:
            print("\n" + "=" * 50)
            print(f"ИГРОК СПРОСИЛ: {choice}")
            print(f"НАЙДЕНО В КНИГЕ: {lore_context[:300]}...")
            print("=" * 50 + "\n")

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
    learned_names = [a["name"] for a in abilities.catalog_view(db_player) if a["learned"]]
    abilities_line = ", ".join(learned_names) if learned_names else "нет"

    prompt = f"""Ты — талантливый писатель и Мастер Игры.
{start_instruction}

ЖАНР КАМПАНИИ: {profile['display_name']}
ТОН ПОВЕСТВОВАНИЯ: {profile['tone']}
ЧТО СЧИТАЕТСЯ ПРОГРЕССОМ: {profile['progress_hint']}
БОИ В ЭТОМ ЖАНРЕ: {profile['combat_hint']}

СОСТОЯНИЕ ИГРОКА:
Имя: {db_player.name}, HP: {db_player.hp}/{db_player.max_hp}, Локация: {db_player.location}
Характеристики: {stats_line}
Экипировка: {db_player.equipment}
Инвентарь: {db_player.inventory}
Способности: {abilities_line}
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
5. ФОРМАТ ЭФФЕКТОВ: Пиши строго так: [EFFECTS] HP: -5, ITEM: Название, REMOVE_ITEM: Название, LOCATION: Название. Опыт в [EFFECTS] НЕ пиши.
5а. ОПИСАНИЕ ПРЕДМЕТОВ: когда игрок находит вещь, добавь короткое пояснение после названия через тире: ITEM: Название — что это и зачем (до 8 слов, без запятых). Пример: ITEM: Ржавый кинжал — бьёт быстро, но неглубоко.
6. ИСПОЛЬЗОВАНИЕ ПРЕДМЕТОВ: Если игрок отдает или использует предмет — используй ТОЛЬКО REMOVE_ITEM.
7. ОПЫТ ЗА СОБЫТИЯ: не пиши числа опыта. Вместо этого добавь с новой строки ОДИН тег события:
   [EVENT] type=ТИП, result=success|partial|fail, tier=minor|standard|major|epic, target="объект"
   ТИП выбирай из: combat_win (победа в бою), obstacle (преодолённая опасность или препятствие), discovery (новая локация, улика, тайна), social (убедил, договорился, разоблачил), relationship (сближение, доверие, важный разговор), quest (взял или завершил квест), growth (обучение, тренировка, опыт ошибки), risk (риск с ценой), milestone (сюжетный поворот, глава).
   tier: minor — мелочь, standard — обычное, major — важное, epic — эпохальное. Обычные повторяющиеся действия НЕ размечай.
8. КВЕСТЫ: Если игроку дают новое задание, добавь тег: [NEW_QUEST] {{"title": "Название", "description": "Описание", "giver": "Кто дал", "location": "Где"}}. Если игрок выполнил квест, добавь тег: [QUEST_DONE] Название.
9. ВСЕ ЛОКАЦИИ ПИШИ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.
10. ВРАГИ: Если начинается бой, создавай врага тегом: [ENEMY] {{"name": "Имя", "hp": 30}}.
11. Если игрок атакует, нанеси урон врагу: [EFFECTS] ENEMY_HP: -10. Учитывай оружие игрока.
12. Если враг атакует игрока, нанеси урон игроку: [EFFECTS] HP: -5.
    ВАЖНО: в бою сервер сам пересчитывает числа по характеристикам и экипировке — тебе достаточно описать сцену. Просто укажи, что удар попал (ENEMY_HP отрицательный) или что враг попал по игроку (HP отрицательный), не подбирая точные цифры.
13. ВАЖНО: Если в "ПОСЛЕДНИХ СОБЫТИЯХ" было описано сражение, учти это. Опиши последствия. НЕ возвращай игрока в старые локации.
14. КАТЕГОРИЧЕСКИЙ ЗАПРЕТ: Никогда не пиши теги вроде [LOCATION] или [ENEMY] открытым текстом внутри описания. Все команды должны быть либо в блоке [EFFECTS], либо в формате [ENEMY] {{...}}.
15. ФОРМАТИРОВАНИЕ: Каждый тег (LOCATION, ENEMY, EFFECTS) пиши СТРОГО С НОВОЙ СТРОКИ. Никогда не сливай их в одну строку.
16. ИГРОВЫЕ ЭЛЕМЕНТЫ: Если в книге есть игровой интерфейс (восклицательные знаки, системные окна), используй их, но только для тех персонажей и событий, которые уже произошли в книге. Не выдумывай новых NPC с квестами, если их не было в тексте.
17. ДЕТАЛИЗАЦИЯ: Описывай не только действия, но и ощущения, запахи, звуки, внутренние мысли героя. Сделай сцену живой и кинематографичной.
18. СПОСОБНОСТИ ИГРОКА: игрок уже владеет перечисленными способностями — учитывай их, когда он их применяет. Если по сюжету книги герой получает НОВУЮ особую способность, добавь с новой строки тег:
   [ABILITY_UNLOCK] name="Название", description="что делает", effect=damage|heal|guard|rage|insight|charm|stealth, tier=1|2|3
   Выдавай такую способность редко и только по значимому сюжетному событию.
19. ЗАПРЕТ: Никогда не описывай в открытом тексте механику игры (очки, ранги, перезарядки).
20. ФОРМАТ ОТВЕТА: каждый ход заканчивай блоком [EFFECTS] (если изменений нет — напиши [EFFECTS] NONE). Если случилось значимое событие — добавь ровно ОДИН тег [EVENT] подходящего типа.
21. ПРЕДМЕТЫ ИГРОКА: списки «Инвентарь» и «Экипировка» — единственный источник правды о вещах. Используй ТОЛЬКО те предметы, что там перечислены, и описывай ровно их. Не заменяй предмет игрока другим (фонарик — это фонарик, а не зажигалка) и не выдумывай вещей, которых у него нет.
22. БЕЗ ПОВТОРОВ: не повторяй дословно фразы и целые предложения из «ПОСЛЕДНИХ СОБЫТИЙ». Даже если игрок снова делает то же самое, каждый ход описывай по-новому — другими словами, с новыми деталями, ощущениями и поворотами. Запрещены шаблонные повторы вроде «ты упорно продвигаешься вперёд...».

ПРИМЕРЫ ПРАВИЛЬНОГО ОТВЕТА:
Игрок: "Бросаю гранату"
Твой ответ: Ты швыряешь гранату. Взрыв.
[EFFECTS] HP: -10, REMOVE_ITEM: Граната
[EVENT] type=obstacle, result=success, tier=major, target="склад"

Игрок: "Иду в лес"
Твой ответ: Ты входишь под темные своды. Ветки хлещут по лицу.
[EFFECTS] LOCATION: Темный лес
[EVENT] type=discovery, result=success, tier=standard, target="Темный лес"

Игрок: "Обнимаю Марту и говорю, что она мне дорога"
Твой ответ: Она замирает, потом отвечает на объятие.
[EFFECTS] NONE
[EVENT] type=relationship, result=success, tier=major, target="Марта"
"""

    try:
        raw_text = llm.call_llm(prompt)
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n--- ИГРОК {player_id} ---\n" + raw_text + "\n---\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    full_text, effects_list = llm.parse_effects(raw_text, db_player, allow_xp=not is_start)
    db.commit()

    history.append(f"Мастер: {full_text}")
    db_player.history = history[-15:]
    db.commit()

    gamelog.log_turn(
        db_player,
        "story",
        action=choice or ("<старт>" if is_start else ""),
        raw=raw_text,
        text=full_text,
        effects=effects_list,
        extra={"is_start": is_start},
    )

    return {"story": full_text, "effects": effects_list}