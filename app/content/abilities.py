"""Каталог способностей.

Способности не привязаны к конкретной книге: набор зависит от жанра кампании,
а уникальные «книжные» способности выдаются сюжетом отдельно.

Эффект (effect) — это механика, общая для всех жанров:
    damage  — гарантированный урон в бою;
    heal    — восстановление HP;
    guard   — щит: снижает входящий урон несколько ходов;
    rage    — прилив сил: усиливает урон игрока несколько ходов;
    insight — озарение: подсказка и преимущество вне боя;
    charm   — обаяние: сближение и удача в разговоре вне боя;
    stealth — скрытность: уйти от опасности (в бою — побег).

tier задаёт силу и стоимость (cost = tier), а rank — ступень развития.
"""

MAX_RANK = 3

CONTENT_HELP = (
    "Способности дают игроку активные приёмы. Сервер сам считает их эффект, "
    "поэтому в бою и вне боя они работают одинаково предсказуемо."
)


def _a(
    ability_id,
    name,
    description,
    tier,
    effect,
    value,
    growth=0,
    cooldown=0,
    scaling=None,
    combat=True,
    field=False,
    max_rank=MAX_RANK,
):
    return {
        "id": ability_id,
        "name": name,
        "description": description,
        "tier": tier,
        "cost": tier,
        "effect": effect,
        "value": value,
        "growth": growth,
        "cooldown": cooldown,
        "scaling": scaling,
        "combat": combat,
        "field": field,
        "max_rank": max_rank,
    }


PACKS = {
    "fantasy": [
        _a("power_strike", "Мощный удар", "Усиленный удар, наносит повышенный урон.", 1, "damage", 12, 6, 0, "strength"),
        _a("shield_block", "Блок щитом", "Ставит щит, который гасит входящий урон.", 1, "guard", 8, 5, 2),
        _a("heal", "Исцеление", "Восстанавливает здоровье.", 1, "heal", 25, 15, 3, field=True),
        _a("fireball", "Огненный шар", "Магический удар по врагу.", 2, "damage", 18, 8, 2, "intelligence"),
        _a("battle_fury", "Боевой азарт", "Усиливает ваши атаки на несколько ходов.", 2, "rage", 7, 4, 3),
        _a("arcane_insight", "Магическое озарение", "Раскрывает скрытое и подсказывает путь.", 2, "insight", 0, 0, 2, combat=False, field=True),
    ],
    "romance": [
        _a("warm_word", "Тёплое слово", "Берёт верный тон и располагает собеседника.", 1, "charm", 0, 0, 1, combat=False, field=True),
        _a("keen_look", "Взгляд в душу", "Читает чувства и скрытые мотивы.", 1, "insight", 0, 0, 2, combat=False, field=True),
        _a("support", "Поддержка", "Придаёт сил и восстанавливает здоровье.", 1, "heal", 22, 14, 3, field=True),
        _a("confession", "Признание", "Откровенный разговор сближает по-настоящему.", 2, "charm", 0, 0, 3, combat=False, field=True),
        _a("sharp_tongue", "Острый язык", "Колкая фраза сбивает противника с толку.", 2, "guard", 7, 4, 2),
        _a("grand_gesture", "Красивый жест", "Запоминающийся поступок воодушевляет.", 2, "rage", 6, 4, 3),
    ],
    "mystery": [
        _a("observe", "Наблюдательность", "Замечает важную деталь.", 1, "insight", 0, 0, 1, combat=False, field=True),
        _a("quick_shot", "Точный выстрел", "Бьёт наверняка.", 2, "damage", 16, 7, 1, "perception"),
        _a("hide", "Затаиться", "Уйти в тень от чужих глаз.", 1, "stealth", 0, 0, 2, field=True),
        _a("interrogation", "Допрос", "Давит на слабое место и сбивает уверенность.", 1, "guard", 6, 4, 2),
        _a("deduce", "Дедукция", "Выстраивает цепочку выводов.", 2, "insight", 0, 0, 2, combat=False, field=True),
        _a("bluff", "Блеф", "Играет на доверии и выигрывает время.", 2, "charm", 0, 0, 2, combat=False, field=True),
    ],
    "horror": [
        _a("steady_nerves", "Крепкие нервы", "Собирает волю в кулак и держит удар.", 1, "guard", 9, 5, 3),
        _a("dash_dark", "Рывок из тьмы", "Уходит от опасности.", 1, "stealth", 0, 0, 2, field=True),
        _a("lantern", "Свет фонаря", "Освещает то, что скрыто.", 1, "insight", 0, 0, 2, combat=False, field=True),
        _a("desperate_strike", "Отчаянный удар", "Бьёт из последних сил.", 2, "damage", 15, 9, 2),
        _a("endure", "Терпеть", "Затягивает раны и восстанавливается.", 2, "heal", 20, 16, 3, field=True),
        _a("occult_lore", "Запретное знание", "Слабые места нечисти.", 3, "guard", 12, 6, 4),
    ],
    "scifi": [
        _a("pulse_shot", "Импульсный выстрел", "Разряд энергии по цели.", 1, "damage", 13, 6, 1, "intelligence"),
        _a("scan", "Сканирование", "Анализирует обстановку и слабые места.", 1, "insight", 0, 0, 1, combat=False, field=True),
        _a("medkit", "Аптечка", "Быстро залечивает раны.", 1, "heal", 24, 14, 3, field=True),
        _a("energy_barrier", "Энергощит", "Поглощает входящий урон.", 2, "guard", 10, 6, 3),
        _a("overcharge", "Перегрузка", "Высвобождает накопленную энергию.", 2, "damage", 20, 9, 3, "intelligence"),
        _a("hack", "Взлом", "Ломает защиту противника.", 2, "guard", 9, 5, 2),
    ],
    "historical": [
        _a("lunge", "Выпад", "Стремительная атака.", 1, "damage", 12, 6, 1, "strength"),
        _a("parry", "Парирование", "Отводит удар.", 1, "guard", 8, 5, 2),
        _a("herbs", "Травы", "Затягивает раны.", 1, "heal", 22, 14, 3, field=True),
        _a("read_intrigue", "Чутьё интриг", "Улавливает скрытые намерения.", 1, "insight", 0, 0, 2, combat=False, field=True),
        _a("courtly_charm", "Светское обхождение", "Располагает к себе.", 2, "charm", 0, 0, 2, combat=False, field=True),
        _a("rally", "Воодушевление", "Ведёт за собой и придаёт сил.", 2, "rage", 7, 4, 3),
    ],
    "adventure": [
        _a("swift_strike", "Быстрый удар", "Лёгкая стремительная атака.", 1, "damage", 11, 6, 0, "agility"),
        _a("dodge", "Уклонение", "Уходит из-под удара.", 1, "guard", 8, 5, 1),
        _a("second_wind", "Второе дыхание", "Восстанавливает силы.", 1, "heal", 20, 14, 3, field=True),
        _a("lucky_find", "Удачная находка", "Замечает полезное рядом.", 1, "insight", 0, 0, 2, combat=False, field=True),
        _a("brave_charge", "Смелая атака", "Наваливается всем телом.", 2, "damage", 18, 8, 2, "strength"),
        _a("inspiration", "Вдохновение", "Прилив решимости.", 2, "rage", 7, 4, 3),
    ],
    "universal": [
        _a("strike", "Удар", "Прямая атака.", 1, "damage", 12, 6, 0, "strength"),
        _a("brace", "Стойка", "Готовность держать удар.", 1, "guard", 8, 5, 2),
        _a("mend", "Перевязка", "Останавливает кровь и лечит.", 1, "heal", 22, 14, 3, field=True),
        _a("focus", "Сосредоточение", "Собирает внимание и подсказывает.", 1, "insight", 0, 0, 2, combat=False, field=True),
        _a("feint", "Обманный манёвр", "Сбивает противника с толку.", 2, "guard", 8, 5, 2),
        _a("surge", "Прилив сил", "Придаёт мощь атакам.", 2, "rage", 7, 4, 3),
    ],
}

DEFAULT_PACK = "universal"

EFFECTS = ("damage", "heal", "guard", "rage", "insight", "charm", "stealth")


def pack(code: str | None) -> list:
    return PACKS.get(code or DEFAULT_PACK, PACKS[DEFAULT_PACK])


def _iter():
    for abilities in PACKS.values():
        for ability in abilities:
            yield ability


def get(ability_id: str | None):
    if not ability_id:
        return None
    for ability in _iter():
        if ability["id"] == ability_id:
            return ability
    return None


def find(key: str | None):
    """Ищет способность по id, затем по имени (без учёта регистра)."""
    if not key:
        return None
    key = str(key).strip()
    found = get(key)
    if found:
        return found
    low = key.lower()
    for ability in _iter():
        if ability["name"].lower() == low:
            return ability
    return None
