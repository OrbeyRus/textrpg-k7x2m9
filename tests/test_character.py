"""Тесты новых влияний характеристик и окна персонажа.

Ловкость -> уклонение и инициатива, восприятие -> меткость и крит,
удача -> крит и добыча. Формулы детерминированные, поэтому проверяем
на понятных игроках.
"""

import random

from app.services import campaign, combat, llm, loot, progression


class DummyPlayer:
    def __init__(self, **kwargs):
        self.name = "Тест"
        self.level = kwargs.get("level", 1)
        self.xp = 0
        self.next_level_xp = progression.xp_to_next(1)
        self.hp = kwargs.get("hp", 100)
        self.max_hp = kwargs.get("max_hp", 100)
        self.strength = kwargs.get("strength", 5)
        self.agility = kwargs.get("agility", 5)
        self.vitality = kwargs.get("vitality", 5)
        self.intelligence = kwargs.get("intelligence", 5)
        self.perception = kwargs.get("perception", 5)
        self.luck = kwargs.get("luck", 5)
        self.stat_points = 0
        self.ability_points = 0
        self.inventory = []
        self.equipment = kwargs.get("equipment", {})
        self.item_notes = {}
        self.quests = []
        self.location = "Неизвестно"
        self.enemy = kwargs.get("enemy", {"name": "Гоблин", "hp": 30, "max_hp": 30})
        self.abilities = []
        self.genre = kwargs.get("genre", "fantasy")
        self.genre_secondary = ""
        self.relationships = {}
        self.xp_ledger = {}
        self.ability_cooldowns = {}
        self.turn = 0
        self.reputation = 0
        self.title = ""
        self.faction = ""


# --- уклонение (ловкость) --------------------------------------------------

def test_dodge_reduces_incoming_damage():
    base = DummyPlayer(agility=0)
    dodgy = DummyPlayer(agility=40)  # 48% уклонения

    assert combat.incoming_damage(dodgy, 30) < combat.incoming_damage(base, 30)


def test_dodge_never_below_one():
    tank = DummyPlayer(agility=1000, vitality=100)
    assert combat.incoming_damage(tank, 1) >= 1


# --- инициатива (ловкость) -------------------------------------------------

def test_initiative_adds_attack():
    slow = DummyPlayer(agility=0, strength=5)
    fast = DummyPlayer(agility=10, strength=5)
    assert combat.attack_power(fast) > combat.attack_power(slow)


# --- крит и меткость (восприятие, удача) ----------------------------------

def test_crit_chance_from_perception_and_luck():
    assert progression.crit_chance(DummyPlayer(perception=0, luck=0)) == 0
    assert progression.crit_chance(DummyPlayer(perception=10, luck=10)) > 0


def test_crit_raises_player_damage():
    plain = DummyPlayer(perception=0, luck=0)
    lucky = DummyPlayer(perception=20, luck=20)

    plain_hit = combat.player_damage(plain, -999)
    lucky_hit = combat.player_damage(lucky, -999)
    assert lucky_hit > plain_hit


def test_accuracy_raises_minimum_damage():
    plain = DummyPlayer(perception=0)
    sharp = DummyPlayer(perception=20)

    plain_low, _ = combat.attack_range(plain)
    sharp_low, _ = combat.attack_range(sharp)
    assert sharp_low > plain_low


# --- производные значения для окна персонажа ------------------------------

def test_derived_stats_shape():
    stats = combat.derived_stats(DummyPlayer())

    for key in (
        "attack", "attack_min", "attack_max", "defense", "max_hp",
        "magic_power", "crit_chance", "crit_bonus", "dodge_chance",
        "accuracy", "initiative", "loot_chance",
    ):
        assert key in stats

    assert stats["attack_min"] <= stats["attack_max"]
    assert stats["dodge_chance"] >= 0


# --- добыча (удача) --------------------------------------------------------

def test_loot_needs_luck():
    assert loot.roll(DummyPlayer(luck=0)) == ""


def test_loot_appears_with_luck():
    player = DummyPlayer(luck=100)  # шанс упирается в потолок 60%
    player.inventory = []
    found = loot.roll(player, rng=random.Random(1))
    assert found
    assert found in loot.loot_for(player.genre)


def test_loot_added_on_combat_win():
    player = DummyPlayer(luck=100)
    player.turn = 0
    from app.services import xp

    _, lines = xp.award_events(
        player,
        [{"type": "combat_win", "result": "success", "tier": "standard", "target": "Гоблин"}],
    )
    # Добыча либо выпала (тогда есть строка и предмет), либо нет — но инвентарь
    # и строки не должны расходиться.
    loot_lines = [line for line in lines if "Добыча" in line]
    if loot_lines:
        assert player.inventory


# --- теги репутации/титула/фракции ----------------------------------------

def test_effects_parse_reputation_title_faction():
    player = DummyPlayer()
    _, effects = llm.parse_effects(
        "Тебя заметили.\n[EFFECTS] REPUTATION: +5, TITLE: Следопыт, FACTION: Лесной союз",
        player,
    )

    assert player.reputation == 5
    assert player.title == "Следопыт"
    assert player.faction == "Лесной союз"
    assert any("Репутация" in e for e in effects)
    assert any("Звание" in e for e in effects)
    assert any("Фракция" in e for e in effects)


def test_raw_reputation_without_wrapper_is_applied():
    player = DummyPlayer()
    text, _ = llm.parse_effects("Тебя хвалят. REPUTATION: -3", player)

    assert player.reputation == -3
    assert "REPUTATION" not in text


def test_campaign_reset_clears_standing():
    player = DummyPlayer()
    player.reputation = 42
    player.title = "Герой"
    player.faction = "Гильдия"

    campaign.start_new_campaign(player, "fantasy")

    assert player.reputation == 0
    assert player.title == ""
    assert player.faction == ""
