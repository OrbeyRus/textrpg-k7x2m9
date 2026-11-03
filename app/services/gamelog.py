"""Автосохранение полного лога игры по каждому персонажу.

Для каждого игрока создаётся подпапка ``data/logs/{имя}_{id}/``, в которой
ведутся три файла:

* ``game.jsonl`` — машиночитаемые записи, по одной JSON-строке на событие;
* ``game.log``   — тот же ход человекочитаемым текстом;
* ``story.md``   — связная «пьеса» сессии: только действия игрока и ответы
  Мастера, без служебных тегов, — удобно читать историю целиком.

Лог нужен, чтобы разбирать сюжетные несоответствия и ошибки движка: в него
попадает сырой ответ LLM, разобранный текст, эффекты и состояние игрока.

Логирование намеренно «безопасное»: любые ошибки записи глотаются, чтобы
проблема с диском никогда не ломала саму игру.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import LOGS_DIR

# Символы, недопустимые в имени папки Windows (плюс управляющие).
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_NAME_LEN = 40


def safe_name(name: str) -> str:
    """Превращает имя персонажа в безопасное имя папки."""
    cleaned = _BAD_CHARS.sub("_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:_MAX_NAME_LEN] or "player"


def player_dir(player) -> Path:
    """Папка логов конкретного персонажа: ``{имя}_{id}``."""
    return LOGS_DIR / f"{safe_name(getattr(player, 'name', ''))}_{getattr(player, 'id', 0)}"


def _state(player) -> dict:
    return {
        "hp": getattr(player, "hp", None),
        "max_hp": getattr(player, "max_hp", None),
        "level": getattr(player, "level", None),
        "xp": getattr(player, "xp", None),
        "location": getattr(player, "location", None),
        "inventory": list(getattr(player, "inventory", None) or []),
        "equipment": dict(getattr(player, "equipment", None) or {}),
        "enemy": dict(getattr(player, "enemy", None) or {}),
        "quests": list(getattr(player, "quests", None) or []),
    }


def _ensure_dir(player) -> Path:
    """Возвращает папку игрока, перенося прежнюю папку под новое имя.

    Имя персонажа может смениться позже создания логов — тогда содержимое
    прежней папки ``player_{id}`` (или старого имени) переносится под новое.
    """
    directory = player_dir(player)
    directory.mkdir(parents=True, exist_ok=True)

    player_id = getattr(player, "id", 0)
    for sibling in LOGS_DIR.glob(f"*_{player_id}"):
        if sibling == directory or not sibling.is_dir():
            continue
        try:
            for child in sibling.iterdir():
                child.replace(directory / child.name)
            sibling.rmdir()
        except OSError:
            pass

    return directory


def _write(player, entry: dict) -> None:
    try:
        directory = _ensure_dir(player)
        with (directory / "game.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        with (directory / "game.log").open("a", encoding="utf-8") as handle:
            handle.write(_render(entry))
        _append_story(directory, player, entry)
    except Exception:  # noqa: BLE001 — логи не должны ломать игру
        pass


# Ходы, которые попадают в связный текст пьесы, и события-разделители.
_STORY_KINDS = {"story", "combat_action", "combat_ability", "ability_use"}
_STORY_MARKERS = {
    "reset": "Сброс кампании",
    "new_game": "Новая игра",
    "book": "Новая книга",
}


def _append_story(directory: Path, player, entry: dict) -> None:
    """Дописывает ход в файл-«пьесу» ``story.md`` — связный сюжет сессии."""
    kind = entry.get("kind")
    lines = []

    if kind in _STORY_KINDS:
        if entry.get("action"):
            lines.append(f"**Игрок:** {entry['action'].strip()}")
        if entry.get("text"):
            lines.append(f"**Мастер:** {entry['text'].strip()}")
    elif kind in _STORY_MARKERS:
        lines.append(f"> **{_STORY_MARKERS[kind]}**")
        if entry.get("message"):
            lines.append(f"> {entry['message']}")

    if not lines:
        return

    path = directory / "story.md"
    if not path.exists():
        title = getattr(player, "name", "") or "Безымянный герой"
        header = f"# {title} (id {getattr(player, 'id', 0)}) — история приключения\n\n"
        path.write_text(header, encoding="utf-8")

    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n\n".join(lines) + "\n\n---\n\n")


def _render(entry: dict) -> str:
    name = entry.get("name") or "?"
    header = f"[{entry.get('ts', '')}] === {entry.get('kind', '?')} · {name} (id {entry.get('player_id')}) ==="
    lines = [header]

    if entry.get("action"):
        lines.append(f"Игрок: {entry['action']}")

    raw = entry.get("raw") or ""
    text = entry.get("text") or ""
    if raw and raw.strip() != text.strip():
        lines.append(f"Сырой ответ LLM:\n{raw.strip()}")
    if text.strip():
        lines.append(f"Мастер: {text.strip()}")

    if entry.get("effects"):
        lines.append("Эффекты: " + ", ".join(str(effect) for effect in entry["effects"]))

    if entry.get("message"):
        lines.append(str(entry["message"]))

    state = entry.get("state") or {}
    if state:
        lines.append(
            "Состояние: HP {hp}/{max_hp}, уровень {level}, xp {xp}, локация {location}\n"
            "  рюкзак: {inventory}\n"
            "  надето: {equipment}\n"
            "  враг: {enemy}".format(**state)
        )

    return "\n".join(lines) + "\n\n"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_turn(
    player,
    kind: str,
    *,
    action: str = "",
    raw: str = "",
    text: str = "",
    effects=None,
    extra: dict | None = None,
) -> None:
    """Пишет один ход: действие, ответы LLM и состояние после него."""
    entry = {
        "ts": _now(),
        "kind": kind,
        "player_id": getattr(player, "id", 0),
        "name": getattr(player, "name", ""),
        "action": action or "",
        "raw": raw or "",
        "text": text or "",
        "effects": list(effects or []),
        "state": _state(player),
    }
    if extra:
        entry.update(extra)
    _write(player, entry)


def log_note(player, kind: str, message: str, *, extra: dict | None = None) -> None:
    """Пишет служебное событие: создание героя, сброс, загрузка книги и т.п."""
    entry = {
        "ts": _now(),
        "kind": kind,
        "player_id": getattr(player, "id", 0),
        "name": getattr(player, "name", ""),
        "message": message,
        "state": _state(player),
    }
    if extra:
        entry.update(extra)
    _write(player, entry)
