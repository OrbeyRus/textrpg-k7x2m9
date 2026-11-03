import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolate_game_logs(tmp_path, monkeypatch):
    """Логи игры в тестах пишутся во временную папку, а не в data/logs."""
    from app.services import gamelog
    monkeypatch.setattr(gamelog, "LOGS_DIR", tmp_path / "logs")
