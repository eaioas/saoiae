#!/usr/bin/env bash
# Сборка IPInfo.app.
#   ./build.sh            — собрать в build/IPInfo.app
#   ./build.sh install    — собрать, скопировать в /Applications и запустить
#   UNIVERSAL=1 ./build.sh — универсальная сборка (Apple Silicon + Intel, нужен Xcode)
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="IPInfo"
APP_DIR="build/${APP_NAME}.app"

ARCH_FLAGS=""
if [[ "${UNIVERSAL:-0}" == "1" ]]; then
    ARCH_FLAGS="--arch arm64 --arch x86_64"
fi

echo "==> swift build"
# shellcheck disable=SC2086
swift build -c release $ARCH_FLAGS
# shellcheck disable=SC2086
BIN_DIR="$(swift build -c release $ARCH_FLAGS --show-bin-path)"

echo "==> Собираем ${APP_DIR}"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$BIN_DIR/$APP_NAME" "$APP_DIR/Contents/MacOS/$APP_NAME"
cp Resources/Info.plist "$APP_DIR/Contents/Info.plist"

echo "==> Подпись (ad-hoc)"
codesign --force --sign - "$APP_DIR"

echo "Готово: $APP_DIR"

if [[ "${1:-}" == "install" ]]; then
    echo "==> Установка в /Applications"
    pkill -x "$APP_NAME" 2>/dev/null || true
    rm -rf "/Applications/${APP_NAME}.app"
    cp -R "$APP_DIR" /Applications/
    open "/Applications/${APP_NAME}.app"
    echo "Запущено. Иконка 🌐 появилась в меню-баре."
fi
