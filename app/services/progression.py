"""Единая система прогрессии персонажа.

Все числа, из которых складывается «формула увеличения», собраны здесь,
чтобы их можно было менять в одном месте и не искать по всему проекту.

Формулы:
    опыт до следующего уровня   = XP_BASE + XP_LINEAR*(L-1) + XP_QUADRATIC*(L-1)^2
    очки характеристик за уровень = STAT_POINTS_PER_LEVEL
                                    + (L-1) // STAT_POINTS_BONUS_EVERY
    очки способностей за уровень  = ABILITY_POINTS_PER_LEVEL
                                    + (L-1) // ABILITY_POINTS_BONUS_EVERY
    макс. HP за уровень          = HP_PER_LEVEL + vitality // HP_VITALITY_STEP
    стоимость +1 характеристики  = POINT_COST (1 очко)
    эффект +1 живучести          = +HP_PER_VITALITY к макс. HP и текущему HP
"""

STAT_KEYS = ("strength", "agility", "vitality", "intelligence", "perception", "luck")

STAT_LABELS = {
    "strength": "Сила",
    "agility": "Ловкость",
    "vitality": "Живучесть",
    "intelligence": "Интеллект",
    "perception": "Восприятие",
    "luck": "Удача",
}

# ---------- стартовые значения ----------
START_LEVEL = 1
START_STAT_POINTS = 3
START_ABILITY_POINTS = 1

# ---------- кривая опыта ----------
XP_BASE = 100        # опыт для перехода 1 -> 2
XP_LINEAR = 60       # линейная прибавка за каждый следующий уровень
XP_QUADRATIC = 20    # квадратичная прибавка (сглаживает «горку» на высоких уровнях)
MAX_LEVEL = 100      # страховка от бесконечного цикла

# ---------- награды за уровень ----------
STAT_POINTS_PER_LEVEL = 3        # базовые очки характеристик за уровень
STAT_POINTS_BONUS_EVERY = 5      # +1 очко каждые N уровней
ABILITY_POINTS_PER_LEVEL = 1     # базовые очки способностей за уровень
ABILITY_POINTS_BONUS_EVERY = 3   # +1 очко способностей каждые N уровней

HP_PER_LEVEL = 15                # прирост макс. HP за уровень
HP_VITALITY_STEP = 5             # каждые N единиц живучести дают +1 HP к приросту

# ---------- характеристики ----------
POINT_COST = 1                   # сколько очков стоит +1 к характеристике
HP_PER_VITALITY = 10             # +1 живучести = +10 макс. HP
ATTACK_PER_STRENGTH = 2          # +1 силы = +2 к урону в бою
MAGIC_PER_INTELLIGENCE = 2       # +1 интеллекта = +2 к силе способностей


def xp_to_next(level: int) -> int:
    """Сколько опыта нужно, чтобы уйти с уровня `level` на следующий."""
    lv = max(1, int(level))
    n = lv - 1
    return int(XP_BASE + XP_LINEAR * n + XP_QUADRATIC * n * n)


def stat_points_for_level(level: int) -> int:
    """Сколько очков характеристик даётся за достижение уровня `level`."""
    lv = max(1, int(level))
    return STAT_POINTS_PER_LEVEL + (lv - 1) // STAT_POINTS_BONUS_EVERY


def ability_points_for_level(level: int) -> int:
    """Сколько очков способностей даётся за достижение уровня `level`."""
    lv = max(1, int(level))
    return ABILITY_POINTS_PER_LEVEL + (lv - 1) // ABILITY_POINTS_BONUS_EVERY


def hp_gain_for_level(vitality: int) -> int:
    """Прирост макс. HP за очередной уровень с учётом живучести."""
    return HP_PER_LEVEL + max(0, int(vitality)) // HP_VITALITY_STEP


def attack_power(strength: int) -> int:
    return 4 + max(0, int(strength)) * ATTACK_PER_STRENGTH


def magic_power(intelligence: int) -> int:
    return 3 + max(0, int(intelligence)) * MAGIC_PER_INTELLIGENCE


def apply_level_up(player) -> list:
    """Повышает уровень, пока хватает опыта.

    Возвращает список новых уровней (может быть пустым).
    Работает с любой моделью, у которой есть поля из database.Player.
    """
    gained = []

    # страховка от «нулевого» или отрицательного порога
    if not getattr(player, "next_level_xp", 0) or player.next_level_xp <= 0:
        player.next_level_xp = xp_to_next(player.level)

    guard = 0
    while player.xp >= player.next_level_xp and player.level < MAX_LEVEL and guard < 1000:
        guard += 1
        player.xp -= player.next_level_xp
        player.level += 1
        gained.append(player.level)

        player.max_hp += hp_gain_for_level(player.vitality)
        player.hp = player.max_hp

        player.stat_points += stat_points_for_level(player.level)
        player.ability_points += ability_points_for_level(player.level)

        player.next_level_xp = xp_to_next(player.level)

    if player.level >= MAX_LEVEL:
        player.xp = min(player.xp, player.next_level_xp)

    return gained


def apply_stat_increase(player, stat_name: str, old_value: int) -> int:
    """Применяет эффект от +1 к характеристике. Возвращает прирост макс. HP."""
    hp_gain = 0
    if stat_name == "vitality":
        hp_gain = HP_PER_VITALITY
        player.max_hp += hp_gain
        player.hp += hp_gain
    return hp_gain
