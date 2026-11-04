"""Служебный скрипт: скачивает встроенные книги с Викитеки.

Приложение его не импортирует — это инструмент разработчика. Запуск из корня
проекта:

    py -3.15 scripts/fetch_classics.py

Скрипт проходит по каталогу ``app.content.library`` и для каждой книги берёт
страницу Викитеки (``source_page``), вычищает вики-разметку и сохраняет чистый
текст в ``app/content/books/<filename>``. Повторный запуск просто перезапишет
тексты.

Тексты — общественное достояние (см. комментарий в app/content/library.py),
поэтому их можно свободно распространять вместе с игрой.
"""

import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.content import library  # noqa: E402

API = "https://ru.wikisource.org/w/api.php"
UA = {"User-Agent": "TextRPG/1.0 (educational; built-in classics fetcher)"}

# Служебные блоки Викитеки: навигация, сноски, шапка, правки.
SKIP_CLASS = re.compile(
    r"(ws-noexport|mw-editsection|mw-references|references|navbox|infobox"
    r"|headertemplate|mw-cite-backlink|mw-ref|noprint|searchaux|licens"
    r"|catlinks|printfooter|mbox|ambox|tmbox)",
    re.I,
)
SKIP_TAGS = {"script", "style"}
BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "section", "table", "hr",
}
# Строки-заглушки, которые не относятся к самому произведению.
DROP_LINES = {
    "примечания", "комментарии", "сноски", "источник", "лицензия",
    "лицензии", "энциклопедии", "внешние ссылки", "википроекты",
}
DROP_PATTERNS = re.compile(
    r"(источник текста не указан|могут содержаться серьёзные ошибки|"
    r"внимание!|сверен[оа]? с изданием|источник текста:|"
    r"могут быть включены в Викитеку|отредактировать эту работу|выверив её текст)",
    re.I,
)


class TextExtractor(HTMLParser):
    """Превращает HTML Викитеки в простой текст."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []  # True — внутри служебного блока, текст не берём

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        classes = dict(attrs).get("class", "") or ""
        parent_skip = self.stack[-1] if self.stack else False
        skip = parent_skip or tag in SKIP_TAGS or bool(SKIP_CLASS.search(classes))
        self.stack.append(skip)
        if skip:
            return
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br" and not (self.stack and self.stack[-1]):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        was_skip = self.stack.pop() if self.stack else False
        if was_skip:
            return
        if tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.stack and self.stack[-1]:
            return
        self.parts.append(data)

    def text(self):
        raw = "".join(self.parts).replace("\xa0", " ")
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r" *\n *", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def fetch_page_html(title: str) -> str:
    """Возвращает отрендеренный HTML страницы Викитеки."""
    url = (
        f"{API}?action=parse&format=json&formatversion=2&prop=text&disabletoc=1"
        f"&page={urllib.parse.quote(title)}"
    )
    request = urllib.request.Request(url, headers=UA)
    for attempt in range(6):
        try:
            import json

            payload = json.loads(
                urllib.request.urlopen(request, timeout=60).read().decode("utf-8")
            )
            if "error" in payload:
                raise RuntimeError(payload["error"].get("info", "ошибка API"))
            return payload["parse"]["text"]
        except urllib.error.HTTPError as error:
            if error.code == 429:  # лимит запросов — ждём и повторяем
                time.sleep(5 + attempt * 5)
                continue
            raise
    raise RuntimeError("Викитека ограничила запросы")


def clean_text(html: str) -> str:
    extractor = TextExtractor()
    extractor.feed(html)
    paragraphs = []
    for line in extractor.text().split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("↑"):
            continue
        if stripped.lower() in DROP_LINES:
            continue
        if DROP_PATTERNS.search(stripped):
            continue
        paragraphs.append(stripped)
    return "\n\n".join(paragraphs) + "\n"


def main() -> int:
    library.BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for index, book in enumerate(library.BOOKS):
        try:
            html = fetch_page_html(book["source_page"])
            text = clean_text(html)
        except Exception as error:  # noqa: BLE001 - сообщаем и идём дальше
            print(f"ОШИБКА  {book['title']}: {error}")
            failed.append(book["id"])
            continue

        if len(text) < 2000:
            print(f"МАЛО    {book['title']}: всего {len(text)} символов — проверьте страницу")
            failed.append(book["id"])
            continue

        target = library.BOOKS_DIR / book["filename"]
        target.write_text(text, encoding="utf-8")
        print(f"OK      {book['title']:32} {len(text):>8} символов -> {book['filename']}")

        if index < len(library.BOOKS) - 1:
            time.sleep(2)  # не упираемся в лимит Викитеки

    if failed:
        print("Не удалось скачать:", ", ".join(failed))
        return 1
    print(f"Готово: {len(library.BOOKS)} книг в {library.BOOKS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
