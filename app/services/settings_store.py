"""Пользовательские настройки игры: провайдер ИИ, ключ, звук, обновления.

Настройки лежат в ``data/settings.json`` (на Android — во внутренней папке
приложения, куда писать можно). Читать их может любой модуль, поэтому клиент
LLM берёт провайдера и ключ отсюда, а не из константы.

Ключ никогда не отдаётся наружу целиком: в API уходит только маска.
"""

import json
import threading

from app.config import DATA_DIR, LLM_MODEL, PROXYAPI_KEY
from app.services.llm import providers

SETTINGS_FILE = DATA_DIR / "settings.json"

_DEFAULTS = {
    "llm_provider": providers.DEFAULT_ID,
    "llm_key": "",
    "llm_model": "",
    "llm_base_url": "",
    "sound_master": 80,
    "sound_effects": 100,
    "sound_music": 60,
    "update_repo": "",
    "update_auto": True,
}

_lock = threading.Lock()


def _read() -> dict:
    data = dict(_DEFAULTS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            data.update(raw)
    except (OSError, ValueError):
        pass
    return data


def load() -> dict:
    """Текущие настройки (средённые со значениями по умолчанию)."""
    with _lock:
        return _read()


def save(patch: dict) -> dict:
    """Сохраняет переданные поля и возвращает получившиеся настройки."""
    with _lock:
        data = _read()
        for key, value in (patch or {}).items():
            if key in _DEFAULTS:
                data[key] = value
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass
        return data


def _mask(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:4]}…{key[-4:]}"


def llm_config() -> dict:
    """Провайдер, ключ, модель и адрес для запроса к модели.

    Ключ из ``.env`` (PROXYAPI_KEY) работает как запасной вариант, пока
    пользователь не выбрал провайдера сам — так сохраняется поведение
    прежних версий.
    """
    data = load()
    provider_id = (data.get("llm_provider") or providers.DEFAULT_ID).strip()
    provider = providers.get(provider_id)

    key = (data.get("llm_key") or "").strip()
    if not key and provider_id == providers.DEFAULT_ID:
        key = (PROXYAPI_KEY or "").strip()

    model = (data.get("llm_model") or "").strip()
    if not model:
        model = (provider.get("default_model") or "") or LLM_MODEL

    if provider_id == providers.CUSTOM_ID:
        base_url = (data.get("llm_base_url") or "").strip()
    else:
        base_url = (provider.get("base_url") or "").strip()

    return {
        "provider": provider_id,
        "label": provider.get("label") or provider_id,
        "key": key,
        "model": model,
        "base_url": base_url,
    }


def public() -> dict:
    """Настройки для интерфейса: без полного ключа, только маска."""
    data = load()
    config = llm_config()
    return {
        "llm": {
            "provider": config["provider"],
            "label": config["label"],
            "model": config["model"],
            "base_url": config["base_url"],
            "has_key": bool(config["key"]),
            "key_masked": _mask(config["key"]),
        },
        "providers": providers.catalog(),
        "sound": {
            "master": int(data.get("sound_master", 80)),
            "effects": int(data.get("sound_effects", 100)),
            "music": int(data.get("sound_music", 60)),
        },
        "update": {
            "repo": data.get("update_repo") or "",
            "auto": bool(data.get("update_auto", True)),
        },
    }
