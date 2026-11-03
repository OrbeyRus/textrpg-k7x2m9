"""HTTP-клиент для LLM."""

import requests

from app.config import LLM_MODEL, PROXYAPI_KEY


def call_llm(prompt: str, max_tokens: int = 800) -> str:
    if not PROXYAPI_KEY:
        raise Exception("PROXYAPI_KEY не задан. Добавьте ключ в .env")

    try:
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

        response = requests.post(
            "https://api.proxyapi.ru/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=40,
        )
        if response.status_code != 200:
            raise Exception(f"Ошибка {response.status_code}: {response.text}")

        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"Ошибка LLM: {e}")
