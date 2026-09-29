"""Настройки приложения и разбор строки хоткея."""

import json
import os
from dataclasses import asdict, dataclass, field

CONFIG_DIR = os.path.expanduser("~/Library/Application Support/LayoutFix")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Виртуальные коды клавиш macOS (ANSI), не зависят от раскладки.
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8,
    "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25,
    "7": 26, "-": 27, "8": 28, "0": 29, "]": 30, "o": 31, "u": 32, "[": 33,
    "i": 34, "p": 35, "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42,
    ",": 43, "/": 44, "n": 45, "m": 46, ".": 47, "`": 50,
    "return": 36, "tab": 48, "space": 49, "delete": 51, "escape": 53,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "f13": 105, "f14": 107, "f15": 113,
}

MODIFIERS = {
    "cmd": "cmd", "command": "cmd", "⌘": "cmd",
    "ctrl": "ctrl", "control": "ctrl", "⌃": "ctrl",
    "alt": "alt", "option": "alt", "opt": "alt", "⌥": "alt",
    "shift": "shift", "⇧": "shift",
}

MODIFIER_SYMBOLS = {"ctrl": "⌃", "alt": "⌥", "shift": "⇧", "cmd": "⌘"}


@dataclass(frozen=True)
class Hotkey:
    keycode: int
    modifiers: frozenset
    text: str

    def label(self):
        mods = "".join(MODIFIER_SYMBOLS[m] for m in MODIFIER_SYMBOLS if m in self.modifiers)
        key = self.text.split("+")[-1].strip()
        return mods + (key.capitalize() if len(key) > 1 else key.upper())


def parse_hotkey(text):
    """``"alt+space"`` -> Hotkey. Бросает ValueError при ошибке."""
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if not parts:
        raise ValueError("пустой хоткей")
    *mods, key = parts
    unknown = [m for m in mods if m not in MODIFIERS]
    if unknown:
        raise ValueError(f"неизвестный модификатор: {unknown[0]}")
    if key not in KEYCODES:
        raise ValueError(f"неизвестная клавиша: {key}")
    modifiers = frozenset(MODIFIERS[m] for m in mods)
    if not modifiers and not key.startswith("f"):
        raise ValueError("нужен хотя бы один модификатор (cmd/ctrl/alt/shift)")
    return Hotkey(KEYCODES[key], modifiers, "+".join(parts))


DEFAULT_EXCLUDED_APPS = [
    "com.apple.Terminal",
    "com.googlecode.iterm2",
    "dev.warp.Warp-Stable",
    "net.kovidgoyal.kitty",
    "com.microsoft.VSCode",
    "com.jetbrains.intellij",
    "com.jetbrains.pycharm",
    "com.1password.1password",
    "com.apple.keychainaccess",
]


@dataclass
class Config:
    hotkey: str = "alt+space"
    auto_correct: bool = False
    switch_layout: bool = True
    ru_variant: str = "auto"          # "auto", "pc" или "mac"
    min_word_length: int = 3
    exclusions: list = field(default_factory=list)
    excluded_apps: list = field(default_factory=lambda: list(DEFAULT_EXCLUDED_APPS))

    @classmethod
    def load(cls, path=CONFIG_PATH):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        cfg = cls(**known)
        try:
            parse_hotkey(cfg.hotkey)
        except ValueError:
            cfg.hotkey = cls.hotkey
        return cfg

    def save(self, path=CONFIG_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
