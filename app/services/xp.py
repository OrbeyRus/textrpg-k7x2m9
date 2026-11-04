"""Опыт от действий.

LLM описывает, что произошло, тегом [EVENT], а сервер сам считает опыт:
учитывает сложность, жанровые веса, повторяемость и бюджет сцены.
"""

from app.content import genres
from app.services import loot

BASE_XP = 10          # опыт за обычное событие на 1 уровне
LEVEL_STEP = 3        # прибавка за каждый уровень игрока

TIER_MULT = {
    "minor": 1,
    "standard": 2,
    "major": 3,
    "epic": 5,
}

# Множитель за повтор одного и того же действия: 6-й раз и далее — 0.
REPEAT_MULTIPLIERS = [1.0, 0.6, 0.4, 0.25, 0.1]

SCENE_BUDGET = 4               # сколько оплачиваемых событий на одну локацию
MAX_REWARDED_PER_TURN = 1      # сверх этого платят только вехи и квесты
LEGACY_XP_MAX_PER_TURN = 60    # страховка для старого тега XP:

RELATIONSHIP_STAGES = [3, 6, 10, 15]
RELATIONSHIP_BONUS_MULT = 2

EVENT_LABELS = {
    "combat_win": "Победа",
    "obstacle": "Преодоление",
    "discovery": "Открытие",
    "social": "Разговор",
    "relationship": "Сближение",
    "quest": "Квест",
    "growth": "Развитие",
    "risk": "Риск",
    "milestone": "Веха",
}

# События, которые платят даже при исчерпанном бюджете сцены.
FREE_EVENTS = {"milestone", "quest"}


def normalize_tier(tier: str | None) -> str:
    if tier and tier in TIER_MULT:
        return tier
    return "minor"


def base_xp(level: int) -> int:
    return BASE_XP + LEVEL_STEP * (max(1, int(level)) - 1)


def _novelty(count: int) -> float:
    if count < len(REPEAT_MULTIPLIERS):
        return REPEAT_MULTIPLIERS[count]
    return 0.0


def award_events(player, events: list, context: dict | None = None) -> tuple:
    """Начисляет опыт за события. Возвращает (сумма опыта, список строк для UI)."""
    if not events:
        return 0, []

    context = context or {}
    profile = genres.profile_for(
        player.genre or genres.DEFAULT_GENRE,
        player.genre_secondary or None,
    )
    weights = profile["event_weights"]

    ledger = dict(player.xp_ledger or {})
    turn = (player.turn or 0) + 1
    player.turn = turn

    scene_key = f"scene|{player.location}"
    scene_count = ledger.get(scene_key, {}).get("count", 0)

    total = 0
    rewarded = 0
    lines = []

    for event in events:
        event_type = (event.get("type") or "").strip().lower()
        if event_type not in EVENT_LABELS:
            continue

        tier = normalize_tier(event.get("tier"))
        target = (event.get("target") or "").strip()
        result = (event.get("result") or "success").strip().lower()

        key = f"{event_type}|{target.lower() or event_type}"
        count = ledger.get(key, {}).get("count", 0)
        novelty = _novelty(count)

        # Бюджет сцены и лимит награды за ход
        if event_type not in FREE_EVENTS:
            if scene_count >= SCENE_BUDGET:
                novelty = 0.0
            elif rewarded >= MAX_REWARDED_PER_TURN:
                novelty = 0.0

        # Провал не даёт награды за победу, но может дать опыт ошибки.
        if result == "fail":
            if event_type in ("growth", "risk"):
                novelty *= 0.3
            else:
                novelty = 0.0

        gain = 0
        if novelty > 0:
            if event_type == "combat_win" and context.get("enemy_max_hp"):
                gain = (12 + 0.5 * context["enemy_max_hp"]) * weights.get(event_type, 1.0) * novelty
            else:
                gain = base_xp(player.level) * TIER_MULT[tier] * weights.get(event_type, 1.0) * novelty
            gain = int(round(gain))

        ledger[key] = {"count": count + 1, "turn": turn}

        if gain > 0:
            total += gain
            rewarded += 1
            if event_type not in FREE_EVENTS:
                scene_count += 1

            label = EVENT_LABELS[event_type]
            suffix = f": {target}" if target else ""
            repeat_note = f" (повтор ×{novelty:g})" if novelty < 1 else ""
            lines.append(f"✨ +{gain} XP · {label}{suffix}{repeat_note}")

        # Отношения с персонажем
        if event_type == "relationship" and target and result != "fail":
            bonus, bonus_line = _bump_relationship(player, target, tier, weights, profile)
            total += bonus
            if bonus_line:
                lines.append(bonus_line)

        # Удача: после победы можно найти что-то полезное сверх сюжетного.
        if event_type == "combat_win" and result != "fail":
            found = loot.roll(player)
            if found:
                inventory = list(player.inventory or [])
                inventory.append(found)
                player.inventory = inventory
                lines.append(f"🎁 Добыча: {found}")

    ledger[scene_key] = {"count": scene_count, "turn": turn}
    player.xp_ledger = ledger

    if total > 0:
        player.xp += total
        gained_levels = _apply_levels(player, profile)
        lines.extend(gained_levels)

    return total, lines


def bump_relationship(player, target: str, tier: str = "standard") -> tuple:
    """Публичная обёртка: развивает отношения с персонажем. Возвращает (бонус, строка)."""
    if not target:
        return 0, ""
    profile = genres.profile_for(
        player.genre or genres.DEFAULT_GENRE,
        player.genre_secondary or None,
    )
    return _bump_relationship(player, target, normalize_tier(tier), profile["event_weights"], profile)


def _bump_relationship(player, target: str, tier: str, weights: dict, profile: dict) -> tuple:
    """Повышает значение отношений и возвращает бонус за новый этап."""
    relationships = dict(player.relationships or {})
    entry = dict(relationships.get(target) or {"value": 0})
    old_value = int(entry.get("value", 0))
    new_value = old_value + TIER_MULT[tier]

    entry["value"] = new_value
    entry["stage"] = sum(1 for threshold in RELATIONSHIP_STAGES if new_value >= threshold)
    relationships[target] = entry
    player.relationships = relationships

    crossed = any(old_value < threshold <= new_value for threshold in RELATIONSHIP_STAGES)
    if not crossed:
        return 0, ""

    bonus = int(round(base_xp(player.level) * RELATIONSHIP_BONUS_MULT * weights.get("relationship", 1.0)))
    return bonus, f"❤️ Отношения с {target}: новый этап (+{bonus} XP)"


def _apply_levels(player, profile: dict) -> list:
    from app.services import progression

    lines = []
    for new_level in progression.apply_level_up(player):
        lines.append(
            f"🆙 Уровень {new_level}! "
            f"+{progression.stat_points_for_level(new_level)} очк. характеристик, "
            f"+{progression.ability_points_for_level(new_level)} очк. способностей"
        )
    return lines


def clamp_legacy_xp(value: int) -> int:
    """Ограничивает старый тег XP:, чтобы LLM не выдал «+1000»."""
    if value <= 0:
        return 0
    return min(value, LEGACY_XP_MAX_PER_TURN)
