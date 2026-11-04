"""Тесты формул боя: атака, защита, масштабирование врагов.

Числа боя считает сервер, поэтому формулы должны быть предсказуемыми
и не зависеть от того, что придумает LLM.
"""

from app.services import combat


class DummyPlayer:
    def __init__(self, **kwargs):
        self.strength = kwargs.get("strength", 0)
        self.vitality = kwargs.get("vitality", 0)
        self.level = kwargs.get("level", 1)
        self.equipment = kwargs.get("equipment", {})
        self.genre = kwargs.get("genre", "fantasy")
        self.genre_secondary = kwargs.get("genre_secondary", "")


# --- Оружие ---------------------------------------------------------------

def test_weapon_bonus_without_weapon():
    assert combat.weapon_bonus(DummyPlayer()) == 0


def test_weapon_bonus_tiers():
    heavy = DummyPlayer(equipment={"weapon": "Стальной меч"})
    light = DummyPlayer(equipment={"weapon": "Ржавый кинжал"})
    other = DummyPlayer(equipment={"weapon": "Лопата"})

    assert combat.weapon_bonus(heavy) == 10
    assert combat.weapon_bonus(light) == 6
    assert combat.weapon_bonus(other) == 3


# --- Защита ---------------------------------------------------------------

def test_armor_bonus_slots_and_material():
    player = DummyPlayer(
        equipment={
            "weapon": "Меч",  # оружие в защиту не входит
            "armor": "Стальные латы",
            "helmet": "Шлем",
        }
    )
    # armor 4 + heavy 4 + helmet 3 = 11
    assert combat.armor_bonus(player) == 11


def test_armor_bonus_light_material():
    player = DummyPlayer(equipment={"armor": "Кожаная куртка"})
    # armor 4 + light 2 = 6
    assert combat.armor_bonus(player) == 6


def test_defense_adds_vitality_half():
    player = DummyPlayer(vitality=7, equipment={"armor": "Кожаная куртка"})
    assert combat.defense(player) == 7 // 2 + 6


# --- Атака игрока ---------------------------------------------------------

def test_attack_power_formula():
    player = DummyPlayer(strength=5, equipment={"weapon": "Стальной меч"})
    # 4 + 2*5 + 10 = 24
    assert combat.attack_power(player) == 24


def test_attack_range_is_seventy_percent():
    player = DummyPlayer(strength=5, equipment={"weapon": "Стальной меч"})
    low, high = combat.attack_range(player)
    assert high == 24
    assert low == round(24 * 0.7)


def test_player_damage_clamped_into_range():
    player = DummyPlayer(strength=5, equipment={"weapon": "Стальной меч"})
    low, high = combat.attack_range(player)

    assert combat.player_damage(player, -999) == high  # слишком много
    assert combat.player_damage(player, -1) == low  # слишком мало
    assert combat.player_damage(player, 0) == 0  # без удара
    assert low <= combat.player_damage(player, -12) <= high


# --- Масштабирование врагов ----------------------------------------------

def test_enemy_hp_scales_with_level():
    # «mystery» — средняя интенсивность (множитель 1.0), чтобы изолировать уровень.
    lvl1 = combat.scale_enemy_hp(DummyPlayer(level=1, genre="mystery"), 30)
    lvl6 = combat.scale_enemy_hp(DummyPlayer(level=6, genre="mystery"), 30)
    # level 6: 1 + 0.2*5 = 2.0
    assert lvl1 == 30
    assert lvl6 == 60


def test_enemy_hp_uses_genre_intensity():
    high = combat.scale_enemy_hp(DummyPlayer(genre="fantasy"), 100)  # бои — основа
    low = combat.scale_enemy_hp(DummyPlayer(genre="romance"), 100)  # бои редки
    assert high > low


def test_enemy_hp_never_below_one():
    assert combat.scale_enemy_hp(DummyPlayer(), 0) >= 1


def test_enemy_attack_grows_with_enemy_hp_and_level():
    weak = combat.enemy_attack(DummyPlayer(level=1), 10)
    strong = combat.enemy_attack(DummyPlayer(level=6), 60)
    assert strong > weak


def test_incoming_damage_reduced_by_defense():
    unarmored = DummyPlayer(level=3, vitality=0)
    armored = DummyPlayer(level=3, vitality=10, equipment={"armor": "Стальные латы"})

    assert combat.incoming_damage(armored, 30) < combat.incoming_damage(unarmored, 30)


def test_incoming_damage_never_below_one():
    tank = DummyPlayer(
        level=1,
        vitality=100,
        equipment={"armor": "Стальные латы", "helmet": "Шлем"},
    )
    assert combat.incoming_damage(tank, 1) >= 1


def test_enemy_attack_hp_term_is_capped():
    # Очень «толстый» враг бьёт не сильнее, чем просто крупный.
    big = combat.enemy_attack(DummyPlayer(level=1), 100)
    bigger = combat.enemy_attack(DummyPlayer(level=1), 1000)
    assert big == bigger


def test_incoming_damage_capped_by_player_max_hp():
    player = DummyPlayer(level=10)
    player.max_hp = 100
    player.hp = 100
    damage = combat.incoming_damage(player, 500)
    assert damage <= round(100 * combat.MAX_HIT_FRACTION)
