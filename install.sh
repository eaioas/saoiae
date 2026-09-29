#!/bin/bash
# Установка LayoutFix: venv + зависимости + автозапуск через LaunchAgent.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "LayoutFix работает только на macOS" >&2
    exit 1
fi

VENV="$HOME/.layoutfix/venv"
LABEL="com.layoutfix.agent"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "→ Создаю окружение в $VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

echo "→ Настраиваю автозапуск"
"$VENV/bin/python" main.py --install-agent >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

REAL_PY="$("$VENV/bin/python" -c 'import sys, os; print(os.path.realpath(sys.executable))')"
cat <<MSG

✅ LayoutFix запущен — ищите значок ⇄ в строке меню.

Выдайте разрешения в «Системные настройки → Конфиденциальность и безопасность»:
  • Универсальный доступ (Accessibility)
  • Мониторинг ввода (Input Monitoring)
Если Python не появился в списке сам, добавьте кнопкой «+» (⇧⌘G, чтобы вставить путь):
  $REAL_PY

Лог: ~/Library/Logs/LayoutFix.log
MSG
