"""Способности: каталог, изучение, применение и перезарядки.

Сервис работает поверх модели игрока и не обращается к базе напрямую —
сохранение делает вызывающий роутер. Так логику легко тестировать.
"""

import re

from app.content import abilities as catalog
from app.content import genres
from app.services import xp

FIELD_DURATION = 3  # сколько ходов держатся щит и прилив сил


# ---------- базовые помощники ----------

def learned_ids(player) -> list:
    return [str(x) for x in (player.abilities or [])]


def rank_map(player) -> dict:
    return dict(player.ability_ranks or {})


def cooldown_map(player) -> dict:
    return dict(player.ability_cooldowns or {})


def custom_map(player) -> dict:
    return dict(player.custom_abilities or {})


def profile(player) -> dict:
    return genres.profile_for(
        getattr(player, "genre", "") or genres.DEFAULT_GENRE,
        getattr(player, "genre_secondary", "") or None,
    )


def _slug(name: str) -> str:
    return re.sub(r"\W+", "_", (name or "").strip().lower()).strip("_") or "ability"


def custom_ability(player, ability_id: str):
    entry = custom_map(player).get(ability_id)
    if not entry:
        return None
    ability = dict(entry)
    ability.setdefault("cost", ability.get("tier", 2))
    ability.setdefault("value", 0)
    ability.setdefault("growth", 0)
    ability.setdefault("max_rank", 1)
    ability.setdefault("scaling", None)
    ability.setdefault("combat", True)
    ability.setdefault("field", True)
    ability["custom"] = True
    return ability


def resolve(player, key):
    """Находит способность по id или имени: сначала обычный каталог, потом книжные."""
    found = catalog.find(key)
    if found:
        return found
    ability = custom_ability(player, str(key).strip())
    return ability


def is_learned(player, ability) -> bool:
    ids = learned_ids(player)
    return ability["id"] in ids or ability["name"] in ids


def rank_of(player, ability) -> int:
    if not is_learned(player, ability):
        return 0
    return int(rank_map(player).get(ability["id"], 1))


def can_use(player, ability) -> bool:
    return is_learned(player, ability) and cooldown_map(player).get(ability["id"], 0) <= 0


def magnitude(player, ability, rank: int = None) -> int:
    """Сила эффекта с учётом ранга и профильной характеристики."""
    rank = rank or rank_of(player, ability) or 1
    base = ability.get("value", 0) + (rank - 1) * ability.get("growth", 0)
    scaling = ability.get("scaling")
    if scaling:
        base += int(getattr(player, scaling, 0) or 0)
    return int(base)


# ---------- состояние для интерфейса ----------

def _view(player, ability, ids, ranks, cooldowns, source) -> dict:
    learned = ability["id"] in ids or ability["name"] in ids
    max_rank = ability.get("max_rank", 1)
    rank = int(ranks.get(ability["id"], 1 if learned else 0))
    left = int(cooldowns.get(ability["id"], 0))
    return {
        "id": ability["id"],
        "name": ability["name"],
        "description": ability.get("description", ""),
        "tier": ability.get("tier", 1),
        "cost": ability.get("cost", ability.get("tier", 1)),
        "effect": ability.get("effect", ""),
        "cooldown": ability.get("cooldown", 0),
        "cooldown_left": left,
        "max_rank": max_rank,
        "combat": bool(ability.get("combat", True)),
        "field": bool(ability.get("field", False)),
        "learned": learned,
        "rank": rank,
        "maxed": learned and rank >= max_rank,
        "usable": learned and left <= 0,
        "source": source,
        "magnitude": magnitude(player, ability, rank) if learned else 0,
    }


def catalog_view(player) -> list:
    ids = learned_ids(player)
    ranks = rank_map(player)
    cooldowns = cooldown_map(player)

    view = [
        _view(player, ability, ids, ranks, cooldowns, "genre")
        for ability in catalog.pack(profile(player)["ability_pack"])
    ]

    for ability_id in custom_map(player):
        ability = custom_ability(player, ability_id)
        if ability:
            view.append(_view(player, ability, ids, ranks, cooldowns, "book"))

    # Наследие старых сейвов: изученное имя, которого нет в каталоге.
    known = {item["id"] for item in view} | {item["name"] for item in view}
    for entry in ids:
        if entry in known:
            continue
        ability = catalog.find(entry) or custom_ability(player, entry)
        if ability:
            continue
        view.append({
            "id": entry,
            "name": entry,
            "description": "Старая способность из прошлой кампании.",
            "tier": 1,
            "cost": 1,
            "effect": "insight",
            "cooldown": 0,
            "cooldown_left": 0,
            "max_rank": 1,
            "combat": False,
            "field": True,
            "learned": True,
            "rank": 1,
            "maxed": True,
            "usable": int(cooldowns.get(entry, 0)) <= 0,
            "source": "legacy",
            "magnitude": 0,
        })

    return view


# ---------- изучение и открытие ----------

def learn(player, key):
    """Изучает способность или повышает её ранг. Возвращает (успех, текст, view)."""
    ability = resolve(player, key)
    if not ability or ability.get("custom"):
        return False, "Способность недоступна для изучения", None

    learned = is_learned(player, ability)
    rank = rank_of(player, ability)
    max_rank = ability.get("max_rank", 1)
    if learned and rank >= max_rank:
        return False, "Способность уже максимального ранга", None

    cost = ability.get("cost", ability.get("tier", 1))
    if (player.ability_points or 0) < cost:
        return False, "Не хватает очков способностей", None

    # Заменяем возможное старое имя на стабильный id.
    ids = [entry for entry in learned_ids(player) if entry != ability["name"]]
    if ability["id"] not in ids:
        ids.append(ability["id"])
    player.abilities = ids

    ranks = rank_map(player)
    ranks[ability["id"]] = rank + 1
    player.ability_ranks = ranks
    player.ability_points = (player.ability_points or 0) - cost

    view = _view(player, ability, ids, ranks, cooldown_map(player), "genre")
    verb = "Улучшена" if learned else "Изучена"
    return True, f"{verb} способность: {ability['name']}", view


def grant(player, name, description="", effect="insight", tier=2, cooldown=2):
    """Выдаёт книжную способность по сюжету. Возвращает определение или None."""
    name = (name or "").strip()
    if not name:
        return None

    if effect not in catalog.EFFECTS:
        effect = "insight"
    tier = tier if tier in (1, 2, 3) else 2
    ability_id = f"book:{_slug(name)}"

    ability = {
        "id": ability_id,
        "name": name,
        "description": description or "Особый дар, полученный по сюжету.",
        "tier": tier,
        "cost": tier,
        "effect": effect,
        "value": 12 + 4 * tier,
        "growth": 6,
        "cooldown": max(0, int(cooldown)),
        "scaling": None,
        "combat": effect in ("damage", "heal", "guard", "rage", "stealth"),
        "field": effect in ("heal", "insight", "charm", "stealth"),
        "max_rank": 1,
    }

    custom = custom_map(player)
    custom[ability_id] = ability
    player.custom_abilities = custom

    ids = learned_ids(player)
    if ability_id not in ids:
        ids.append(ability_id)
    player.abilities = ids

    ranks = rank_map(player)
    ranks.setdefault(ability_id, 1)
    player.ability_ranks = ranks
    return ability


# ---------- время, перезарядки и статусы ----------

def tick(player) -> None:
    """Уменьшает перезарядки и длительность статусов на один ход."""
    cooldowns = cooldown_map(player)
    new_cooldowns = {}
    for key, value in cooldowns.items():
        left = int(value) - 1
        if left > 0:
            new_cooldowns[key] = left
    if new_cooldowns != cooldowns:
        player.ability_cooldowns = new_cooldowns

    statuses = dict(player.statuses or {})
    new_statuses = {}
    for key, status in statuses.items():
        status = dict(status)
        status["turns"] = int(status.get("turns", 0)) - 1
        if status["turns"] > 0:
            new_statuses[key] = status
    if new_statuses != statuses:
        player.statuses = new_statuses


def set_cooldown(player, ability) -> None:
    cooldown = int(ability.get("cooldown", 0) or 0)
    if cooldown <= 0:
        return
    cooldowns = cooldown_map(player)
    cooldowns[ability["id"]] = cooldown
    player.ability_cooldowns = cooldowns


def set_status(player, key, value, turns=FIELD_DURATION) -> None:
    statuses = dict(player.statuses or {})
    statuses[key] = {"value": int(value), "turns": int(turns)}
    player.statuses = statuses


def _apply_heal(player, value: int, notes: list) -> None:
    """Восстанавливает HP и добавляет строку для интерфейса.

    Если здоровье уже полное, не пишем «Восстановлено 0 HP» — это выглядело как
    сбой, хотя лечение просто нечего было восполнять.
    """
    missing = max(0, player.max_hp - player.hp)
    if missing <= 0:
        notes.append("❤️ Здоровье и так полное")
        return
    amount = min(int(value), missing)
    player.hp = min(player.max_hp, player.hp + amount)
    notes.append(f"❤️ Восстановлено {amount} HP")


# ---------- применение эффектов ----------

def apply_field_effect(player, ability, target: str = "") -> list:
    """Применяет эффект вне боя. Возвращает список строк для интерфейса."""
    effect = ability.get("effect")
    value = magnitude(player, ability)
    notes = []

    if effect == "heal":
        _apply_heal(player, value, notes)
    elif effect == "charm":
        if target:
            bonus, line = xp.bump_relationship(player, target, _tier(ability))
            notes.append(line or f"❤️ Отношения с {target} укрепились")
        else:
            notes.append("💬 Способность помогла расположить собеседника")
    elif effect == "guard":
        set_status(player, "guard", value)
        notes.append(f"🛡️ Щит: поглощает до {value} урона ({FIELD_DURATION} хода)")
    elif effect == "rage":
        set_status(player, "rage", value)
        notes.append(f"🔥 Прилив сил: +{value} к урону ({FIELD_DURATION} хода)")
    elif effect == "stealth":
        notes.append("🌫️ Удалось уйти от опасности незамеченным")
    else:  # insight
        notes.append("🔎 Открылась важная деталь")

    return notes


def apply_combat_effect(player, ability) -> tuple:
    """Применяет эффект в бою. Возвращает (список строк, враг_мертв)."""
    effect = ability.get("effect")
    value = magnitude(player, ability)
    notes = []
    killed = False

    if effect == "damage":
        enemy = dict(player.enemy or {})
        enemy["hp"] = max(0, int(enemy.get("hp", 0)) - value)
        notes.append(f"⚔️ Урон врагу: {value} HP")
        if enemy["hp"] <= 0:
            notes.append(f"💀 Враг {enemy.get('name', 'Враг')} повержен!")
            player.enemy = {}
            killed = True
        else:
            player.enemy = enemy
    elif effect == "heal":
        _apply_heal(player, value, notes)
    elif effect == "guard":
        set_status(player, "guard", value)
        notes.append(f"🛡️ Щит: поглощает до {value} урона ({FIELD_DURATION} хода)")
    elif effect == "rage":
        set_status(player, "rage", value)
        notes.append(f"🔥 Прилив сил: +{value} к урону ({FIELD_DURATION} хода)")
    elif effect == "stealth":
        enemy_name = (player.enemy or {}).get("name", "Враг")
        player.enemy = {}
        notes.append(f"🌫️ Вы скрылись от {enemy_name}")
        killed = False
    else:
        notes.append("✨ Способность применилась")

    return notes, killed


def _tier(ability) -> str:
    return {1: "standard", 2: "major", 3: "epic"}.get(ability.get("tier", 1), "standard")


# ---------- разбор сюжетных тегов ----------

UNLOCK_RE = re.compile(
    r"\[ABILITY_UNLOCK\]\s*(.*?)(?=\n\[|\Z)", re.IGNORECASE | re.DOTALL
)


def parse_unlock_line(line: str) -> dict:
    data = {}
    for part in re.split(r",\s*", line.strip()):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        data[key.strip().lower()] = value.strip().strip('"').strip("'")
    return data


def extract_unlocks(text: str) -> tuple:
    """Вынимает теги [ABILITY_UNLOCK]. Возвращает (списки параметров, очищенный текст)."""
    unlocks = [parse_unlock_line(match) for match in UNLOCK_RE.findall(text)]
    cleaned = UNLOCK_RE.sub("", text)
    return [u for u in unlocks if u.get("name")], cleaned
