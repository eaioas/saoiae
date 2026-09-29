"""Логика исправления: реакция на нажатия, хоткей, автоисправление.

Зависимости от macOS передаются через объект ``system`` (см. ``MacSystem``
в app.py), поэтому логику можно тестировать с подделкой.
"""

import logging
import queue
import threading

from . import mapping
from .config import parse_hotkey
from .detector import Detector, _core
from .tracker import WordTracker

log = logging.getLogger(__name__)

KC_SPACE = 49
KC_BACKSPACE = 51
# Клавиши, после которых позиция курсора неизвестна: Enter, Tab, Esc,
# стрелки, Home/End, PgUp/PgDn, Forward Delete, Enter на цифровом блоке.
RESET_KEYCODES = {36, 48, 53, 76, 115, 116, 117, 119, 121, 123, 124, 125, 126}

MAX_RESELECT = 300


class Corrector:
    def __init__(self, config, system, checker=None):
        self.config = config
        self.system = system
        self.tracker = WordTracker()
        self.checker = checker
        self.variant = "pc"
        self.detector = None
        self.hotkey = None
        self.last_auto = None  # (исходное, исправленное) последнего автоисправления
        self._jobs = queue.Queue()
        threading.Thread(target=self._worker, name="Corrector", daemon=True).start()
        self.reload()

    def reload(self):
        cfg = self.config
        self.variant = self.system.ru_variant() if cfg.ru_variant == "auto" else cfg.ru_variant
        if self.variant not in mapping.VARIANTS:
            self.variant = "pc"
        self.detector = Detector(self.variant, self.checker, cfg.min_word_length, cfg.exclusions)
        self.hotkey = parse_hotkey(cfg.hotkey)

    # ------------------------------------------------------------ key events

    def on_mouse(self):
        self.tracker.reset()

    def on_key(self, keycode, chars, mods):
        """Вызывается из потока перехвата. True — «проглотить» нажатие."""
        if keycode == self.hotkey.keycode and mods == self.hotkey.modifiers:
            self._jobs.put(self.fix_on_hotkey)
            return True
        if mods & {"cmd", "ctrl"}:
            self.tracker.reset()
            return False
        if keycode == KC_BACKSPACE:
            self.tracker.backspace()
            return False
        if keycode == KC_SPACE:
            word = self.tracker.space()
            if word and self.config.auto_correct and "alt" not in mods:
                return self._auto_fix(word)
            return False
        if keycode in RESET_KEYCODES:
            self.tracker.reset()
            return False
        if len(chars) == 1 and chars.isprintable():
            self.tracker.type_char(chars)
        else:
            self.tracker.reset()
        return False

    def _auto_fix(self, word):
        if self.system.frontmost_bundle_id() in self.config.excluded_apps:
            return False
        fixed = self.detector.fix(word)
        if not fixed:
            return False
        log.info("auto: %r -> %r", word, fixed)
        # Пробел проглочен: стираем слово и печатаем исправленное вместе с пробелом.
        self.system.press_backspace(len(word))
        self.system.type_text(fixed + " ")
        self.tracker.replace_last(fixed)
        self.last_auto = (word, fixed)
        self._switch_layout(fixed)
        return True

    # ------------------------------------------------------------ hotkey

    def _worker(self):
        while True:
            job = self._jobs.get()
            try:
                job()
            except Exception:
                log.exception("correction failed")
            finally:
                self._jobs.task_done()

    def fix_on_hotkey(self):
        self.system.wait_modifiers_released()
        if not self._fix_selection():
            self._fix_last_word()

    def fix_selection_from_menu(self):
        self._jobs.put(self._fix_selection)

    def _fix_selection(self):
        text = self.system.selected_text()
        if not text:
            return False
        converted, direction = mapping.convert(text, self.variant)
        if direction is None or converted == text:
            return True
        log.info("selection: %r -> %r", text, converted)
        self.system.replace_selection(converted)
        if len(converted) <= MAX_RESELECT:
            self.system.reselect(len(converted))
        self.tracker.reset()
        self._switch_layout(converted)
        return True

    def _fix_last_word(self):
        word, spaces = self.tracker.take_last()
        if not word:
            return
        converted, direction = mapping.convert(word, self.variant)
        if direction is None or converted == word:
            return
        log.info("last word: %r -> %r", word, converted)
        self.system.press_backspace(len(word) + spaces)
        self.system.type_text(converted + " " * spaces)
        self.tracker.replace_last(converted)
        self._learn_from_undo(word)
        self._switch_layout(converted)

    def _learn_from_undo(self, word):
        """Пользователь отменил автоисправление хоткеем — больше так не делаем."""
        if not self.last_auto or self.last_auto[1] != word:
            return
        original = self.last_auto[0]
        _, direction = mapping.convert(original, self.variant)
        key = _core(original, "en" if direction == "en->ru" else "ru").lower() or original.lower()
        self.last_auto = None
        if key not in self.config.exclusions:
            self.config.exclusions.append(key)
            self.system.save_config(self.config)
            self.detector.exclusions.add(key)
            log.info("learned exclusion %r", key)

    def _switch_layout(self, text):
        if not self.config.switch_layout:
            return
        direction = mapping.detect_direction(text)
        if direction:
            # Раскладку, в которой теперь написан текст, и включаем.
            self.system.select_language("ru" if direction == "ru->en" else "en")
