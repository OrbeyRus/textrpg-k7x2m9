"""Старт новой кампании.

Новая книга = новый герой и новая история: прогресс, инвентарь, отношения
и способности сбрасываются, а к жанру применяется стартовый набор.
"""

from app.content import genres
from app.services import progression


def start_new_campaign(player, primary_genre: str, secondary_genre: str | None = None) -> dict:
    """Сбрасывает кампанию игрока под выбранный жанр. Возвращает профиль жанра."""
    profile = genres.profile_for(primary_genre, secondary_genre)

    player.level = progression.START_LEVEL
    player.xp = 0
    player.next_level_xp = progression.xp_to_next(progression.START_LEVEL)

    player.strength = 5
    player.agility = 5
    player.vitality = 5
    player.intelligence = 5
    player.perception = 5
    player.luck = 5

    player.max_hp = 100
    player.hp = 100
    player.stat_points = progression.START_STAT_POINTS
    player.ability_points = progression.START_ABILITY_POINTS

    player.inventory = list(profile["starting_inventory"])
    player.equipment = dict(profile["starting_equipment"])
    player.abilities = []
    player.quests = []
    player.history = []
    player.location = "Неизвестно"
    player.enemy = {}

    player.genre = profile["code"]
    player.genre_secondary = profile["secondary"] or ""
    player.genre_weights = profile["event_weights"]
    player.relationships = {}
    player.xp_ledger = {}
    player.ability_cooldowns = {}
    player.ability_ranks = {}
    player.custom_abilities = {}
    player.statuses = {}
    player.turn = 0

    return profile
