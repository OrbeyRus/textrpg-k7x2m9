"""Правила боя: урон, защита, масштабирование врагов.

Числа считает сервер, а LLM только описывает сцену — так характеристики,
экипировка и жанр реально влияют на исход боя.

Формулы:
    атака игрока   = 4 + 2*сила + бонус оружия
    урон по врагу  = зажимаем число LLM в [0.7*атака; атака]
    защита         = живучесть // 2 + бонус брони
    HP врага       = базовое * (1 + 0.2*(уровень-1)) * множитель жанра
    атака врага    = (4 + 2*(HP врага // 10) + 2*(уровень-1)) * множитель жанра
    урон врага     = max(1, атака врага - защита // 2)
"""

from app.content import genres
from app.services import progression

# Жанровая интенсивность боёв (совпадает с combat_intensity профиля).
INTENSITY_MULT = {"low": 0.7, "medium": 1.0, "high": 1.4}

# Бонус оружия по ключевому слову в названии (первое совпадение выигрывает).
WEAPON_TIERS = (
    (
        (
            "меч", "топор", "булава", "молот", "секира", "копь", "копьё", "катана",
            "автомат", "винтовка", "дробовик", "карабин", "пулемёт", "пулемет",
            "гранатомёт", "гранатомет", "рапира-меч",
        ),
        10,
    ),
    (
        (
            "кинжал", "нож", "пистолет", "револьвер", "лук", "арбалет", "шпага",
            "рапира", "дубина", "палица", "праща", "стек", "тесак", "мачете",
        ),
        6,
    ),
)

# Базовый вклад слота в защиту.
SLOT_DEFENSE = {
    "armor": 4,
    "helmet": 3,
    "boots": 2,
    "cloak": 2,
    "gloves": 1,
    "ring": 1,
    "amulet": 1,
}

ARMOR_HEAVY = ("латы", "кольчуг", "кирас", "доспех", "щит", "стальн", "чешуй", "панцир")
ARMOR_LIGHT = ("кож", "кожан", "стёган", "стеган", "мехов", "ткан", "моль")


def _intensity_for(player) -> float:
    profile = genres.profile_for(
        getattr(player, "genre", None) or genres.DEFAULT_GENRE,
        getattr(player, "genre_secondary", None) or None,
    )
    return INTENSITY_MULT.get(profile["combat_intensity"], 1.0)


def _equipment(player) -> dict:
    return dict(getattr(player, "equipment", None) or {})


def weapon_bonus(player) -> int:
    """Прибавка к урону от оружия в слоте weapon."""
    weapon = str(_equipment(player).get("weapon") or "").strip().lower()
    if not weapon:
        return 0
    for words, bonus in WEAPON_TIERS:
        if any(word in weapon for word in words):
            return bonus
    return 3


def armor_bonus(player) -> int:
    """Суммарная прибавка к защите от всех надетых вещей (кроме оружия)."""
    total = 0
    for slot, item in _equipment(player).items():
        if slot == "weapon" or not item:
            continue
        total += SLOT_DEFENSE.get(slot, 1)
        name = str(item).lower()
        if any(word in name for word in ARMOR_HEAVY):
            total += 4
        elif any(word in name for word in ARMOR_LIGHT):
            total += 2
    return total


def attack_power(player) -> int:
    strength = int(getattr(player, "strength", 0) or 0)
    return progression.attack_power(strength) + weapon_bonus(player)


def attack_range(player) -> tuple:
    """Диапазон урона игрока по врагу: (минимум, максимум)."""
    power = max(1, attack_power(player))
    return max(1, round(power * 0.7)), power


def defense(player) -> int:
    vitality = int(getattr(player, "vitality", 0) or 0)
    return vitality // 2 + armor_bonus(player)


def player_damage(player, raw) -> int:
    """Урон игрока по врагу: зажимаем число LLM в диапазон характеристик."""
    try:
        value = abs(int(raw))
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return 0
    low, high = attack_range(player)
    return max(low, min(value, high))


def scale_enemy_hp(player, base_hp) -> int:
    """Масштабирует HP врага под уровень игрока и жанр."""
    try:
        base = max(1, int(base_hp))
    except (TypeError, ValueError):
        base = 1
    level = max(1, int(getattr(player, "level", 1) or 1))
    level_factor = 1 + 0.2 * (level - 1)
    return max(1, round(base * level_factor * _intensity_for(player)))


def enemy_attack(player, enemy_max_hp=0) -> int:
    """Сила удара врага по игроку."""
    try:
        max_hp = max(0, int(enemy_max_hp or 0))
    except (TypeError, ValueError):
        max_hp = 0
    level = max(1, int(getattr(player, "level", 1) or 1))
    base = 4 + 2 * (max_hp // 10) + 2 * (level - 1)
    return max(1, round(base * _intensity_for(player)))


def incoming_damage(player, enemy_max_hp=0) -> int:
    """Урон врага по игроку: сервер задаёт силу удара, защита его снижает."""
    return max(1, enemy_attack(player, enemy_max_hp) - defense(player) // 2)
