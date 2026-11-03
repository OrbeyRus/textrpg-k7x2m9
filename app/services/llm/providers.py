"""Каталог бесплатных провайдеров ИИ (OpenAI-совместимый Chat Completions).

Игра не вшивает чужие ключи: они привязаны к аккаунтам и лимиты на них общие.
Здесь только справочник — где взять бесплатный ключ и какой адрес/модель
использовать. Ключ пользователя хранится локально (см. settings_store).

Все провайдеры ниже говорят на одном протоколе (`/chat/completions`), поэтому
достаточно менять адрес, ключ и модель — код запроса остаётся общим.
"""

# Идентификатор «своего» провайдера: пользователь сам указывает адрес и модель.
CUSTOM_ID = "custom"

# Провайдер по умолчанию (совпадает с историческим ключом proxyapi из .env).
DEFAULT_ID = "proxyapi"

PROVIDERS = (
    {
        "id": "gemini",
        "label": "Google Gemini",
        "free": True,
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "default_model": "gemini-3.8-flash",
        "models": [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ],
        "key_url": "https://aistudio.google.com/apikey",
        "note": "Бесплатный тариф Google AI Studio. Модели Flash щедры на лимиты.",
    },
    {
        "id": "groq",
        "label": "Groq",
        "free": True,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "moonshotai/kimi-k2-instruct",
            "llama-3.1-8b-instant",
        ],
        "key_url": "https://console.groq.com/keys",
        "note": "Очень быстрый. Бесплатный тариф без карты, но лимит запросов в минуту.",
    },
    {
        "id": "openrouter",
        "label": "OpenRouter",
        "free": True,
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "openrouter/free",
        "models": [
            "openrouter/free",
            "nvidia/nemotron-3.5-lightning:free",
            "cohere/north-mini-code:free",
            "google/gemma-4-26b-a4b-it:free",
        ],
        "key_url": "https://openrouter.ai/keys",
        "note": "Модель «openrouter/free» сама выбирает доступную бесплатную модель.",
    },
    {
        "id": "mistral",
        "label": "Mistral",
        "free": True,
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "default_model": "mistral-small-latest",
        "models": [
            "mistral-small-latest",
            "magistral-small-latest",
            "devstral-small-latest",
        ],
        "key_url": "https://console.mistral.ai/api-keys",
        "note": "Разработчикам доступен бесплатный уровень (нужна регистрация).",
    },
    {
        "id": "proxyapi",
        "label": "proxyapi",
        "free": False,
        "base_url": "https://api.proxyapi.ru/v1/chat/completions",
        "default_model": "deepseek/deepseek-v3.2",
        "models": [
            "deepseek/deepseek-v3.2",
            "gpt-4o-mini",
            "claude-3-5-haiku",
        ],
        "key_url": "https://proxyapi.ru/",
        "note": "Российский посредник: удобен без VPN, но обычно платный.",
    },
    {
        "id": CUSTOM_ID,
        "label": "Свой адрес",
        "free": True,
        "base_url": "",
        "default_model": "",
        "models": [],
        "key_url": "",
        "note": "Любой OpenAI-совместимый сервер: свой прокси или локальная Ollama.",
    },
)

_BY_ID = {provider["id"]: provider for provider in PROVIDERS}


def get(provider_id: str) -> dict:
    """Провайдер по идентификатору или пустой словарь."""
    return _BY_ID.get((provider_id or "").strip(), {})


def catalog() -> list:
    """Публичный список провайдеров для экрана настроек (без ключей)."""
    return [
        {
            "id": provider["id"],
            "label": provider["label"],
            "free": provider["free"],
            "default_model": provider["default_model"],
            "models": list(provider["models"]),
            "key_url": provider["key_url"],
            "note": provider["note"],
            "custom": provider["id"] == CUSTOM_ID,
        }
        for provider in PROVIDERS
    ]
