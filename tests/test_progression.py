from app.services import progression


def test_xp_curve_is_strictly_growing():
    values = [progression.xp_to_next(level) for level in range(1, 20)]
    assert values[0] == 100
    assert all(b > a for a, b in zip(values, values[1:]))


def test_level_rewards_grow():
    assert progression.stat_points_for_level(1) == 3
    assert progression.stat_points_for_level(6) == 4
    assert progression.ability_points_for_level(1) == 1
    assert progression.ability_points_for_level(4) == 2


def test_attack_scales_with_strength():
    assert progression.attack_power(10) > progression.attack_power(5)
