"""Журнал игры: папка на игрока, jsonl и читаемый лог."""

import json

from app.services import gamelog


class DummyPlayer:
    def __init__(self, player_id=7, name="Андрей"):
        self.id = player_id
        self.name = name
        self.hp = 80
        self.max_hp = 100
        self.level = 3
        self.xp = 40
        self.location = "Тёмный лес"
        self.inventory = ["Факел"]
        self.equipment = {"weapon": "Меч"}
        self.enemy = {}
        self.quests = []


def _use_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(gamelog, "LOGS_DIR", tmp_path)


def test_safe_name_sanitizes_bad_characters():
    assert gamelog.safe_name("Андрей") == "Андрей"
    assert gamelog.safe_name('a/b:c*?"<>|') == "a_b_c______"
    assert gamelog.safe_name("   ") == "player"


def test_log_turn_writes_jsonl_and_readable_log(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    player = DummyPlayer()

    gamelog.log_turn(
        player,
        "story",
        action="Осматриваюсь",
        raw="Ты видишь лес.\n[EFFECTS] NONE",
        text="Ты видишь лес.",
        effects=["👀 Осмотр"],
    )

    directory = tmp_path / "Андрей_7"
    assert directory.is_dir()

    entries = [json.loads(line) for line in (directory / "game.jsonl").read_text("utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["kind"] == "story"
    assert entries[0]["action"] == "Осматриваюсь"
    assert entries[0]["state"]["hp"] == 80

    readable = (directory / "game.log").read_text("utf-8")
    assert "Осматриваюсь" in readable
    assert "Ты видишь лес." in readable
    assert "Сырой ответ LLM" in readable  # сырой ответ отличается от разобранного


def test_log_note_writes_message(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    player = DummyPlayer()

    gamelog.log_note(player, "reset", "Кампания сброшена")

    directory = tmp_path / "Андрей_7"
    assert (directory / "game.log").read_text("utf-8").count("Кампания сброшена") == 1


def test_story_play_file_collects_session(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    player = DummyPlayer()

    gamelog.log_turn(player, "story", action="Осматриваюсь", raw="сырое", text="Ты видишь лес.")
    gamelog.log_turn(player, "combat_action", action="Атакую врага", raw="сырое", text="Ты бьёшь гоблина.")

    story = (tmp_path / "Андрей_7" / "story.md").read_text(encoding="utf-8")
    assert story.startswith("# Андрей")
    assert "**Игрок:** Осматриваюсь" in story
    assert "**Мастер:** Ты видишь лес." in story
    assert "**Игрок:** Атакую врага" in story
    assert "**Мастер:** Ты бьёшь гоблина." in story


def test_story_marker_on_reset(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)
    player = DummyPlayer()

    gamelog.log_turn(player, "story", action="Иду", text="Ты идёшь.")
    gamelog.log_note(player, "reset", "Кампания сброшена")

    story = (tmp_path / "Андрей_7" / "story.md").read_text(encoding="utf-8")
    assert "Сброс кампании" in story
    assert "Кампания сброшена" in story


def test_legacy_folder_is_renamed_to_current_name(monkeypatch, tmp_path):
    _use_tmp(monkeypatch, tmp_path)

    legacy = tmp_path / "player_7"
    legacy.mkdir()
    (legacy / "game.log").write_text("старый лог", encoding="utf-8")

    player = DummyPlayer(name="Андрей")
    gamelog.log_turn(player, "story", text="привет")

    target = tmp_path / "Андрей_7"
    assert target.is_dir()
    assert not legacy.exists()
    assert "старый лог" in (target / "game.log").read_text("utf-8")


def test_logging_failure_does_not_raise(monkeypatch, tmp_path):
    # Путь, который нельзя создать как папку: уже занят файлом.
    blocker = tmp_path / "Андрей_7"
    blocker.write_text("я файл", encoding="utf-8")
    _use_tmp(monkeypatch, tmp_path)

    gamelog.log_turn(DummyPlayer(), "story", text="привет")  # не должно бросить
