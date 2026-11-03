"""Проверка обновлений на GitHub Releases.

Приложение при старте спрашивает: «есть ли релиз новее?». Сервер ходит в
GitHub (у него есть интернет), потому что из WebView это делать неудобно и
мешают ограничения CORS. Ответ кэшируется на несколько минут, чтобы не
упираться в лимит GitHub.
"""

import time

import requests
from fastapi import APIRouter, Query

from app.config import APP_VERSION
from app.services import settings_store, updates

router = APIRouter(prefix="/update", tags=["update"])

CACHE_SECONDS = 300
_TIMEOUT = 15
_cache = {"ts": 0.0, "repo": "", "data": None}


def _fetch_latest(repo: str) -> dict:
    response = requests.get(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TextRPG-Updater",
        },
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return updates.release_info(response.json())


@router.get("/check")
def check_update(current: str = Query("")):
    settings = settings_store.load()
    repo = (settings.get("update_repo") or "").strip()
    current_version = (current or APP_VERSION).strip()

    if not repo:
        return {
            "configured": False,
            "reason": "not_configured",
            "version": current_version,
        }

    cached = _cache
    fresh = (
        cached["data"]
        and cached["repo"] == repo
        and time.time() - cached["ts"] < CACHE_SECONDS
    )
    if fresh:
        info = cached["data"]
    else:
        try:
            info = _fetch_latest(repo)
        except requests.exceptions.HTTPError as error:
            status = getattr(error.response, "status_code", None)
            detail = "Релизы не найдены" if status == 404 else f"GitHub ответил {status}"
            return {"configured": True, "error": detail, "version": current_version}
        except Exception as error:  # noqa: BLE001 — текст нужен пользователю
            return {"configured": True, "error": str(error)[:200], "version": current_version}
        _cache.update({"ts": time.time(), "repo": repo, "data": info})

    return {
        "configured": True,
        "version": current_version,
        "latest": info.get("tag", ""),
        "update_available": updates.is_newer(info.get("tag", ""), current_version),
        **info,
    }
