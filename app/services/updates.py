"""Проверка обновлений через GitHub Releases.

Сравниваем версию приложения с тегом последнего релиза (``v1.2.0``),
ищем среди вложений файл ``.apk`` и отдаём прямую ссылку на скачивание.
Сетевые запросы и разбор ответа GitHub собраны здесь, чтобы их было удобно
тестировать отдельно от роутера.
"""

import re

_SEMVER = re.compile(r"\d+")


def parse_version(text: str) -> tuple:
    """Версия в виде кортежа чисел: ``v1.2.0`` → ``(1, 2, 0)``."""
    return tuple(int(part) for part in _SEMVER.findall(text or ""))


def is_newer(latest: str, current: str) -> bool:
    """Вернулось True, если ``latest`` новее ``current``."""
    newest, current_parts = parse_version(latest), parse_version(current)
    if not newest:
        return False
    length = max(len(newest), len(current_parts))
    left = newest + (0,) * (length - len(newest))
    right = current_parts + (0,) * (length - len(current_parts))
    return left > right


def pick_apk_asset(assets) -> dict:
    """Первое вложение-APK из релиза (или пустой словарь)."""
    for asset in assets or []:
        name = str(asset.get("name") or "")
        if name.lower().endswith(".apk"):
            return {
                "name": name,
                "url": asset.get("browser_download_url") or "",
                "size": asset.get("size") or 0,
            }
    return {}


def release_info(release: dict) -> dict:
    """Компактная сводка релиза GitHub."""
    asset = pick_apk_asset(release.get("assets"))
    return {
        "tag": release.get("tag_name") or "",
        "name": release.get("name") or "",
        "notes": (release.get("body") or "")[:2000],
        "page": release.get("html_url") or "",
        "asset_url": asset.get("url", ""),
        "asset_name": asset.get("name", ""),
        "asset_size": asset.get("size", 0),
    }
