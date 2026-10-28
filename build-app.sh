#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Antigravity 汉化助手.app 一键编译打包脚本
# 产出：
#   dist/Antigravity 汉化助手.app       (Universal 双架构: Apple Silicon + Intel)
#   dist/Antigravity-汉化助手-macOS.zip (可直接分发给其他 Mac 的压缩包)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
APP_NAME="Antigravity 汉化助手.app"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}"
ZIP_OUT="${DIST_DIR}/Antigravity-汉化助手-macOS.zip"

echo "[1/4] 清理并创建构建目录: ${DIST_DIR}"
rm -rf "${APP_BUNDLE}" "${ZIP_OUT}"
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

echo "[2/4] 编译 macOS Universal 通用架构启动器 (arm64 + x86_64)..."
cc -O2 -arch arm64 -arch x86_64 -framework Cocoa \
  "${SCRIPT_DIR}/macos-app/launcher.m" \
  -o "${APP_BUNDLE}/Contents/MacOS/launcher"

echo "[3/4] 写入应用资源与词典..."
cp "${SCRIPT_DIR}/macos-app/Info.plist" "${APP_BUNDLE}/Contents/Info.plist"
cp "${SCRIPT_DIR}/patch.py" "${APP_BUNDLE}/Contents/Resources/patch.py"
cp "${SCRIPT_DIR}/runtime-i18n.js" "${APP_BUNDLE}/Contents/Resources/runtime-i18n.js"
cp "${SCRIPT_DIR}/zh-CN.json" "${APP_BUNDLE}/Contents/Resources/zh-CN.json"
chmod +x "${APP_BUNDLE}/Contents/Resources/patch.py"

if [ -f "/Applications/Antigravity.app/Contents/Resources/icon.icns" ]; then
  cp "/Applications/Antigravity.app/Contents/Resources/icon.icns" "${APP_BUNDLE}/Contents/Resources/icon.icns"
elif [ -f "${SCRIPT_DIR}/macos-app/icon.icns" ]; then
  cp "${SCRIPT_DIR}/macos-app/icon.icns" "${APP_BUNDLE}/Contents/Resources/icon.icns"
fi

echo "[4/4] 对应用包进行重签名并生成可分发压缩包..."
codesign --force --deep --sign - "${APP_BUNDLE}"
ditto -c -k --sequesterRsrc --keepParent "${APP_BUNDLE}" "${ZIP_OUT}"

echo ""
echo "[✓] 打包完成！"
echo "  - 应用路径: ${APP_BUNDLE}"
echo "  - 分发压缩包: ${ZIP_OUT}"
