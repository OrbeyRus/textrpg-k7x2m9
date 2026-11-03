"""Описания предметов: заметки Мастера Игры и локальные подсказки."""

from app.services import items


class DummyPlayer:
    def __init__(self):
        self.id = 1
        self.name = "Тест"
        self.genre = "fantasy"
        self.inventory = ["Ржавый кинжал", "Факел"]
        self.equipment = {"weapon": "Стальной меч", "helmet": "Кожаный шлем"}
        self.item_notes = {}


def test_known_item_gets_local_description():
    text = items.describe_item("Стальной меч", genre="fantasy")
    assert text
    assert "оружие" in text.lower()


def test_note_overrides_local_description():
    text = items.describe_item("Стальной меч", genre="fantasy", note="Дар старого кузнеца.")
    assert text == "Дар старого кузнеца."


def test_describe_all_covers_bag_and_equipment():
    player = DummyPlayer()
    described = items.describe_all(player)

    assert set(described) == {"Ржавый кинжал", "Факел", "Стальной меч", "Кожаный шлем"}
    assert all(description for description in described.values())


def test_split_note_variants():
    assert items.split_note("Кинжал — бьёт быстро") == ("Кинжал", "бьёт быстро")
    assert items.split_note("Меч (тяжёлый, но прочный)") == ("Меч", "тяжёлый, но прочный")
    assert items.split_note("Факел") == ("Факел", "")


def test_remember_stores_trimmed_note():
    player = DummyPlayer()
    items.remember(player, "  Факел  ", "  Горит долго.  ")
    assert player.item_notes["Факел"] == "Горит долго."


def test_remember_ignores_empty_values():
    player = DummyPlayer()
    items.remember(player, "Факел", "")
    items.remember(player, "", "что-то")
    assert player.item_notes == {}
