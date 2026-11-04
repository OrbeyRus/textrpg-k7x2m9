"""Жанровые профили.

Жанр задаёт тон повествования, акценты опыта, подписи характеристик и
стартовый набор. Механики при этом общие для всех жанров.
"""

from app.services.progression import STAT_DESCRIPTIONS, STAT_LABELS

DEFAULT_GENRE = "universal"

# Порядок карточек в интерфейсе
GENRE_ORDER = [
    "fantasy",
    "romance",
    "mystery",
    "horror",
    "scifi",
    "historical",
    "adventure",
    "universal",
]

# Базовые веса событий: по умолчанию всё по единице.
BASE_EVENT_WEIGHTS = {
    "combat_win": 1.0,
    "obstacle": 1.0,
    "discovery": 1.0,
    "social": 1.0,
    "relationship": 1.0,
    "quest": 1.0,
    "growth": 1.0,
    "risk": 1.0,
    "milestone": 1.0,
}

# Подсказка для Мастера Игры: как часто и насколько опасны бои в жанре.
COMBAT_HINTS = {
    "high": "бои — основа пути: враги сильны и агрессивны, урон ощутим, отступать почти некуда",
    "medium": "стычки случаются, но не каждый шаг: угроза реальна и требует расчёта",
    "low": "бои редки и нежелательны: конфликты решаются словами, уговорами и хитростью",
}

GENRES = {
    "fantasy": {
        "code": "fantasy",
        "name": "Фэнтези",
        "description": "Магия, чудовища, древние тайны и подвиги.",
        "tone": "мрачное героическое фэнтези, магия ощутима, опасность реальна",
        "progress_hint": "победы над врагами, преодоление опасностей, находки и древние тайны",
        "combat_intensity": "high",
        "ability_pack": "fantasy",
        "event_weights": {
            "combat_win": 1.3,
            "obstacle": 1.1,
            "discovery": 1.0,
            "social": 0.8,
            "relationship": 0.5,
            "quest": 1.0,
            "growth": 1.0,
            "risk": 1.0,
            "milestone": 1.1,
        },
        "stat_labels": {
            "strength": "Мощь",
            "agility": "Сноровка",
            "vitality": "Живучесть",
            "intelligence": "Магия",
            "perception": "Чутьё",
            "luck": "Фортуна",
        },
        "stat_descriptions": {
            "strength": "Мощь: +2 к силе удара оружием за очко — враги падают быстрее.",
            "agility": "Сноровка: уклонение от атак (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Живучесть: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Магия: +2 к силе заклинаний (способностей) за очко.",
            "perception": "Чутьё: меткость — промахи и слабые удары реже, +1% к шансу крита за очко.",
            "luck": "Фортуна: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Факел"],
        "starting_equipment": {"weapon": "Кинжал"},
    },
    "romance": {
        "code": "romance",
        "name": "Роман",
        "description": "Чувства, отношения, тайны сердца и выбор.",
        "tone": "камерное любовное повествование, важны чувства, взгляды и подтекст",
        "progress_hint": "развитие отношений, доверие, откровенные разговоры, преодоление недопонимания",
        "combat_intensity": "low",
        "ability_pack": "romance",
        "event_weights": {
            "combat_win": 0.3,
            "obstacle": 0.9,
            "discovery": 0.7,
            "social": 1.2,
            "relationship": 1.4,
            "quest": 1.0,
            "growth": 1.0,
            "risk": 0.9,
            "milestone": 1.2,
        },
        "stat_labels": {
            "strength": "Напор",
            "agility": "Грация",
            "vitality": "Выдержка",
            "intelligence": "Эрудиция",
            "perception": "Эмпатия",
            "luck": "Шарм",
        },
        "stat_descriptions": {
            "strength": "Напор: +2 к силе удара за очко, если дело дойдёт до драки.",
            "agility": "Грация: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Выдержка: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Эрудиция: +2 к силе способностей за очко.",
            "perception": "Эмпатия: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Шарм: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Блокнот", "Кулон"],
        "starting_equipment": {},
    },
    "mystery": {
        "code": "mystery",
        "name": "Детектив",
        "description": "Улики, допросы, дедукция и разоблачение.",
        "tone": "напряжённое расследование, детали важны, ложь чувствуется",
        "progress_hint": "находки и улики, разоблачение лжи, верные выводы, продвижение расследования",
        "combat_intensity": "medium",
        "ability_pack": "mystery",
        "event_weights": {
            "combat_win": 0.7,
            "obstacle": 1.0,
            "discovery": 1.4,
            "social": 1.1,
            "relationship": 0.7,
            "quest": 1.1,
            "growth": 1.0,
            "risk": 1.0,
            "milestone": 1.2,
        },
        "stat_labels": {
            "strength": "Натиск",
            "agility": "Реакция",
            "vitality": "Выносливость",
            "intelligence": "Дедукция",
            "perception": "Внимательность",
            "luck": "Интуиция",
        },
        "stat_descriptions": {
            "strength": "Натиск: +2 к силе удара за очко — пригодится в стычке.",
            "agility": "Реакция: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Выносливость: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Дедукция: +2 к силе способностей за очко — приёмы работают мощнее.",
            "perception": "Внимательность: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Интуиция: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Блокнот", "Лупа"],
        "starting_equipment": {},
    },
    "horror": {
        "code": "horror",
        "name": "Хоррор",
        "description": "Ужас, выживание и тонкая грань рассудка.",
        "tone": "гнетущий ужас, мало информации, много угрозы, каждое решение на вес",
        "progress_hint": "выживание, разгадка зла, преодоление страха, риск ради истины",
        "combat_intensity": "medium",
        "ability_pack": "horror",
        "event_weights": {
            "combat_win": 0.6,
            "obstacle": 1.2,
            "discovery": 1.2,
            "social": 0.8,
            "relationship": 0.6,
            "quest": 1.0,
            "growth": 0.9,
            "risk": 1.5,
            "milestone": 1.3,
        },
        "stat_labels": {
            "strength": "Натиск",
            "agility": "Реакция",
            "vitality": "Стойкость",
            "intelligence": "Смекалка",
            "perception": "Чутьё",
            "luck": "Удача",
        },
        "stat_descriptions": {
            "strength": "Натиск: +2 к силе удара за очко — когда бежать уже поздно.",
            "agility": "Реакция: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Стойкость: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Смекалка: +2 к силе способностей за очко.",
            "perception": "Чутьё: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Удача: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Фонарь", "Спички"],
        "starting_equipment": {},
    },
    "scifi": {
        "code": "scifi",
        "name": "Фантастика",
        "description": "Технологии, космос, неизведанное и логика.",
        "tone": "научная фантастика, технологии и логика, масштаб и неизвестность",
        "progress_hint": "технические решения, открытия, выживание в опасной среде, важные дилеммы",
        "combat_intensity": "medium",
        "ability_pack": "scifi",
        "event_weights": {
            "combat_win": 0.9,
            "obstacle": 1.1,
            "discovery": 1.3,
            "social": 0.9,
            "relationship": 0.7,
            "quest": 1.0,
            "growth": 1.1,
            "risk": 1.1,
            "milestone": 1.1,
        },
        "stat_labels": {
            "strength": "Мощь",
            "agility": "Реакция",
            "vitality": "Устойчивость",
            "intelligence": "Логика",
            "perception": "Наблюдательность",
            "luck": "Удача",
        },
        "stat_descriptions": {
            "strength": "Мощь: +2 к силе атаки за очко — прямое решение конфликта.",
            "agility": "Реакция: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Устойчивость: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Логика: +2 к силе способностей за очко — приёмы и техника мощнее.",
            "perception": "Наблюдательность: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Удача: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Мультитул"],
        "starting_equipment": {},
    },
    "historical": {
        "code": "historical",
        "name": "Историческое",
        "description": "Эпоха, интриги, честь и судьба.",
        "tone": "историческая драма, эпоха чувствуется в деталях, важны честь и репутация",
        "progress_hint": "интриги, репутация, верные решения, судьбоносные встречи",
        "combat_intensity": "medium",
        "ability_pack": "historical",
        "event_weights": {
            "combat_win": 0.9,
            "obstacle": 1.0,
            "discovery": 1.0,
            "social": 1.2,
            "relationship": 1.0,
            "quest": 1.1,
            "growth": 1.0,
            "risk": 1.0,
            "milestone": 1.2,
        },
        "stat_labels": {
            "strength": "Доблесть",
            "agility": "Сноровка",
            "vitality": "Здоровье",
            "intelligence": "Образованность",
            "perception": "Прозорливость",
            "luck": "Фортуна",
        },
        "stat_descriptions": {
            "strength": "Доблесть: +2 к силе удара за очко — исход поединка чести.",
            "agility": "Сноровка: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Здоровье: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Образованность: +2 к силе способностей за очко — приёмы и знания работают сильнее.",
            "perception": "Прозорливость: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Фортуна: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Письмо"],
        "starting_equipment": {},
    },
    "adventure": {
        "code": "adventure",
        "name": "Приключение",
        "description": "Дорога, риск, находки и неожиданные встречи.",
        "tone": "приключенческий дух, темп, дорога, азарт и открытия",
        "progress_hint": "новые места, смелые решения, находки, преодоление препятствий",
        "combat_intensity": "medium",
        "ability_pack": "adventure",
        "event_weights": {
            "combat_win": 1.0,
            "obstacle": 1.2,
            "discovery": 1.2,
            "social": 1.0,
            "relationship": 0.8,
            "quest": 1.1,
            "growth": 1.0,
            "risk": 1.1,
            "milestone": 1.1,
        },
        "stat_labels": {
            "strength": "Мощь",
            "agility": "Проворство",
            "vitality": "Закалка",
            "intelligence": "Смекалка",
            "perception": "Зоркость",
            "luck": "Везучесть",
        },
        "stat_descriptions": {
            "strength": "Мощь: +2 к силе удара за очко в любой стычке.",
            "agility": "Проворство: уклонение от ударов (до 60%) и инициатива — +0,5 к атаке за очко.",
            "vitality": "Закалка: +10 к запасу здоровья за очко и защита от урона.",
            "intelligence": "Смекалка: +2 к силе способностей за очко.",
            "perception": "Зоркость: меткость — слабые удары реже (до 60%), +1% к шансу крита за очко.",
            "luck": "Везучесть: +1,5% к шансу крита и +2% к находкам за очко.",
        },
        "starting_inventory": ["Верёвка", "Компас"],
        "starting_equipment": {},
    },
    "universal": {
        "code": "universal",
        "name": "Универсальное",
        "description": "Смешанный сюжет без жанровых перекосов.",
        "tone": "сбалансированное повествование, следуй за жанром книги",
        "progress_hint": "любой значимый прогресс: победы, открытия, отношения, квесты",
        "combat_intensity": "medium",
        "ability_pack": "universal",
        "event_weights": dict(BASE_EVENT_WEIGHTS),
        "stat_labels": {},
        "stat_descriptions": {},
        "starting_inventory": [],
        "starting_equipment": {},
    },
}


def normalize(code: str | None) -> str:
    """Приводит код жанра к известному значению."""
    if code and code in GENRES:
        return code
    return DEFAULT_GENRE


def get(code: str | None) -> dict:
    return GENRES[normalize(code)]


def labels_for(code: str | None) -> dict:
    """Подписи характеристик для жанра (базовые + жанровые)."""
    labels = dict(STAT_LABELS)
    labels.update(GENRES[normalize(code)].get("stat_labels", {}))
    return labels


def descriptions_for(code: str | None) -> dict:
    """Пояснения характеристик для жанра: что улучшится при вложении очка."""
    descriptions = dict(STAT_DESCRIPTIONS)
    descriptions.update(GENRES[normalize(code)].get("stat_descriptions", {}))
    return descriptions


def public_list() -> list:
    """Список жанров для интерфейса."""
    return [
        {
            "code": GENRES[code]["code"],
            "name": GENRES[code]["name"],
            "description": GENRES[code]["description"],
            "stat_labels": labels_for(code),
            "stat_descriptions": descriptions_for(code),
        }
        for code in GENRE_ORDER
    ]


def blended_weights(primary: str, secondary: str | None = None) -> dict:
    """Смешивает веса: 70% основного жанра и 30% дополнительного."""
    primary_code = normalize(primary)
    weights = dict(GENRES[primary_code]["event_weights"])

    if not secondary or secondary == primary:
        return weights

    secondary_code = normalize(secondary)
    secondary_weights = GENRES[secondary_code]["event_weights"]

    mixed = {}
    for key, base in BASE_EVENT_WEIGHTS.items():
        mixed[key] = round(
            0.7 * weights.get(key, base) + 0.3 * secondary_weights.get(key, base), 3
        )
    return mixed


def profile_for(primary: str, secondary: str | None = None) -> dict:
    """Итоговый профиль кампании с учётом второго тона."""
    primary_code = normalize(primary)
    primary_profile = GENRES[primary_code]

    secondary_code = None
    if secondary and normalize(secondary) != primary_code:
        secondary_code = normalize(secondary)

    display_name = primary_profile["name"]
    if secondary_code:
        display_name = f"{primary_profile['name']} · {GENRES[secondary_code]['name']}"

    labels = dict(STAT_LABELS)
    labels.update(primary_profile.get("stat_labels", {}))
    if secondary_code:
        for key, value in GENRES[secondary_code].get("stat_labels", {}).items():
            labels.setdefault(key, value)

    descriptions = dict(STAT_DESCRIPTIONS)
    descriptions.update(primary_profile.get("stat_descriptions", {}))
    if secondary_code:
        for key, value in GENRES[secondary_code].get("stat_descriptions", {}).items():
            descriptions.setdefault(key, value)

    return {
        "code": primary_code,
        "secondary": secondary_code,
        "display_name": display_name,
        "tone": primary_profile["tone"],
        "progress_hint": primary_profile["progress_hint"],
        "combat_intensity": primary_profile["combat_intensity"],
        "combat_hint": COMBAT_HINTS.get(
            primary_profile["combat_intensity"], COMBAT_HINTS["medium"]
        ),
        "ability_pack": primary_profile["ability_pack"],
        "stat_labels": labels,
        "stat_descriptions": descriptions,
        "event_weights": blended_weights(primary_code, secondary_code),
        "starting_inventory": list(primary_profile.get("starting_inventory", [])),
        "starting_equipment": dict(primary_profile.get("starting_equipment", {})),
    }
