"""Точка входа Python внутри Android-приложения (Chaquopy).

Kotlin вызывает bootstrap.start(...) — поднимается тот же самый сервер, что и
на десктопе (main:app), но в фоновом потоке и с данными в папке приложения.
После этого WebView открывает http://127.0.0.1:8001.
"""

import os
import socket
import threading
import time

_server = None
_url = None


def start(data_dir, api_key="", host="127.0.0.1", port=8001):
    """Запускает сервер (один раз) и возвращает его адрес."""
    global _server, _url

    # Повторный вызов (например, после поворота экрана) — сервер уже работает.
    if _url:
        return _url

    # Изменяемые данные — только в папке приложения.
    os.environ["TEXTRPG_DATA_DIR"] = data_dir
    # На телефоне нет Ollama — поиск по книге идёт по словам (BM25).
    os.environ["TEXTRPG_NO_EMBED"] = "1"
    if api_key:
        os.environ["PROXYAPI_KEY"] = api_key

    import uvicorn

    config = uvicorn.Config(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        loop="asyncio",  # uvloop на Android не собираем
        http="h11",      # httptools тоже не собираем
    )
    _server = uvicorn.Server(config)
    threading.Thread(target=_server.run, name="textrpg-server", daemon=True).start()

    _wait_ready(host, port)
    _url = "http://{}:{}/".format(host, port)
    return _url


def _wait_ready(host, port, timeout=90.0):
    """Ждём, пока сервер начнёт принимать соединения (первый старт бывает долгим)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False
