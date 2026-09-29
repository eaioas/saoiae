import pytest

from layoutfix.config import Config, parse_hotkey
from layoutfix.service import KC_BACKSPACE, KC_SPACE, Corrector
from layoutfix.tracker import WordTracker

KC_RETURN = 36


class FakeSystem:
    """Имитирует текстовое поле: печать, стирание, выделение."""

    def __init__(self, selection=None):
        self.text = ""
        self.selection = selection
        self.languages = []
        self.saved = 0
        self.frontmost = "com.apple.TextEdit"

    def ru_variant(self):
        return "pc"

    def frontmost_bundle_id(self):
        return self.frontmost

    def press_backspace(self, n):
        self.text = self.text[:-n] if n else self.text

    def type_text(self, text):
        self.text += text

    def wait_modifiers_released(self):
        pass

    def selected_text(self):
        return self.selection

    def replace_selection(self, text):
        self.text = self.text.replace(self.selection, text)
        self.selection = None

    def reselect(self, length):
        pass

    def select_language(self, lang):
        self.languages.append(lang)

    def save_config(self, config):
        self.saved += 1


def type_keys(corrector, system, text):
    """Нажатие клавиш пользователем: событие проходит, если его не проглотили."""
    for ch in text:
        if ch == " ":
            if not corrector.on_key(KC_SPACE, " ", frozenset()):
                system.text += " "
        elif ch == "\b":
            corrector.on_key(KC_BACKSPACE, "\x7f", frozenset())
            system.text = system.text[:-1]
        else:
            corrector.on_key(0, ch, frozenset())
            system.text += ch


def press_hotkey(corrector):
    assert corrector.on_key(49, "\xa0", frozenset({"alt"})) is True
    corrector._jobs.join()


def make(auto=False, selection=None, **kw):
    system = FakeSystem(selection)
    config = Config(auto_correct=auto, **kw)
    return Corrector(config, system), system


# ---------------------------------------------------------------- tracker

def test_tracker_words_and_backspace():
    t = WordTracker()
    for ch in "ghbd":
        t.type_char(ch)
    t.backspace()
    assert t.take_last() == ("ghb", 0)
    assert t.space() == "ghb"
    t.space()
    assert t.take_last() == ("ghb", 2)
    t.backspace()
    t.backspace()
    assert t.take_last() == ("ghb", 0)
    t.type_char("x")
    assert t.current == "ghbx"


# ---------------------------------------------------------------- config

def test_parse_hotkey():
    hk = parse_hotkey("Alt+Space")
    assert hk.keycode == 49 and hk.modifiers == {"alt"}
    assert hk.label() == "⌥Space"
    assert parse_hotkey("ctrl+shift+z").label() == "⌃⇧Z"
    for bad in ("", "space", "alt+foo", "hyper+a"):
        with pytest.raises(ValueError):
            parse_hotkey(bad)


def test_config_roundtrip(tmp_path):
    path = tmp_path / "c.json"
    Config(auto_correct=True, exclusions=["ok"]).save(str(path))
    cfg = Config.load(str(path))
    assert cfg.auto_correct and cfg.exclusions == ["ok"]


def test_config_bad_hotkey_falls_back(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"hotkey": "nonsense", "unknown_key": 1}')
    assert Config.load(str(path)).hotkey == "alt+space"


# ---------------------------------------------------------------- auto mode

def test_auto_fixes_on_space():
    c, s = make(auto=True)
    type_keys(c, s, "ghbdtn rfr ltkf ")
    assert s.text == "привет как дела "
    assert s.languages[-1] == "ru"


def test_auto_leaves_correct_text():
    c, s = make(auto=True)
    type_keys(c, s, "hello world ")
    assert s.text == "hello world "


def test_auto_disabled_by_default():
    c, s = make()
    type_keys(c, s, "ghbdtn ")
    assert s.text == "ghbdtn "


def test_auto_skips_excluded_apps():
    c, s = make(auto=True)
    s.frontmost = "com.apple.Terminal"
    type_keys(c, s, "ghbdtn ")
    assert s.text == "ghbdtn "


def test_auto_respects_backspace_edits():
    c, s = make(auto=True)
    type_keys(c, s, "ghbdtx\bn ")
    assert s.text == "привет "


# ---------------------------------------------------------------- hotkey

def test_hotkey_fixes_current_word():
    c, s = make()
    type_keys(c, s, "hello ghbdtn")
    press_hotkey(c)
    assert s.text == "hello привет"


def test_hotkey_fixes_last_word_after_space_and_toggles_back():
    c, s = make()
    type_keys(c, s, "руддщ ")
    press_hotkey(c)
    assert s.text == "hello "
    press_hotkey(c)
    assert s.text == "руддщ "


def test_hotkey_converts_selection():
    c, s = make(selection="ghbdtn, rfr ltkf&")
    s.text = "ghbdtn, rfr ltkf&"
    press_hotkey(c)
    assert s.text == "приветб как дела?"


def test_hotkey_undo_of_auto_fix_learns_exclusion():
    c, s = make(auto=True)
    type_keys(c, s, "ghbdtn ")
    assert s.text == "привет "
    press_hotkey(c)
    assert s.text == "ghbdtn "
    assert "ghbdtn" in c.config.exclusions and s.saved == 1
    type_keys(c, s, "ghbdtn ")
    assert s.text == "ghbdtn ghbdtn "


def test_shortcuts_and_navigation_reset_buffer():
    c, s = make()
    type_keys(c, s, "ghbdtn")
    c.on_key(KC_RETURN, "\r", frozenset())
    press_hotkey(c)
    assert s.text == "ghbdtn"
