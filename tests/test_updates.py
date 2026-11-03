"""Сравнение версий и выбор APK из релиза GitHub."""

from app.services import updates


def test_parse_version():
    assert updates.parse_version("v1.2.3") == (1, 2, 3)
    assert updates.parse_version("1.2.0") == (1, 2, 0)
    assert updates.parse_version("") == ()


def test_is_newer():
    assert updates.is_newer("v1.2.0", "1.1.0")
    assert updates.is_newer("v1.2.1", "1.2.0")
    assert updates.is_newer("v2.0", "1.9.9")
    assert not updates.is_newer("v1.2.0", "1.2.0")
    assert not updates.is_newer("v1.1.0", "1.2.0")
    assert not updates.is_newer("", "1.2.0")


def test_pick_apk_asset_skips_other_files():
    assets = [
        {"name": "notes.txt", "browser_download_url": "notes"},
        {"name": "TextRPG-1.2.0.apk", "browser_download_url": "apk", "size": 123},
    ]
    chosen = updates.pick_apk_asset(assets)

    assert chosen["url"] == "apk"
    assert chosen["name"] == "TextRPG-1.2.0.apk"


def test_pick_apk_asset_without_apk():
    assert updates.pick_apk_asset([{"name": "readme.md"}]) == {}


def test_release_info_compacts_github_payload():
    release = {
        "tag_name": "v1.2.0",
        "name": "Версия 1.2",
        "body": "Что нового",
        "html_url": "https://example/release",
        "assets": [
            {"name": "app.apk", "browser_download_url": "https://example/app.apk", "size": 10}
        ],
    }
    info = updates.release_info(release)

    assert info["tag"] == "v1.2.0"
    assert info["asset_url"] == "https://example/app.apk"
