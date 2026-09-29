"""Иконка в строке меню (rumps) и связка с macOS."""

import logging
import subprocess
import time

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from PyObjCTools import AppHelper

from . import autostart, macos
from .config import CONFIG_PATH, Config, parse_hotkey
from .service import Corrector

log = logging.getLogger(__name__)

SETTINGS_URLS = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
)


class MacSystem:
    """Реализация операций для Corrector поверх macOS."""

    def __init__(self):
        self.clipboard = macos.Clipboard()

    ru_variant = staticmethod(macos.detect_ru_variant)
    frontmost_bundle_id = staticmethod(macos.frontmost_bundle_id)
    type_text = staticmethod(macos.type_text)
    wait_modifiers_released = staticmethod(macos.wait_modifiers_released)

    def press_backspace(self, n):
        macos.press(macos.KC_BACKSPACE, times=n)

    def selected_text(self):
        text = macos.selected_text_ax()
        if text is not None:
            return text
        # Приложение не поддерживает Accessibility — пробуем через ⌘C.
        snapshot = self.clipboard.snapshot()
        text = macos.copy_selection(self.clipboard)
        if text is None:
            return None
        self.clipboard.restore(snapshot)
        # Редакторы кода копируют всю строку, если ничего не выделено.
        if text.endswith("\n") and text.count("\n") == 1:
            return None
        return text

    def replace_selection(self, text):
        snapshot = self.clipboard.snapshot()
        self.clipboard.set_text(text)
        macos.press(macos.KC_V, ("cmd",))
        time.sleep(0.3)  # даём приложению прочитать буфер
        self.clipboard.restore(snapshot)

    def reselect(self, length):
        macos.press(macos.KC_LEFT, ("shift",), times=length)

    def select_language(self, lang):
        AppHelper.callAfter(macos.select_language, lang)

    def save_config(self, config):
        config.save()


FIX_KEY = "Исправить выделенное"


class LayoutFixApp(rumps.App):
    def __init__(self):
        super().__init__("LayoutFix", title="⇄", quit_button=None)
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self.config = Config.load()
        checker = None
        try:
            checker = macos.SpellChecker()
        except Exception:
            log.exception("system spell checker unavailable, using built-in word lists")
        self.corrector = Corrector(self.config, MacSystem(), checker)
        self.tap = macos.KeyTap(self.corrector.on_key, self.corrector.on_mouse)

        self.fix_item = rumps.MenuItem(FIX_KEY, callback=self.fix_selection)
        self.auto_item = rumps.MenuItem("Автоисправление при вводе", callback=self.toggle_auto)
        self.switch_item = rumps.MenuItem("Переключать раскладку после исправления",
                                          callback=self.toggle_switch)
        self.login_item = rumps.MenuItem("Запускать при входе в систему", callback=self.toggle_login)
        self.perm_item = rumps.MenuItem("⚠️ Выдать разрешения…", callback=self.request_permissions)
        self.menu = [
            self.fix_item,
            None,
            self.auto_item,
            self.switch_item,
            rumps.MenuItem("Изменить хоткей…", callback=self.change_hotkey),
            None,
            rumps.MenuItem("Открыть файл настроек", callback=self.open_config),
            rumps.MenuItem("Перечитать настройки", callback=self.reload_config),
            self.login_item,
            None,
            rumps.MenuItem("Выход", callback=rumps.quit_application),
        ]
        self.refresh_menu()
        self._prompted = False
        self.retry_timer = rumps.Timer(self.try_start_tap, 3)
        if not self.try_start_tap(None):
            self.retry_timer.start()

    # ------------------------------------------------------------ state

    def refresh_menu(self):
        self.fix_item.title = f"{FIX_KEY} / последнее слово   {self.corrector.hotkey.label()}"
        self.auto_item.state = int(self.config.auto_correct)
        self.switch_item.state = int(self.config.switch_layout)
        self.login_item.state = int(autostart.is_enabled())

    def try_start_tap(self, timer):
        """Запустить перехват клавиш; пока нет разрешений — повторять по таймеру."""
        if self.tap.tap is None and macos.has_accessibility():
            self.tap.start()
        if self.tap.tap is not None:
            log.info("keyboard tap started")
            self.title = "⇄"
            self.retry_timer.stop()
            if self.perm_item.title in self.menu:
                del self.menu[self.perm_item.title]
            return True
        self.title = "⇄!"
        if self.perm_item.title not in self.menu:
            self.menu.insert_before(FIX_KEY, self.perm_item)
        if timer is not None and not self._prompted:
            self._prompted = True
            self.request_permissions(None)
        return False

    # ------------------------------------------------------------ actions

    def request_permissions(self, _):
        macos.has_accessibility(prompt=True)
        macos.has_input_monitoring(prompt=True)
        rumps.alert(
            "LayoutFix: нужны разрешения",
            "Откройте «Системные настройки → Конфиденциальность и безопасность» и "
            "включите LayoutFix (Python / Терминал) в разделах «Универсальный доступ» "
            "и «Мониторинг ввода». Приложение подхватит разрешения автоматически.")
        for url in SETTINGS_URLS:
            subprocess.run(["open", url], check=False)

    def fix_selection(self, _):
        self.corrector.fix_selection_from_menu()

    def toggle_auto(self, _):
        self.config.auto_correct = not self.config.auto_correct
        self.save()

    def toggle_switch(self, _):
        self.config.switch_layout = not self.config.switch_layout
        self.save()

    def toggle_login(self, _):
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()
        self.refresh_menu()

    def change_hotkey(self, _):
        window = rumps.Window(
            message="Например: alt+space, ctrl+shift+z, cmd+alt+k, f13",
            title="Хоткей исправления раскладки",
            default_text=self.config.hotkey,
            ok="Сохранить", cancel="Отмена", dimensions=(240, 24))
        response = window.run()
        if not response.clicked:
            return
        try:
            parse_hotkey(response.text)
        except ValueError as e:
            rumps.alert("Неверный хоткей", str(e))
            return
        self.config.hotkey = response.text.strip().lower()
        self.save()

    def open_config(self, _):
        self.config.save()
        subprocess.run(["open", "-t", CONFIG_PATH], check=False)

    def reload_config(self, _):
        self.config = Config.load()
        self.corrector.config = self.config
        self.corrector.reload()
        self.refresh_menu()

    def save(self):
        self.config.save()
        self.corrector.reload()
        self.refresh_menu()


def run():
    LayoutFixApp().run()
