"""Решает, набрано ли слово в неправильной раскладке."""

import re

from . import mapping, wordlists

# Токены, которые никогда не трогаем: ссылки, почта, пути, код, числа.
_SPECIAL = re.compile(r"(://|www\.|\w@\w|^/|[_=+0-9])")

_LANG_OF = {"en->ru": ("en", "ru"), "ru->en": ("ru", "en")}


def _core(token, lang):
    """Слово без знаков по краям (только буквы нужного алфавита)."""
    is_letter = mapping.is_cyrillic if lang == "ru" else mapping.is_latin
    start, end = 0, len(token)
    while start < end and not is_letter(token[start]):
        start += 1
    while end > start and not is_letter(token[end - 1]):
        end -= 1
    return token[start:end]


def _unseen_ratio(word, lang):
    bigrams = wordlists.RU_BIGRAMS if lang == "ru" else wordlists.EN_BIGRAMS
    grams = list(wordlists._bigrams(word.lower()))
    if not grams:
        return 1.0
    return sum(g not in bigrams for g in grams) / len(grams)


def _embedded_is_word(word, lang):
    words = wordlists.RU_SET if lang == "ru" else wordlists.EN_SET
    return word.lower() in words


class Detector:
    """
    ``checker(word, lang) -> bool`` — проверка «это настоящее слово?»
    (на macOS — системная орфография). Без него используется встроенный словарь.
    """

    def __init__(self, variant="pc", checker=None, min_length=3, exclusions=()):
        self.variant = variant
        self.checker = checker
        self.min_length = min_length
        self.exclusions = {w.lower() for w in exclusions}

    def is_word(self, word, lang):
        if _embedded_is_word(word, lang):
            return True
        if self.checker is not None:
            try:
                return bool(self.checker(word, lang))
            except Exception:
                return False
        return False

    def fix(self, token):
        """Вернуть исправленный токен или ``None``, если исправлять не нужно."""
        if not token or _SPECIAL.search(token):
            return None
        if any(map(mapping.is_latin, token)) and any(map(mapping.is_cyrillic, token)):
            return None  # смесь алфавитов — скорее всего осознанно

        converted, direction = mapping.convert(token, self.variant)
        if direction is None or converted == token:
            return None
        src, dst = _LANG_OF[direction]
        core_src = _core(token, src)
        core_dst = _core(converted, dst)
        if len(core_dst) < self.min_length:
            return None
        if token.lower() in self.exclusions or core_src.lower() in self.exclusions:
            return None

        if core_src and self.is_word(core_src, src):
            return None
        if self.is_word(core_dst, dst):
            return converted

        # Запасной вариант: исходное слово «непроизносимо» для своего языка,
        # а сконвертированное выглядит естественно.
        if (len(core_dst) >= 4
                and _unseen_ratio(core_src or token, src) >= 0.5
                and _unseen_ratio(core_dst, dst) <= 0.25):
            return converted
        return None
