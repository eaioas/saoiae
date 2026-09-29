"""Буфер набираемого слова: что пользователь напечатал с последней границы."""

import threading


class WordTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.current = ""        # слово, которое набирается сейчас
        self.last_word = ""      # предыдущее законченное слово
        self.spaces_after = 0    # сколько пробелов набрано после last_word

    def reset(self):
        with self._lock:
            self.current = ""
            self.last_word = ""
            self.spaces_after = 0

    def type_char(self, ch):
        with self._lock:
            if not self.current:
                self.last_word, self.spaces_after = "", 0
            self.current += ch

    def backspace(self):
        with self._lock:
            if self.current:
                self.current = self.current[:-1]
            elif self.spaces_after:
                self.spaces_after -= 1
                if self.spaces_after == 0:
                    self.current, self.last_word = self.last_word, ""
            else:
                self.last_word = ""

    def space(self):
        """Пробел. Возвращает только что законченное слово (или пустую строку)."""
        with self._lock:
            if self.current:
                self.last_word, self.current = self.current, ""
                self.spaces_after = 1
                return self.last_word
            if self.last_word:
                self.spaces_after += 1
            return ""

    def take_last(self):
        """
        Слово для исправления по хоткею без выделения.
        Возвращает (слово, число_пробелов_после_него) или ("", 0).
        """
        with self._lock:
            if self.current:
                return self.current, 0
            if self.last_word:
                return self.last_word, self.spaces_after
            return "", 0

    def replace_last(self, new_word):
        """Отметить, что последнее слово было заменено на ``new_word``."""
        with self._lock:
            if self.current:
                self.current = new_word
            elif self.last_word:
                self.last_word = new_word
