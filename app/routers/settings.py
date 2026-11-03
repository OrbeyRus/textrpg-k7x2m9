"""Настройки игры: провайдер ИИ, ключ, звук, обновления."""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import APP_VERSION
from app.services import settings_store
from app.services.llm import call_llm

router = APIRouter(prefix="/settings", tags=["settings"])


class LlmSettings(BaseModel):
    provider: str = ""
    # Ключ передаём только когда пользователь его меняет (None — не трогать).
    api_key: Optional[str] = None
    model: str = ""
    base_url: str = ""


class SoundSettings(BaseModel):
    master: int = 80
    effects: int = 100
    music: int = 60


class UpdateSettings(BaseModel):
    repo: str = ""
    auto: bool = True


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


@router.get("")
def get_settings():
    data = settings_store.public()
    data["version"] = APP_VERSION
    return data


@router.post("/llm")
def set_llm(payload: LlmSettings):
    patch = {
        "llm_provider": (payload.provider or "").strip(),
        "llm_model": (payload.model or "").strip(),
        "llm_base_url": (payload.base_url or "").strip(),
    }
    if payload.api_key is not None:
        patch["llm_key"] = payload.api_key.strip()
    settings_store.save(patch)
    return {"status": "ok", "settings": settings_store.public()["llm"]}


@router.post("/llm/test")
def test_llm():
    """Небольшой запрос к модели: проверить, что ключ и адрес рабочие."""
    try:
        answer = call_llm("Ответь одним словом: работает?", max_tokens=16)
        return {"status": "ok", "answer": (answer or "").strip()[:120]}
    except Exception as error:  # noqa: BLE001 — текст ошибки нужен пользователю
        return {"status": "error", "detail": str(error)[:400]}


@router.post("/sound")
def set_sound(payload: SoundSettings):
    settings_store.save(
        {
            "sound_master": _clamp(payload.master),
            "sound_effects": _clamp(payload.effects),
            "sound_music": _clamp(payload.music),
        }
    )
    return {"status": "ok", "sound": settings_store.public()["sound"]}


@router.post("/update")
def set_update(payload: UpdateSettings):
    settings_store.save(
        {
            "update_repo": (payload.repo or "").strip(),
            "update_auto": bool(payload.auto),
        }
    )
    return {"status": "ok", "update": settings_store.public()["update"]}
