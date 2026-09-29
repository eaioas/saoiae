import pytest

from layoutfix import mapping


def test_en_to_ru_letters():
    assert mapping.en_to_ru("ghbdtn") == "привет"
    assert mapping.en_to_ru("Ghbdtn") == "Привет"
    assert mapping.en_to_ru("cjj,otybt") == "сообщение"
    assert mapping.en_to_ru("{jhjij") == "Хорошо"


def test_ru_to_en_letters():
    assert mapping.ru_to_en("руддщ") == "hello"
    assert mapping.ru_to_en("Руддщ цщкдв") == "Hello world"


def test_pc_punctuation():
    assert mapping.en_to_ru("rfr ltkf&", "pc") == "как дела?"
    assert mapping.en_to_ru("`krf", "pc") == "ёлка"
    assert mapping.ru_to_en("руддщ,", "pc") == "hello?"


def test_mac_variant():
    assert mapping.en_to_ru("\\krf", "mac") == "ёлка"
    assert mapping.en_to_ru("ghbdtn^", "mac") == "привет,"
    assert mapping.ru_to_en("руддщ.", "mac") == "hello&"


@pytest.mark.parametrize("variant", mapping.VARIANTS)
def test_roundtrip(variant):
    text = "Съешь же ещё этих мягких французских булок, да выпей чаю"
    assert mapping.en_to_ru(mapping.ru_to_en(text, variant), variant) == text


def test_unmapped_chars_untouched():
    assert mapping.en_to_ru("123 !") == "123 !"


def test_convert_direction():
    assert mapping.convert("ghbdtn") == ("привет", "en->ru")
    assert mapping.convert("руддщ") == ("hello", "ru->en")
    assert mapping.convert("123") == ("123", None)
