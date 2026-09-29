"""Всё, что зависит от macOS: перехват клавиш, отправка нажатий, буфер обмена,
Accessibility, переключение раскладки и системная проверка орфографии."""

import logging
import threading
import time

import objc
import Quartz
from AppKit import (NSPasteboard, NSPasteboardItem, NSPasteboardTypeString,
                    NSSpellChecker, NSWorkspace)
from CoreFoundation import (CFMachPortCreateRunLoopSource, CFRunLoopAddSource,
                            CFRunLoopGetCurrent, CFRunLoopRun, kCFRunLoopCommonModes)
from Foundation import NSBundle, NSNotFound

log = logging.getLogger(__name__)

MAGIC = 0x4C46_4958  # помечаем свои события, чтобы не обрабатывать их повторно

KC_SPACE = 49
KC_BACKSPACE = 51
KC_C = 8
KC_V = 9
KC_LEFT = 123

FLAG_BITS = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "shift": Quartz.kCGEventFlagMaskShift,
}


def modifiers_from_flags(flags):
    return frozenset(name for name, bit in FLAG_BITS.items() if flags & bit)


# ---------------------------------------------------------------- permissions

def has_accessibility(prompt=False):
    from ApplicationServices import (AXIsProcessTrustedWithOptions,
                                     kAXTrustedCheckOptionPrompt)
    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))


def has_input_monitoring(prompt=False):
    preflight = getattr(Quartz, "CGPreflightListenEventAccess", None)
    if preflight is None:
        return True
    if preflight():
        return True
    if prompt and hasattr(Quartz, "CGRequestListenEventAccess"):
        Quartz.CGRequestListenEventAccess()
    return False


# ---------------------------------------------------------------- key events

_source = None


def _event_source():
    global _source
    if _source is None:
        _source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStatePrivate)
    return _source


def _post(event, flags):
    Quartz.CGEventSetFlags(event, flags)
    Quartz.CGEventSetIntegerValueField(event, Quartz.kCGEventSourceUserData, MAGIC)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def press(keycode, modifiers=(), times=1):
    flags = 0
    for m in modifiers:
        flags |= FLAG_BITS[m]
    for _ in range(times):
        for down in (True, False):
            _post(Quartz.CGEventCreateKeyboardEvent(_event_source(), keycode, down), flags)
        time.sleep(0.002)


def type_text(text):
    for ch in text:
        if ch == " ":
            press(KC_SPACE)
            continue
        units = len(ch.encode("utf-16-le")) // 2
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(_event_source(), 0, down)
            Quartz.CGEventKeyboardSetUnicodeString(ev, units, ch)
            _post(ev, 0)
        time.sleep(0.002)


def wait_modifiers_released(timeout=1.0):
    """Ждём, пока пользователь отпустит модификаторы хоткея."""
    mask = 0
    for bit in FLAG_BITS.values():
        mask |= bit
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateHIDSystemState)
        if not flags & mask:
            return
        time.sleep(0.01)


# ---------------------------------------------------------------- event tap

class KeyTap:
    """
    Глобальный перехват нажатий через CGEventTap в отдельном потоке.

    ``on_key(keycode, chars, modifiers) -> bool`` — True, чтобы «проглотить» нажатие.
    ``on_mouse()`` — клик мышью (курсор мог переместиться).
    """

    def __init__(self, on_key, on_mouse):
        self.on_key = on_key
        self.on_mouse = on_mouse
        self.tap = None
        self._ready = threading.Event()
        self._callback = self._handle  # держим ссылку, чтобы не собрал GC

    def start(self):
        self._ready.clear()
        threading.Thread(target=self._run, name="KeyTap", daemon=True).start()
        self._ready.wait(2)
        return self.tap is not None

    def _run(self):
        mask = (Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDown))
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault, mask, self._callback, None)
        if self.tap is None:
            log.error("CGEventTapCreate failed: no Accessibility/Input Monitoring permission")
            self._ready.set()
            return
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self.tap, True)
        self._ready.set()
        CFRunLoopRun()

    def _handle(self, proxy, etype, event, refcon):
        if etype in (Quartz.kCGEventTapDisabledByTimeout,
                     Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(self.tap, True)
            return event
        if Quartz.CGEventGetIntegerValueField(event, Quartz.kCGEventSourceUserData) == MAGIC:
            return event
        try:
            if etype != Quartz.kCGEventKeyDown:
                self.on_mouse()
                return event
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            mods = modifiers_from_flags(Quartz.CGEventGetFlags(event))
            result = Quartz.CGEventKeyboardGetUnicodeString(event, 4, None, None)
            chars = next((r for r in result if isinstance(r, str)), "") if isinstance(result, tuple) else ""
            if self.on_key(keycode, chars or "", mods):
                return None
        except Exception:
            log.exception("key handler failed")
        return event


# ---------------------------------------------------------------- clipboard

class Clipboard:
    def __init__(self):
        self.pb = NSPasteboard.generalPasteboard()

    def change_count(self):
        return self.pb.changeCount()

    def text(self):
        return self.pb.stringForType_(NSPasteboardTypeString)

    def set_text(self, text):
        self.pb.clearContents()
        self.pb.setString_forType_(text, NSPasteboardTypeString)

    def snapshot(self):
        items = []
        for item in self.pb.pasteboardItems() or []:
            items.append({t: item.dataForType_(t) for t in item.types()})
        return items

    def restore(self, snapshot):
        self.pb.clearContents()
        objects = []
        for data_by_type in snapshot:
            item = NSPasteboardItem.alloc().init()
            for t, data in data_by_type.items():
                if data is not None:
                    item.setData_forType_(data, t)
            objects.append(item)
        if objects:
            self.pb.writeObjects_(objects)


def selected_text_ax():
    """Выделенный текст через Accessibility. ``None`` — если приложение не отдаёт."""
    try:
        from ApplicationServices import (AXUIElementCopyAttributeValue,
                                         AXUIElementCreateSystemWide,
                                         kAXFocusedUIElementAttribute,
                                         kAXSelectedTextAttribute)
        system = AXUIElementCreateSystemWide()
        err, focused = AXUIElementCopyAttributeValue(system, kAXFocusedUIElementAttribute, None)
        if err or focused is None:
            return None
        err, selected = AXUIElementCopyAttributeValue(focused, kAXSelectedTextAttribute, None)
        if err or selected is None:
            return None
        return str(selected)
    except Exception:
        log.debug("AX selected text unavailable", exc_info=True)
        return None


def copy_selection(clipboard, timeout=0.4):
    """Скопировать выделение через ⌘C. ``None`` — если буфер не изменился."""
    before = clipboard.change_count()
    press(KC_C, ("cmd",))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if clipboard.change_count() != before:
            return clipboard.text()
        time.sleep(0.01)
    return None


def frontmost_bundle_id():
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    return app.bundleIdentifier() if app is not None else None


# ---------------------------------------------------------------- input sources

_tis = {}


def _load_tis():
    if _tis:
        return _tis
    bundle = NSBundle.bundleWithIdentifier_("com.apple.HIToolbox")
    objc.loadBundleFunctions(bundle, _tis, [
        ("TISCreateInputSourceList", b"@@Z"),
        ("TISCopyCurrentKeyboardInputSource", b"@"),
        ("TISSelectInputSource", b"i@"),
        ("TISGetInputSourceProperty", b"@@@"),
    ])
    objc.loadBundleVariables(bundle, _tis, [
        ("kTISPropertyInputSourceID", b"@"),
        ("kTISPropertyInputSourceLanguages", b"@"),
        ("kTISPropertyInputSourceCategory", b"@"),
        ("kTISPropertyInputSourceIsSelectCapable", b"@"),
        ("kTISCategoryKeyboardInputSource", b"@"),
    ])
    return _tis


def _keyboard_sources():
    """(id, основной язык, источник) для всех включённых раскладок."""
    t = _load_tis()
    result = []
    for src in t["TISCreateInputSourceList"](None, False) or []:
        prop = lambda key: t["TISGetInputSourceProperty"](src, t[key])  # noqa: E731
        if prop("kTISPropertyInputSourceCategory") != t["kTISCategoryKeyboardInputSource"]:
            continue
        if not prop("kTISPropertyInputSourceIsSelectCapable"):
            continue
        langs = prop("kTISPropertyInputSourceLanguages") or []
        result.append((str(prop("kTISPropertyInputSourceID")), str(langs[0]) if langs else "", src))
    return result


def detect_ru_variant():
    """``pc`` для «Русская – ПК», ``mac`` для стандартной «Русская»."""
    try:
        for source_id, lang, _ in _keyboard_sources():
            if lang == "ru":
                return "pc" if source_id.endswith("RussianWin") else "mac"
    except Exception:
        log.exception("cannot read input sources")
    return "pc"


_PREFERRED_EN = ("com.apple.keylayout.ABC", "com.apple.keylayout.US")


def select_language(lang):
    """Переключить раскладку на первую включённую с языком ``lang`` (ru/en).
    Вызывать из главного потока."""
    try:
        sources = [s for s in _keyboard_sources() if s[1] == lang]
        sources.sort(key=lambda s: s[0] not in _PREFERRED_EN)
        if sources:
            _load_tis()["TISSelectInputSource"](sources[0][2])
            return True
    except Exception:
        log.exception("cannot switch input source")
    return False


# ---------------------------------------------------------------- spelling

class SpellChecker:
    """Проверка «настоящее ли это слово» через системный NSSpellChecker."""

    def __init__(self):
        self._checker = NSSpellChecker.sharedSpellChecker()
        available = [str(x) for x in self._checker.availableLanguages()]
        self.languages = {}
        for lang in ("ru", "en"):
            exact = [a for a in available if a == lang]
            prefixed = [a for a in available if a.startswith(lang + "_")]
            if exact or prefixed:
                self.languages[lang] = (exact or prefixed)[0]
        self._lock = threading.Lock()
        log.info("spell checker languages: %s", self.languages)

    def __call__(self, word, lang):
        code = self.languages.get(lang)
        if not code:
            return False
        with self._lock:
            rng, _count = self._checker.checkSpellingOfString_startingAt_language_wrap_inSpellDocumentWithTag_wordCount_(
                word, 0, code, False, 0, None)
        location = rng.location if hasattr(rng, "location") else rng[0]
        return location == NSNotFound
