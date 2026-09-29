import pytest

from layoutfix.detector import Detector


@pytest.fixture
def det():
    return Detector()


@pytest.mark.parametrize("typed, expected", [
    ("ghbdtn", "привет"),
    ("Ghbdtn", "Привет"),
    ("ltkf&", "дела?"),
    ("gjkmpjdfntkm", "пользователь"),
    ("руддщ", "hello"),
    ("руддщб", "hello,"),
    ("цщкл", "work"),
    # нет в словаре — срабатывает биграммная эвристика
    ("cjdctv", "совсем"),
    ("ytcrjkmrj", "несколько"),
    ("dcnhtnbvcz", "встретимся"),
])
def test_fixes_wrong_layout(det, typed, expected):
    assert det.fix(typed) == expected


@pytest.mark.parametrize("word", [
    "hello", "привет", "the", "something", "keyboard", "string", "rhythm",
    "javascript", "github", "спасибо", "здравствуйте", "взгляд", "кошка",
    "asdf", "git", "ls", "ok",
])
def test_keeps_correct_words(det, word):
    assert det.fix(word) is None


@pytest.mark.parametrize("token", [
    "https://ghbdtn.com", "www.ghbdtn", "user@ghbdtn.ru", "/usr/bin",
    "ghbdtn123", "my_var", "a=b", "ghbdtnпривет",
])
def test_skips_special_tokens(det, token):
    assert det.fix(token) is None


def test_exclusions():
    assert Detector(exclusions=["ghbdtn"]).fix("ghbdtn") is None


def test_min_length():
    assert Detector(min_length=7).fix("ghbdtn") is None


def test_custom_checker_used():
    det = Detector(checker=lambda w, lang: lang == "ru" and w == "девочка")
    assert det.fix("ltdjxrf") == "девочка"


def test_checker_errors_are_ignored():
    def boom(word, lang):
        raise RuntimeError
    assert Detector(checker=boom).fix("ghbdtn") == "привет"
