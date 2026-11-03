"""HTTP-клиент для LLM."""

import time

import requests

from app.config import LLM_MODEL, PROXYAPI_KEY

API_URL = "https://api.proxyapi.ru/v1/chat/completions"
REQUEST_TIMEOUT = 90     # модель отвечает не мгновенно: 40с не хватало
MAX_ATTEMPTS = 3         # повторы на сетевых ошибках и таймаутах
RETRY_DELAY = 1.5        # пауза между попытками, сек


def call_llm(prompt: str, max_tokens: int = 800) -> str:
    if not PROXYAPI_KEY:
        raise Exception("PROXYAPI_KEY не задан. Добавьте ключ в .env")

    headers = {
        "Authorization": f"Bearer {PROXYAPI_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": LLM_MODEL,
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
                API_URL, headers=headers, json=data, timeout=REQUEST_TIMEOUT
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
