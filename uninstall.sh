#!/bin/bash
# Удаление LayoutFix. Настройки сохраняются, если не передан --purge.
set -uo pipefail
LABEL="com.layoutfix.agent"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
rm -rf "$HOME/.layoutfix"
if [[ "${1:-}" == "--purge" ]]; then
    rm -rf "$HOME/Library/Application Support/LayoutFix" "$HOME/Library/Logs/LayoutFix.log"
fi
echo "LayoutFix удалён. Разрешения можно убрать в Системных настройках вручную."
