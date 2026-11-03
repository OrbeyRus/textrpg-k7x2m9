from app.services import combat, llm, progression, xp


class DummyPlayer:
    def __init__(self, genre="universal"):
        self.level = 1
        self.xp = 0
        self.next_level_xp = progression.xp_to_next(1)
        self.hp = 100
        self.max_hp = 100
        self.vitality = 5
        self.stat_points = 0
        self.ability_points = 0
        self.inventory = []
        self.equipment = {}
        self.quests = []
        self.location = "Неизвестно"
        self.enemy = {"name": "Гоблин", "hp": 30, "max_hp": 30}
        self.abilities = []
        self.genre = genre
        self.genre_secondary = ""
        self.relationships = {}
        self.xp_ledger = {}
        self.ability_cooldowns = {}
        self.turn = 0


def test_enemy_damage_does_not_hurt_player():
    player = DummyPlayer()
    enemy_max_hp = player.enemy["max_hp"]
    _, effects = llm.parse_effects("Удар.\n[EFFECTS] ENEMY_HP: -10, HP: -5", player)

    # Урон врагу зажат сервером в диапазон атаки игрока.
    low, high = combat.attack_range(player)
    assert low <= enemy_max_hp - player.enemy["hp"] <= high
    # ENEMY_HP не задевает игрока: он получает серверный ответный удар, а не «5».
    assert player.hp == player.max_hp - combat.incoming_damage(player, enemy_max_hp)
    assert any("Урон врагу" in e for e in effects)


def test_raw_effects_without_wrapper_are_applied_and_stripped():
    player = DummyPlayer()
    text, effects = llm.parse_effects(
        "Ты бьёшь изо всех сил. ENEMY_HP: -10 HP: -8 ENEMY_DEAD ITEM: Клык тени",
        player,
    )

    assert "ENEMY_HP" not in text
    assert "ENEMY_DEAD" not in text
    assert "ITEM:" not in text
    assert "Клык тени" in player.inventory
    assert player.enemy == {}


def test_kill_turn_still_uses_server_incoming_damage():
    player = DummyPlayer()
    enemy_max = player.enemy["max_hp"]

    # Враг погибает в этом же ходу, но урон игроку всё равно серверный,
    # а не «-999» от модели.
    _, effects = llm.parse_effects(
        "Добиваю врага.\n[EFFECTS] ENEMY_HP: -999, ENEMY_DEAD, HP: -999", player
    )

    assert player.enemy == {}
    assert player.hp == player.max_hp - combat.incoming_damage(player, enemy_max)


def test_event_awards_xp_and_triggers_level_up():
    player = DummyPlayer()
    player.xp = 90

    _, effects = llm.parse_effects(
        "Открытие.\n[EFFECTS] NONE\n[EVENT] type=discovery, result=success, tier=standard, target=\"мельница\"",
        player,
    )

    assert player.xp == 10
    assert player.level == 2
    assert player.stat_points == 3
    assert any("Уровень 2" in e for e in effects)


def test_combat_win_scales_with_enemy_hp():
    player = DummyPlayer()
    _, effects = llm.parse_effects(
        "Победа.\n[EFFECTS] ENEMY_DEAD\n[EVENT] type=combat_win, result=success, tier=standard, target=\"Гоблин\"",
        player,
    )
    assert player.xp > 0
    assert any("Победа" in e for e in effects)


def test_combat_win_clears_enemy_without_enemy_dead():
    player = DummyPlayer()
    _, effects = llm.parse_effects(
        "Победа.\n[EFFECTS] NONE\n[EVENT] type=combat_win, result=success, tier=standard, target=\"Гоблин\"",
        player,
    )
    assert player.enemy == {}
    assert any("повержен" in e for e in effects)


def test_start_does_not_award_xp():
    player = DummyPlayer()
    _, effects = llm.parse_effects(
        "Начало.\n[EFFECTS] NONE\n[EVENT] type=discovery, result=success, tier=standard, target=\"дом\"",
        player,
        allow_xp=False,
    )
    assert player.xp == 0
    assert not any("XP" in e for e in effects)


def test_missing_event_infers_discovery_on_location_change():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Ты идёшь дальше.\n[EFFECTS] LOCATION: Тёмный лес", player)

    assert player.xp > 0
    assert any("Открытие" in e for e in effects)


def test_missing_event_infers_combat_win_when_enemy_dies():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Враг рассыпался.\n[EFFECTS] ENEMY_DEAD", player)

    assert player.enemy == {}
    assert any("Победа" in e for e in effects)


def test_missing_event_without_change_gives_no_xp():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Ты просто стоишь.\n[EFFECTS] NONE", player)

    assert player.xp == 0


def test_rag_empty_book_returns_fallback():
    from app.services import rag

    assert rag.get_relevant_context([], "что угодно") == "Информация о мире недоступна."


def test_repeated_event_loses_value():
    player = DummyPlayer()
    event = [{"type": "social", "result": "success", "tier": "standard", "target": "Марта"}]

    first, _ = xp.award_events(player, event)
    player.turn += 1  # новая сцена/ход
    player.xp_ledger = {k: v for k, v in player.xp_ledger.items() if not k.startswith("scene")}
    second, _ = xp.award_events(player, event)

    assert first > 0
    assert second < first


def test_failed_fight_gives_no_xp():
    player = DummyPlayer()
    gained, _ = xp.award_events(
        player,
        [{"type": "combat_win", "result": "fail", "tier": "standard", "target": "Гоблин"}],
    )
    assert gained == 0


def test_legacy_xp_is_clamped():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Мега-победа.\n[EFFECTS] XP: +1000", player)

    assert player.xp <= xp.LEGACY_XP_MAX_PER_TURN
    assert player.level == 1


def test_relationship_grows_stage():
    player = DummyPlayer(genre="romance")
    event = [{"type": "relationship", "result": "success", "tier": "epic", "target": "Марта"}]

    xp.award_events(player, event)
    assert player.relationships["Марта"]["value"] >= 5
    assert player.relationships["Марта"]["stage"] >= 1
