"""Запуск сервера Text RPG с автоматическим открытием игры в браузере.

Скрипт сам дожидается, пока сервер начнёт отвечать, и только потом открывает
окно игры — поэтому браузер не показывает ошибку «сайт недоступен».

Использование (из папки C:\\TextRPG):
    python start.py                 # сервер на 127.0.0.1:8001 + окно игры
    python start.py --port 8002     # другой порт
    python start.py --no-browser    # только сервер, без браузера

Остановить сервер — Ctrl+C в этом окне.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

HOST = "127.0.0.1"
PORT = 8001
APP = "main:app"


def _force_utf8_console() -> None:
    """Переводит вывод в UTF-8.

    На Windows консоль по умолчанию бывает в cp1251/cp866, и вывод кириллицы
    или эмодзи из логов падает с UnicodeEncodeError. Меняем кодировку потоков,
    если интерпретатор это позволяет (в тестах и перенаправленном выводе —
    молча пропускаем).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

# Настройки ожидания готовности сервера.
READY_TIMEOUT = 30.0   # сколько секунд ждать запуск
POLL_INTERVAL = 0.15   # как часто проверять порт


def _port_is_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """True, если на host:port принимают соединения."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _open_browser_when_ready(url: str, host: str, port: int) -> None:
    """Ждёт, пока сервер поднимется, затем открывает игру в новой вкладке/окне."""
    deadline = time.monotonic() + READY_TIMEOUT
    while time.monotonic() < deadline:
        if _port_is_open(host, port):
            break
        time.sleep(POLL_INTERVAL)
    webbrowser.open_new(url)


def main() -> int:
    _force_utf8_console()
    parser = argparse.ArgumentParser(
        description="Запуск сервера Text RPG и открытие игры в браузере."
    )
    parser.add_argument("--host", default=HOST, help=f"адрес сервера (по умолчанию {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"порт сервера (по умолчанию {PORT})")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="не открывать браузер автоматически",
    )
    args = parser.parse_args()

    # Работаем относительно папки скрипта, чтобы "main:app" и данные находились
    # при любом способе запуска (в т.ч. двойным кликом).
    os.chdir(Path(__file__).resolve().parent)

    url = f"http://{args.host}:{args.port}/"

    # Сервер уже запущен — просто открываем игру.
    if _port_is_open(args.host, args.port):
        print(f"Сервер уже запущен: {url}")
        if not args.no_browser:
            webbrowser.open_new(url)
        return 0

    if not args.no_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(url, args.host, args.port),
            daemon=True,
        ).start()

    print(f"Запускаю сервер: {url}")
    print("Остановить — Ctrl+C.\n")

    try:
        uvicorn.run(APP, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
