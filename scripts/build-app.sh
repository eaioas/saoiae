#!/usr/bin/env bash
# Собирает универсальный (Apple Silicon + Intel) MenuHider.app в папку dist/.
# Использование: ./scripts/build-app.sh
# Для подписи своим сертификатом: CODESIGN_IDENTITY="Developer ID Application: ..." ./scripts/build-app.sh
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="MenuHider"
BUILD_FLAGS=(-c release --arch arm64 --arch x86_64)

swift build "${BUILD_FLAGS[@]}"
BIN_DIR="$(swift build "${BUILD_FLAGS[@]}" --show-bin-path)"

APP="dist/$APP_NAME.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_DIR/$APP_NAME" "$APP/Contents/MacOS/$APP_NAME"
cp App/Info.plist "$APP/Contents/Info.plist"

# "-" — ad-hoc подпись: достаточно для запуска на своём маке.
codesign --force --sign "${CODESIGN_IDENTITY:--}" "$APP"

echo "Готово: $APP"
