#!/usr/bin/env python3
"""Точка входа LayoutFix.

    python main.py                  — запустить (иконка ⇄ в строке меню)
    python main.py --install-agent  — создать LaunchAgent для автозапуска
    python main.py --remove-agent   — удалить LaunchAgent
    python main.py --convert TEXT   — перевести текст в другую раскладку и выйти
"""

import argparse
import fcntl
import logging
import os
import sys

LOCK_PATH = os.path.expanduser("~/Library/Application Support/LayoutFix/.lock")


def single_instance():
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    handle = open(LOCK_PATH, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("LayoutFix уже запущен", file=sys.stderr)
        sys.exit(0)
    return handle


def main():
    parser = argparse.ArgumentParser(description="LayoutFix: исправление раскладки RU ⇄ EN")
    parser.add_argument("--install-agent", action="store_true")
    parser.add_argument("--remove-agent", action="store_true")
    parser.add_argument("--convert", metavar="TEXT")
    parser.add_argument("--variant", choices=["pc", "mac"], default="pc")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.convert is not None:
        from layoutfix.mapping import convert
        print(convert(args.convert, args.variant)[0])
        return

    from layoutfix import autostart
    if args.install_agent:
        autostart.enable()
        print(autostart.PLIST_PATH)
        return
    if args.remove_agent:
        autostart.disable()
        return

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    lock = single_instance()  # noqa: F841 — держим файл открытым всё время работы
    from layoutfix.app import run
    run()


if __name__ == "__main__":
    main()
