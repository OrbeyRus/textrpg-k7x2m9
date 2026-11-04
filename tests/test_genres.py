from app.content import genres
from app.services import campaign, progression


class DummyPlayer:
    pass


def test_all_genres_have_labels_and_weights():
    listed = genres.public_list()
    assert len(listed) == len(genres.GENRE_ORDER)
    for item in listed:
        assert item["stat_labels"]["strength"]
        assert genres.blended_weights(item["code"])["combat_win"] > 0


def test_romance_weights_favor_relationships():
    romance = genres.blended_weights("romance")
    fantasy = genres.blended_weights("fantasy")
    assert romance["relationship"] > fantasy["relationship"]
    assert romance["combat_win"] < fantasy["combat_win"]


def test_secondary_genre_blends_weights():
    pure = genres.blended_weights("romance")
    mixed = genres.blended_weights("romance", "mystery")
    assert mixed["discovery"] > pure["discovery"]


def test_romance_renames_perception_to_empathy():
    profile = genres.profile_for("romance")
    assert profile["stat_labels"]["perception"] == "Эмпатия"


def test_new_campaign_resets_player_and_applies_kit():
    player = DummyPlayer()
    profile = campaign.start_new_campaign(player, "fantasy")

    assert profile["code"] == "fantasy"
    assert player.level == progression.START_LEVEL
    assert player.stat_points == progression.START_STAT_POINTS
    assert player.ability_points == progression.START_ABILITY_POINTS
    assert player.genre == "fantasy"
    assert player.genre_weights["combat_win"] == profile["event_weights"]["combat_win"]
    assert player.equipment.get("weapon") == "Кинжал"
    assert "Факел" in player.inventory
    assert player.history == []
    assert player.turn == 0


def test_unknown_genre_falls_back_to_universal():
    assert genres.normalize("nonsense") == "universal"
    assert genres.get("nonsense")["code"] == "universal"


def test_all_genres_describe_every_stat():
    from app.services.progression import STAT_KEYS

    for code in genres.GENRE_ORDER:
        labels = genres.labels_for(code)
        descriptions = genres.descriptions_for(code)
        for key in STAT_KEYS:
            assert labels.get(key), (code, key)
            assert descriptions.get(key), (code, key)
            # Пояснение должно называть характеристику так же, как её видит игрок.
            assert labels[key] in descriptions[key], (code, key)


def test_historical_intelligence_explains_abilities():
    profile = genres.profile_for("historical")
    text = profile["stat_descriptions"]["intelligence"]

    assert "Образованность" in text
    assert "способност" in text


def test_public_list_includes_stat_descriptions():
    for item in genres.public_list():
        assert item["stat_descriptions"]["strength"]
        assert item["stat_descriptions"]["vitality"]


def test_combat_hint_reflects_intensity():
    fantasy = genres.profile_for("fantasy")   # high
    romance = genres.profile_for("romance")   # low
    assert fantasy["combat_hint"]
    assert romance["combat_hint"]
    assert fantasy["combat_hint"] != romance["combat_hint"]
