"""Провайдеры ИИ и пользовательские настройки."""

from app.services import settings_store
from app.services.llm import providers


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_store, "SETTINGS_FILE", tmp_path / "settings.json")


def test_catalog_lists_free_providers_without_secrets():
    catalog = providers.catalog()
    ids = {provider["id"] for provider in catalog}

    assert {"gemini", "groq", "openrouter", "mistral", "proxyapi", "custom"} <= ids
    # В публичном каталоге нет адресов и уж точно нет ключей.
    assert all("base_url" not in provider for provider in catalog)
    assert all("key" not in provider for provider in catalog)


def test_default_config_uses_env_key(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(settings_store, "PROXYAPI_KEY", "env-key")

    config = settings_store.llm_config()

    assert config["provider"] == "proxyapi"
    assert config["key"] == "env-key"
    assert config["base_url"].startswith("https://api.proxyapi.ru")


def test_saved_provider_overrides_env(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(settings_store, "PROXYAPI_KEY", "env-key")

    settings_store.save({"llm_provider": "gemini", "llm_key": "abc"})
    config = settings_store.llm_config()

    assert config["provider"] == "gemini"
    assert config["key"] == "abc"
    assert config["model"] == "gemini-3.8-flash"
    assert "generativelanguage" in config["base_url"]


def test_custom_provider_uses_own_url(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)

    settings_store.save(
        {
            "llm_provider": "custom",
            "llm_key": "local",
            "llm_base_url": "http://127.0.0.1:11434/v1/chat/completions",
            "llm_model": "llama3",
        }
    )
    config = settings_store.llm_config()

    assert config["base_url"].endswith("/v1/chat/completions")
    assert config["model"] == "llama3"


def test_public_hides_full_key(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    settings_store.save({"llm_provider": "groq", "llm_key": "secret-value-123"})

    data = settings_store.public()

    assert data["llm"]["has_key"] is True
    assert "secret-value-123" not in data["llm"]["key_masked"]
    assert data["sound"]["master"] == 80


def test_sound_settings_are_saved(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)

    settings_store.save({"sound_master": 10, "sound_effects": 20, "sound_music": 30})
    data = settings_store.public()

    assert data["sound"] == {"master": 10, "effects": 20, "music": 30}
