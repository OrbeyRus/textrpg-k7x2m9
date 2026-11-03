from app.services import abilities, combat, llm, progression


class DummyPlayer:
    def __init__(self, genre="fantasy"):
        self.name = "Тест"
        self.level = 1
        self.xp = 0
        self.next_level_xp = progression.xp_to_next(1)
        self.hp = 50
        self.max_hp = 100
        self.strength = 5
        self.agility = 5
        self.vitality = 5
        self.intelligence = 5
        self.perception = 5
        self.luck = 5
        self.stat_points = 0
        self.ability_points = 5
        self.inventory = []
        self.equipment = {}
        self.quests = []
        self.location = "Лес"
        self.enemy = {"name": "Гоблин", "hp": 30, "max_hp": 30}
        self.abilities = []
        self.genre = genre
        self.genre_secondary = ""
        self.relationships = {}
        self.xp_ledger = {}
        self.ability_cooldowns = {}
        self.ability_ranks = {}
        self.custom_abilities = {}
        self.statuses = {}
        self.turn = 0


def test_catalog_shows_genre_pack_locked():
    player = DummyPlayer("fantasy")
    view = abilities.catalog_view(player)
    names = [a["name"] for a in view]
    assert "Огненный шар" in names
    assert all(not a["learned"] for a in view)
    assert all(a["source"] == "genre" for a in view)


def test_learn_spends_points_and_raises_rank():
    player = DummyPlayer("fantasy")

    ok, message, view = abilities.learn(player, "power_strike")
    assert ok
    assert player.ability_points == 4
    assert view["learned"] and view["rank"] == 1

    ok, _, view = abilities.learn(player, "Мощный удар")  # поиск по имени
    assert ok
    assert view["rank"] == 2
    assert player.ability_points == 3


def test_learn_respects_max_rank():
    player = DummyPlayer("fantasy")
    for _ in range(3):
        ok, _, _ = abilities.learn(player, "power_strike")
        assert ok

    ok, message, _ = abilities.learn(player, "power_strike")
    assert not ok
    assert "ранг" in message.lower()


def test_learn_fails_without_points():
    player = DummyPlayer("fantasy")
    player.ability_points = 0
    ok, message, _ = abilities.learn(player, "fireball")
    assert not ok
    assert "очк" in message.lower()


def test_book_ability_is_granted_and_visible():
    player = DummyPlayer("fantasy")
    granted = abilities.grant(player, "Дар пламени", effect="damage", tier=3)

    assert granted["id"] == "book:дар_пламени"
    view = abilities.catalog_view(player)
    book = [a for a in view if a["source"] == "book"]
    assert len(book) == 1
    assert book[0]["learned"] is True
    assert book[0]["name"] == "Дар пламени"


def test_cooldown_tick():
    player = DummyPlayer("fantasy")
    abilities.learn(player, "fireball")
    fireball = abilities.resolve(player, "fireball")
    abilities.set_cooldown(player, fireball)

    assert not abilities.can_use(player, fireball)
    assert player.ability_cooldowns[fireball["id"]] == fireball["cooldown"]

    abilities.tick(player)
    abilities.tick(player)
    assert abilities.can_use(player, fireball)


def test_combat_damage_can_kill_enemy():
    player = DummyPlayer("fantasy")
    player.enemy = {"name": "Крыса", "hp": 10, "max_hp": 10}
    abilities.learn(player, "power_strike")
    strike = abilities.resolve(player, "power_strike")

    notes, killed = abilities.apply_combat_effect(player, strike)
    assert player.enemy == {}
    assert killed
    assert any("повержен" in n for n in notes)


def test_guard_reduces_incoming_damage():
    player = DummyPlayer("fantasy")
    player.statuses = {"guard": {"value": 8, "turns": 2}}

    hp_before = player.hp
    incoming = combat.incoming_damage(player, player.enemy["max_hp"])
    _, effects = llm.parse_effects("Удар.\n[EFFECTS] HP: -20", player)

    # Число «-20» от LLM заменяется серверным уроном, щит гасит 8 из него.
    assert player.hp == hp_before - (incoming - 8)
    assert any("Щит поглотил 8" in e for e in effects)


def test_rage_increases_outgoing_damage():
    calm = DummyPlayer("fantasy")
    llm.parse_effects("Выпад.\n[EFFECTS] ENEMY_HP: -10", calm)

    raging = DummyPlayer("fantasy")
    raging.statuses = {"rage": {"value": 7, "turns": 2}}
    llm.parse_effects("Выпад.\n[EFFECTS] ENEMY_HP: -10", raging)

    calm_damage = calm.enemy["max_hp"] - calm.enemy["hp"]
    rage_damage = raging.enemy["max_hp"] - raging.enemy["hp"]
    assert rage_damage > calm_damage


def test_ability_unlock_tag_grants_ability():
    player = DummyPlayer("universal")
    _, effects = llm.parse_effects(
        'Ты чувствуешь силу.\n[ABILITY_UNLOCK] name="Шёпот ветра", effect=insight, tier=2',
        player,
    )
    assert any("Шёпот ветра" in n for n in effects)
    assert any(a["id"] == "book:шёпот_ветра" for a in abilities.catalog_view(player))


def test_field_heal_restores_hp():
    player = DummyPlayer("romance")
    abilities.learn(player, "support")
    support = abilities.resolve(player, "support")

    abilities.apply_field_effect(player, support)
    assert player.hp > 50


def test_charm_field_effect_bumps_relationship():
    player = DummyPlayer("romance")
    abilities.learn(player, "warm_word")
    charm = abilities.resolve(player, "warm_word")

    abilities.apply_field_effect(player, charm, target="Марта")
    assert player.relationships["Марта"]["value"] >= 1
