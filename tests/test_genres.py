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
