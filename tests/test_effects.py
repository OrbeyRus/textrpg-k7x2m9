from app.services import llm, progression


class DummyPlayer:
    def __init__(self):
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


def test_enemy_damage_does_not_hurt_player():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Удар.\n[EFFECTS] ENEMY_HP: -10, HP: -5", player)

    assert player.enemy["hp"] == 20
    assert player.hp == 95
    assert any("Урон врагу" in e for e in effects)


def test_xp_triggers_level_up_and_rewards():
    player = DummyPlayer()
    _, effects = llm.parse_effects("Победа.\n[EFFECTS] XP: +120", player)

    assert player.level == 2
    assert player.xp == 20
    assert player.next_level_xp == 180
    assert player.stat_points == 3
    assert player.ability_points == 1
    assert any("Уровень 2" in e for e in effects)


def test_effects_none_keeps_state():
    player = DummyPlayer()
    hp_before, xp_before = player.hp, player.xp
    _, effects = llm.parse_effects("Ты осматриваешься.\n[EFFECTS] NONE", player)

    assert player.hp == hp_before
    assert player.xp == xp_before
    assert effects == []
