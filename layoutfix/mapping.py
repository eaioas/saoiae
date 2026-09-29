"""Соответствие клавиш раскладок QWERTY (US) и ЙЦУКЕН.

Конвертация «по клавишам»: символ заменяется на тот, что стоит на той же
физической клавише в другой раскладке. Поддерживаются два варианта русской
раскладки macOS:

* ``pc``  — «Русская – ПК» (com.apple.keylayout.RussianWin), как в Windows;
* ``mac`` — стандартная «Русская» раскладка Apple (com.apple.keylayout.Russian).

Буквы в обоих вариантах одинаковые, различаются знаки препинания и «ё».
"""

_LETTERS_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,."
_LETTERS_RU = "йцукенгшщзхъфывапролджэячсмитьбю"
_LETTERS_EN_SHIFT = 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>'
_LETTERS_RU_SHIFT = "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ"

# Отличия вариантов: (символ в EN-раскладке, символ в RU-раскладке)
_VARIANT_EXTRA = {
    "pc": [
        ("`", "ё"), ("~", "Ё"),
        ("/", "."), ("?", ","),
        ("@", '"'), ("#", "№"), ("$", ";"), ("^", ":"), ("&", "?"),
    ],
    "mac": [
        ("\\", "ё"), ("|", "Ё"),
        ("@", '"'), ("#", "№"), ("$", "%"), ("%", ":"),
        ("^", ","), ("&", "."), ("*", ";"),
    ],
}

VARIANTS = tuple(_VARIANT_EXTRA)


def _build(variant):
    if variant not in _VARIANT_EXTRA:
        raise ValueError(f"unknown Russian layout variant: {variant!r}")
    pairs = list(zip(_LETTERS_EN, _LETTERS_RU))
    pairs += zip(_LETTERS_EN_SHIFT, _LETTERS_RU_SHIFT)
    pairs += _VARIANT_EXTRA[variant]
    en_ru = dict(pairs)
    ru_en = {ru: en for en, ru in pairs}
    assert len(en_ru) == len(ru_en), "mapping must be a bijection"
    return en_ru, ru_en


_TABLES = {v: _build(v) for v in VARIANTS}


def is_cyrillic(ch):
    return "а" <= ch.lower() <= "я" or ch in "ёЁ"


def is_latin(ch):
    return "a" <= ch.lower() <= "z"


def en_to_ru(text, variant="pc"):
    table = _TABLES[variant][0]
    return "".join(table.get(ch, ch) for ch in text)


def ru_to_en(text, variant="pc"):
    table = _TABLES[variant][1]
    return "".join(table.get(ch, ch) for ch in text)


def detect_direction(text):
    """Вернуть ``"en->ru"`` / ``"ru->en"`` по преобладающему алфавиту или ``None``."""
    latin = sum(map(is_latin, text))
    cyr = sum(map(is_cyrillic, text))
    if latin == cyr == 0:
        return None
    return "en->ru" if latin >= cyr else "ru->en"


def convert(text, variant="pc"):
    """Перевести текст в другую раскладку. Возвращает (новый_текст, направление)."""
    direction = detect_direction(text)
    if direction is None:
        return text, None
    fn = en_to_ru if direction == "en->ru" else ru_to_en
    return fn(text, variant), direction
