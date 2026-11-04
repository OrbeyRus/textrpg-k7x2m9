"""Каталог встроенных книг — русская классика в общественном достоянии.

Идея: сразу после установки человек может начать играть, не загружая ничего
вручную. Тексты лежат рядом, в ``app/content/books/*.txt``, и по выбору игрока
проходят через тот же конвейер, что и загруженные книги (нарезка + поиск).

Почему именно эти произведения (юридическая часть):

* Все авторы умерли не позднее 1945 года. По ГК РФ исключительное право
  действует 70 лет после смерти автора (плюс 4 года для тех, кто работал в
  годы Великой Отечественной войны), поэтому сроки давно истекли.
* Все произведения — русскоязычные оригиналы. Переводы сознательно не берём:
  даже у свободной иностранной классики современный перевод может быть под
  охраной, а это лишний риск.

Источник текстов — Викитека (ru.wikisource.org). Точный список источников —
в файле CREDITS.md рядом с книгой и в поле ``source`` ниже.
"""

from pathlib import Path

# Тексты книг лежат в подпапке рядом с этим модулем: Chaquopy копирует весь
# каталог app/** в APK, поэтому книги попадают и в приложение.
BOOKS_DIR = Path(__file__).resolve().parent / "books"

# Порядок карточек в интерфейсе — по жанрам, как в onboarding.
BOOKS = [
    {
        "id": "ruslan_i_lyudmila",
        "title": "Руслан и Людмила",
        "author": "А. С. Пушкин",
        "year": 1820,
        "genre": "fantasy",
        "description": "Волшебная поэма о похищении княжны, богатырях и живом колдуне Черноморе.",
        "filename": "ruslan_i_lyudmila.txt",
        "source": "https://ru.wikisource.org/wiki/Руслан_и_Людмила_(Пушкин)",
        "source_page": "Руслан и Людмила (Пушкин)",
    },
    {
        "id": "upyr",
        "title": "Упырь",
        "author": "А. К. Толстой",
        "year": 1841,
        "genre": "fantasy",
        "description": "Готическая повесть о бале, странном незнакомце и родовом проклятии.",
        "filename": "upyr.txt",
        "source": "https://ru.wikisource.org/wiki/Упырь_(Толстой)",
        "source_page": "Упырь (Толстой)",
    },
    {
        "id": "asya",
        "title": "Ася",
        "author": "И. С. Тургенев",
        "year": 1858,
        "genre": "romance",
        "description": "Тихая история первой любви на берегу Рейна и горечь несказанных слов.",
        "filename": "asya.txt",
        "source": "https://ru.wikisource.org/wiki/Ася_(Тургенев)",
        "source_page": "Ася (Тургенев)",
    },
    {
        "id": "granatovyy_braslet",
        "title": "Гранатовый браслет",
        "author": "А. И. Куприн",
        "year": 1911,
        "genre": "romance",
        "description": "Повесть о безответной любви, что сильнее жизни, и о маленьком гранатовом браслете.",
        "filename": "granatovyy_braslet.txt",
        "source": "https://ru.wikisource.org/wiki/Гранатовый_браслет_(Куприн)/Версия_2",
        "source_page": "Гранатовый браслет (Куприн)/Версия 2",
    },
    {
        "id": "shvedskaya_spichka",
        "title": "Шведская спичка",
        "author": "А. П. Чехов",
        "year": 1884,
        "genre": "mystery",
        "description": "Ироничный детектив: пропал помещик, и следствие берётся за дело рьяно и нелепо.",
        "filename": "shvedskaya_spichka.txt",
        "source": "https://ru.wikisource.org/wiki/Шведская_спичка_(Чехов)",
        "source_page": "Шведская спичка (Чехов)",
    },
    {
        "id": "fatalist",
        "title": "Фаталист",
        "author": "М. Ю. Лермонтов",
        "year": 1840,
        "genre": "mystery",
        "description": "Глава из «Героя нашего времени»: спор о предопределении и смертельный опыт.",
        "filename": "fatalist.txt",
        "source": "https://ru.wikisource.org/wiki/Герой_нашего_времени_(Лермонтов)/СО/Фаталист",
        "source_page": "Герой нашего времени (Лермонтов)/СО/Фаталист",
    },
    {
        "id": "viy",
        "title": "Вий",
        "author": "Н. В. Гоголь",
        "year": 1842,
        "genre": "horror",
        "description": "Повесть о семинаристе Хоме Бруте, ведьме-панночке и том, кого лучше не видеть.",
        "filename": "viy.txt",
        "source": "https://ru.wikisource.org/wiki/Вий_(Гоголь)",
        "source_page": "Вий (Гоголь)",
    },
    {
        "id": "pikovaya_dama",
        "title": "Пиковая дама",
        "author": "А. С. Пушкин",
        "year": 1834,
        "genre": "horror",
        "description": "Петербургская повесть о трёх картах, тайне старой графини и цене одержимости.",
        "filename": "pikovaya_dama.txt",
        "source": "https://ru.wikisource.org/wiki/Пиковая_дама_(Пушкин)",
        "source_page": "Пиковая дама (Пушкин)",
    },
    {
        "id": "na_lune",
        "title": "На Луне",
        "author": "К. Э. Циолковский",
        "year": 1893,
        "genre": "scifi",
        "description": "Ранняя научная фантастика: сон-путешествие на Луну и её удивительный мир.",
        "filename": "na_lune.txt",
        "source": "https://ru.wikisource.org/wiki/На_Луне_(Циолковский)",
        "source_page": "На Луне (Циолковский)",
    },
    {
        "id": "respublika_yuzhnogo_kresta",
        "title": "Республика Южного Креста",
        "author": "В. Я. Брюсов",
        "year": 1905,
        "genre": "scifi",
        "description": "Антиутопия о городе под куполом, где люди разучились видеть и любить.",
        "filename": "respublika_yuzhnogo_kresta.txt",
        "source": "https://ru.wikisource.org/wiki/Республика_Южного_Креста_(Брюсов)/1911_(ВТ)",
        "source_page": "Республика Южного Креста (Брюсов)/1911 (ВТ)",
    },
    {
        "id": "kapitanskaya_dochka",
        "title": "Капитанская дочка",
        "author": "А. С. Пушкин",
        "year": 1836,
        "genre": "historical",
        "description": "Время Пугачёвского бунта: честь, любовь и выбор молодого офицера Петра Гринёва.",
        "filename": "kapitanskaya_dochka.txt",
        "source": "https://ru.wikisource.org/wiki/Капитанская_дочка_(Пушкин)/1978_(СО)",
        "source_page": "Капитанская дочка (Пушкин)/1978 (СО)",
    },
    {
        "id": "kavkazskiy_plennik",
        "title": "Кавказский пленник",
        "author": "Л. Н. Толстой",
        "year": 1872,
        "genre": "historical",
        "description": "Рассказ о двух русских офицерах в плену у горцев и о силе, что зовётся волей.",
        "filename": "kavkazskiy_plennik.txt",
        "source": "https://ru.wikisource.org/wiki/Кавказский_пленник_(Толстой)",
        "source_page": "Кавказский пленник (Толстой)",
    },
    {
        "id": "dubrovskiy",
        "title": "Дубровский",
        "author": "А. С. Пушкин",
        "year": 1841,
        "genre": "adventure",
        "description": "Вражда двух помещиков, разбойничья вольница и благородный мститель.",
        "filename": "dubrovskiy.txt",
        "source": "https://ru.wikisource.org/wiki/Дубровский_(Пушкин)/Версия_2",
        "source_page": "Дубровский (Пушкин)/Версия 2",
    },
    {
        "id": "taman",
        "title": "Тамань",
        "author": "М. Ю. Лермонтов",
        "year": 1840,
        "genre": "adventure",
        "description": "Глава из «Героя нашего времени»: ночёвка в глухом городке и контрабандисты.",
        "filename": "taman.txt",
        "source": "https://ru.wikisource.org/wiki/Герой_нашего_времени_(Лермонтов)/СО/Тамань",
        "source_page": "Герой нашего времени (Лермонтов)/СО/Тамань",
    },
    {
        "id": "ionych",
        "title": "Ионыч",
        "author": "А. П. Чехов",
        "year": 1898,
        "genre": "universal",
        "description": "История доктора Старцева: как мечты и чувства тихо вытесняет обыденность.",
        "filename": "ionych.txt",
        "source": "https://ru.wikisource.org/wiki/Ионыч_(Чехов)",
        "source_page": "Ионыч (Чехов)",
    },
    {
        "id": "starukha_izergil",
        "title": "Старуха Изергиль",
        "author": "М. Горький",
        "year": 1895,
        "genre": "universal",
        "description": "Три легенды о гордости, любви и свободе, рассказанные у моря старой цыганкой.",
        "filename": "starukha_izergil.txt",
        "source": "https://ru.wikisource.org/wiki/Старуха_Изергиль_(Горький)",
        "source_page": "Старуха Изергиль (Горький)",
    },
]

_BY_ID = {book["id"]: book for book in BOOKS}

# Какие поля отдаём в интерфейс (текст книги по сети не гоняем).
_PUBLIC_FIELDS = ("id", "title", "author", "year", "genre", "description")


def get(book_id: str):
    """Метаданные встроенной книги по её идентификатору."""
    return _BY_ID.get((book_id or "").strip())


def public_list() -> list:
    """Список книг для интерфейса (без путей и текста)."""
    return [{field: book[field] for field in _PUBLIC_FIELDS} for book in BOOKS]


def text_path(book_id: str):
    """Путь к текстовому файлу книги или None, если книги нет."""
    book = get(book_id)
    if not book:
        return None
    return BOOKS_DIR / book["filename"]


def load_text(book_id: str):
    """Читает текст книги или возвращает None, если файла нет."""
    path = text_path(book_id)
    if not path or not path.exists():
        return None
    return path.read_text(encoding="utf-8")
