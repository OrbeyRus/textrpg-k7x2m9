"""HTTP-клиент для LLM.

Адрес, ключ и модель берутся из настроек (``settings_store``), поэтому
пользователь может переключить бесплатного провайдера прямо в игре.
"""

import time

import requests

from app.services import settings_store

REQUEST_TIMEOUT = 90     # модель отвечает не мгновенно: 40с не хватало
MAX_ATTEMPTS = 3         # повторы на сетевых ошибках и таймаутах
RETRY_DELAY = 1.5        # пауза между попытками, сек


def _headers(config: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {config['key']}",
        "Content-Type": "application/json",
    }
    # OpenRouter просит указывать источник — так запросы из игры видно в кабинете.
    if config["provider"] == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/textrpg"
        headers["X-Title"] = "Text RPG"
    return headers


def call_llm(prompt: str, max_tokens: int = 800) -> str:
    config = settings_store.llm_config()
    if not config["key"]:
        raise Exception(
            "Не задан ключ ИИ. Откройте меню → «Ключ ИИ» и выберите провайдера."
        )
    if not config["base_url"]:
        raise Exception(
            "Не задан адрес провайдера ИИ. Откройте меню → «Ключ ИИ»."
        )

    data = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": "Ты — профессиональный писатель и Мастер Игры. Отвечай строго на русском.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                config["base_url"],
                headers=_headers(config),
                json=data,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code != 200:
                raise Exception(f"Ошибка {response.status_code}: {response.text}")

            return response.json()["choices"][0]["message"]["content"]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise Exception(f"Ошибка LLM: {e}")
        except Exception as e:
            raise Exception(f"Ошибка LLM: {e}")
