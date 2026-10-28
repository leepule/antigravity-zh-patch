#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity.app 简体中文汉化补丁工具 (纯 Python 3 标准库实现，零第三方依赖)
支持：
  python3 patch.py install           [--app /Applications/Antigravity.app] [--no-sign]
  python3 patch.py restore           [--app /Applications/Antigravity.app] [--no-sign]
  python3 patch.py status            [--app /Applications/Antigravity.app]
  python3 patch.py json-status       [--app /Applications/Antigravity.app]
  python3 patch.py prepare-user-dict
"""

import argparse
import hashlib
import json
import plistlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path

BLOCK_SIZE = 4 * 1024 * 1024  # 4MB per block for Electron ASAR integrity
PATCH_MARKER = "/* __ANTIGRAVITY_ZH_PATCH_APPLIED__ */"

BASE_DIR = Path(__file__).resolve().parent
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "AntigravityZhPatcher"
USER_DICT_PATH = APP_SUPPORT_DIR / "zh-CN.json"
BUNDLED_DICT_PATH = BASE_DIR / "zh-CN.json"
RUNTIME_I18N_PATH = BASE_DIR / "runtime-i18n.js"
BACKUP_ROOT_DIR = APP_SUPPORT_DIR / "backups"


def resolve_dict_path() -> Path:
    """优先使用用户在 Application Support 中自定义的词典，否则使用内置词典。"""
    if USER_DICT_PATH.exists():
        return USER_DICT_PATH
    return BUNDLED_DICT_PATH


def get_version_backup_dir(version: str) -> Path:
    """按版本号隔离每台 Mac 本机的原版备份，避免跨机器或跨版本升级污染。"""
    safe_ver = version if version and version != "未知" else "default"
    return BACKUP_ROOT_DIR / safe_ver


def compute_integrity(data: bytes) -> dict:
    """计算 Electron ASAR 规范要求的 SHA256 与 4MB 分块校验值。"""
    full_hash = hashlib.sha256(data).hexdigest()
    blocks = []
    if len(data) == 0:
        blocks.append(full_hash)
    else:
        for i in range(0, len(data), BLOCK_SIZE):
            chunk = data[i : i + BLOCK_SIZE]
            blocks.append(hashlib.sha256(chunk).hexdigest())
    return {
        "algorithm": "SHA256",
        "hash": full_hash,
        "blockSize": BLOCK_SIZE,
        "blocks": blocks,
    }


def read_asar(asar_path: Path):
    """读取 ASAR 文件，返回 (header_dict, base_offset, raw_bytes, header_sha256)。"""
    raw = asar_path.read_bytes()
    u0, header_size, u1, json_size = struct.unpack("<4I", raw[:16])
    header_bytes = raw[16 : 16 + json_size]
    header_sha256 = hashlib.sha256(header_bytes).hexdigest()
    header = json.loads(header_bytes.decode("utf-8"))
    base_offset = 8 + header_size
    return header, base_offset, raw, header_sha256


def is_asar_patched(asar_path: Path) -> bool:
    """检查目标 app.asar 是否已经打过汉化补丁。"""
    try:
        header, base_offset, raw, _ = read_asar(asar_path)
        preload_node = header["files"]["dist"]["files"]["preload.js"]
        offset = base_offset + int(preload_node["offset"])
        size = int(preload_node["size"])
        content = raw[offset : offset + size].decode("utf-8", errors="ignore")
        return PATCH_MARKER in content
    except Exception:
        return False


def patch_main_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    out = src + f"\n{PATCH_MARKER}\n"
    target_switch = "electron_1.app.commandLine.appendSwitch('disable-blink-features', 'AutomationControlled');"
    out = out.replace(
        target_switch,
        target_switch + "\nelectron_1.app.commandLine.appendSwitch('lang', 'zh-CN');",
    )
    replacements = [
        ("label: 'New Window'", "label: '新建窗口'"),
        ("label: 'No agents running'", "label: '无运行中的智能体'"),
        ("label: `Open ${electron_1.app.getName()}`", "label: `打开 ${electron_1.app.getName()}`"),
        ("label: 'Quit'", "label: '退出'"),
        ("buttons: ['Cancel', 'Quit']", "buttons: ['取消', '退出']"),
        ("title: 'Confirm Quit'", "title: '确认退出'"),
        ("message: 'Are you sure you want to quit?'", "message: '确定要退出吗？'"),
        (
            "detail: 'There may be agents or background tasks running.'",
            "detail: '当前可能有正在运行的智能体或后台任务。'",
        ),
        ("showErrorBox('Binary not found'", "showErrorBox('未找到二进制文件'"),
        ("showErrorBox('Startup failed'", "showErrorBox('启动失败'"),
        ("title: 'WSL distro not found'", "title: '未找到 WSL 发行版'"),
        ("detail: 'Antigravity opened on Windows instead.'", "detail: '已改为在 Windows 本地打开 Antigravity。'"),
    ]
    for old, new in replacements:
        out = out.replace(old, new)
    return out


def patch_menu_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    old_fn = """function setupApplicationMenu(url) {
    const menu = electron_1.Menu.getApplicationMenu();
    if (!menu) {
        return;
    }
    // Adds a "New Window" item to the top of the existing File menu.
    addItemToSubmenu(menu, 'File', 0, new electron_1.MenuItem({
        label: 'New Window',
        accelerator: 'CmdOrCtrl+Shift+N',
        click: () => {
            (0, utils_1.createWindow)(url);
        },
    }));
    // Add "Check for Updates" to the application menu on macOS.
    if ((0, utils_1.isMacOS)()) {
        const appSubmenu = menu.items[0]?.submenu;
        if (appSubmenu) {
            appSubmenu.insert(1, new electron_1.MenuItem({
                id: 'check-for-updates',
                label: updater_1.MenuUpdateStep.CheckForUpdates,
                click: (menuItem) => {
                    const action = updater_1.updateActions[menuItem.label];
                    action?.();
                },
            }));
        }
    }
    // Adds Docs to the Help menu.
    addItemToSubmenu(menu, 'Help', 0, new electron_1.MenuItem({
        label: 'Docs',
        click: async () => {
            await electron_1.shell.openExternal('https://antigravity.google/docs');
        },
    }));
    (0, debugConsole_1.configureDebugConsoleMenu)(menu);
    // Re-apply the menu so the change takes effect.
    electron_1.Menu.setApplicationMenu(menu);
    // Asynchronously adds "Connect to WSL" (Windows only, when WSL is present).
    void addWslConnectMenu(menu);
}"""

    new_fn = """function setupApplicationMenu(url) {
    const appName = electron_1.app.getName();
    const isMac = (0, utils_1.isMacOS)();
    const template = [
        ...(isMac ? [{
            label: appName,
            submenu: [
                { role: 'about', label: `关于 ${appName}` },
                {
                    id: 'check-for-updates',
                    label: updater_1.MenuUpdateStep.CheckForUpdates,
                    click: (menuItem) => {
                        const action = updater_1.updateActions[menuItem.label];
                        action?.();
                    },
                },
                { type: 'separator' },
                { role: 'services', label: '服务' },
                { type: 'separator' },
                { role: 'hide', label: `隐藏 ${appName}` },
                { role: 'hideOthers', label: '隐藏其他' },
                { role: 'unhide', label: '全部显示' },
                { type: 'separator' },
                { role: 'quit', label: `退出 ${appName}` },
            ],
        }] : []),
        {
            label: '文件',
            submenu: [
                {
                    label: '新建窗口',
                    accelerator: 'CmdOrCtrl+Shift+N',
                    click: () => {
                        (0, utils_1.createWindow)(url);
                    },
                },
                { type: 'separator' },
                isMac ? { role: 'close', label: '关闭窗口' } : { role: 'quit', label: '退出' },
            ],
        },
        {
            label: '编辑',
            submenu: [
                { role: 'undo', label: '撤销' },
                { role: 'redo', label: '重做' },
                { type: 'separator' },
                { role: 'cut', label: '剪切' },
                { role: 'copy', label: '复制' },
                { role: 'paste', label: '粘贴' },
                { role: 'pasteAndMatchStyle', label: '粘贴并匹配样式' },
                { role: 'delete', label: '删除' },
                { role: 'selectAll', label: '全选' },
            ],
        },
        {
            label: '视图',
            submenu: [
                { role: 'reload', label: '重新加载' },
                { role: 'forceReload', label: '强制重新加载' },
                { role: 'toggleDevTools', label: '切换开发者工具' },
                { type: 'separator' },
                { role: 'resetZoom', label: '实际大小' },
                { role: 'zoomIn', label: '放大' },
                { role: 'zoomOut', label: '缩小' },
                { type: 'separator' },
                { role: 'togglefullscreen', label: '切换全屏' },
            ],
        },
        {
            label: '窗口',
            submenu: [
                { role: 'minimize', label: '最小化' },
                { role: 'zoom', label: '缩放' },
                ...(isMac ? [
                    { type: 'separator' },
                    { role: 'front', label: '前置全部窗口' },
                ] : [
                    { role: 'close', label: '关闭' },
                ]),
            ],
        },
        {
            role: 'help',
            label: '帮助',
            submenu: [
                {
                    label: '官方文档',
                    click: async () => {
                        await electron_1.shell.openExternal('https://antigravity.google/docs');
                    },
                },
            ],
        },
    ];
    const menu = electron_1.Menu.buildFromTemplate(template);
    (0, debugConsole_1.configureDebugConsoleMenu)(menu);
    electron_1.Menu.setApplicationMenu(menu);
    void addWslConnectMenu(menu);
}"""

    out = src.replace(old_fn, new_fn)
    out = out.replace("label: 'Connect to WSL'", "label: '连接到 WSL'")
    out = out.replace("label: 'Reopen Locally'", "label: '在本地重新打开'")
    out = out.replace("addItemToSubmenu(menu, 'File'", "addItemToSubmenu(menu, '文件'")
    return out + f"\n{PATCH_MARKER}\n"


def patch_tray_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    old_block = """            countItem.label =
                (count > 0 ? `${count}` : 'No') +
                    ' agent' +
                    (count === 1 ? '' : 's') +
                    ' running';"""
    new_block = """            countItem.label =
                count > 0 ? `${count} 个智能体正在运行` : '无运行中的智能体';"""
    out = src.replace(old_block, new_block)
    return out + f"\n{PATCH_MARKER}\n"


def patch_updater_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    replacements = [
        ('MenuUpdateStep["CheckForUpdates"] = "Check for Updates";', 'MenuUpdateStep["CheckForUpdates"] = "检查更新";'),
        ('MenuUpdateStep["CheckingForUpdates"] = "Checking for Updates...";', 'MenuUpdateStep["CheckingForUpdates"] = "正在检查更新...";'),
        ('MenuUpdateStep["DownloadingUpdate"] = "Downloading Update...";', 'MenuUpdateStep["DownloadingUpdate"] = "正在下载更新...";'),
        ('MenuUpdateStep["RestartToUpdate"] = "Restart to Update";', 'MenuUpdateStep["RestartToUpdate"] = "重启以更新";'),
        ("title: 'Check for Updates'", "title: '检查更新'"),
        ("message: 'No updates available'", "message: '当前已是最新版本，暂无可用更新'"),
        ("buttons: ['OK']", "buttons: ['确定']"),
    ]
    out = src
    for old, new in replacements:
        out = out.replace(old, new)
    return out + f"\n{PATCH_MARKER}\n"


def patch_ipc_handlers_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    replacements = [
        ("title: 'Open workspace'", "title: '打开工作区'"),
        ("title: 'Open workspaces'", "title: '打开多个工作区'"),
        ("showErrorBox('Cannot open folder'", "showErrorBox('无法打开文件夹'"),
        ("message: 'Folder is on the Windows filesystem'", "message: '文件夹位于 Windows 文件系统中'"),
    ]
    out = src
    for old, new in replacements:
        out = out.replace(old, new)
    return out + f"\n{PATCH_MARKER}\n"


def patch_wizard_html_js(src: str) -> str:
    if PATCH_MARKER in src:
        return src
    replacements = [
        ("<title>Welcome to Antigravity</title>", "<title>欢迎使用 Antigravity</title>"),
        ("Setting up…", "正在设置…"),
        ("Welcome to the new Antigravity!", "欢迎使用全新 Antigravity！"),
        (
            "Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named <b>Antigravity IDE</b>.",
            "Antigravity 已围绕智能体优先理念全新重构并带来更多新能力。如果你仍需要代码编辑器，可以下载独立应用 <b>Antigravity IDE</b>。",
        ),
        ("Download the Antigravity IDE", "下载 Antigravity IDE"),
        ("Explore the new Antigravity", "探索全新 Antigravity"),
    ]
    out = src
    for old, new in replacements:
        out = out.replace(old, new)
    return out + f"\n{PATCH_MARKER}\n"


def patch_preload_js(src: str, dict_data: dict, runtime_js: str) -> str:
    if PATCH_MARKER in src:
        return src
    out = src.replace(
        "showContextMenu: (items) => electron_1.ipcRenderer.invoke('window:show-context-menu', items),",
        "showContextMenu: (items) => electron_1.ipcRenderer.invoke('window:show-context-menu', window.__ANTIGRAVITY_I18N__ ? window.__ANTIGRAVITY_I18N__.translateMenuItems(items) : items),",
    )
    out = out.replace(
        "send: (options) => electron_1.ipcRenderer.invoke('notification:send', options),",
        "send: (options) => electron_1.ipcRenderer.invoke('notification:send', window.__ANTIGRAVITY_I18N__ && options ? { ...options, title: window.__ANTIGRAVITY_I18N__.translateText(options.title), body: window.__ANTIGRAVITY_I18N__.translateText(options.body) } : options),",
    )
    dict_json_str = json.dumps(dict_data, ensure_ascii=False, separators=(",", ":"))
    injected = (
        f"\n{PATCH_MARKER}\n"
        f"const __ANTIGRAVITY_ZH_DICT__ = {dict_json_str};\n"
        f"{runtime_js}\n"
    )
    return out + injected


def build_patched_asar(orig_asar_path: Path, out_asar_path: Path, dict_data: dict, runtime_js: str) -> str:
    header, base_offset, raw, _ = read_asar(orig_asar_path)
    payload_chunks = []
    current_offset = 0

    def walk(node: dict, rel_path: str):
        nonlocal current_offset
        if "files" in node:
            for name, child in node["files"].items():
                child_rel = f"{rel_path}/{name}" if rel_path else name
                walk(child, child_rel)
            return

        if node.get("unpacked"):
            return

        if "offset" not in node or "size" not in node:
            return

        orig_off = base_offset + int(node["offset"])
        orig_size = int(node["size"])
        file_bytes = raw[orig_off : orig_off + orig_size]

        if rel_path == "dist/main.js":
            file_bytes = patch_main_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/menu.js":
            file_bytes = patch_menu_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/tray.js":
            file_bytes = patch_tray_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/updater.js":
            file_bytes = patch_updater_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/ipcHandlers.js":
            file_bytes = patch_ipc_handlers_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/ideInstall/wizardHtml.js":
            file_bytes = patch_wizard_html_js(file_bytes.decode("utf-8")).encode("utf-8")
        elif rel_path == "dist/preload.js":
            file_bytes = patch_preload_js(
                file_bytes.decode("utf-8"), dict_data, runtime_js
            ).encode("utf-8")

        node["size"] = len(file_bytes)
        node["offset"] = str(current_offset)
        node["integrity"] = compute_integrity(file_bytes)
        payload_chunks.append(file_bytes)
        current_offset += len(file_bytes)

    walk(header, "")

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    header_sha256 = hashlib.sha256(header_bytes).hexdigest()

    json_size = len(header_bytes)
    padding = (4 - (json_size % 4)) % 4
    aligned_json_size = json_size + padding
    u0 = 4
    header_size = aligned_json_size + 8
    u1 = aligned_json_size + 4

    prefix = struct.pack("<4I", u0, header_size, u1, json_size)
    with open(out_asar_path, "wb") as f:
        f.write(prefix)
        f.write(header_bytes)
        if padding:
            f.write(b"\x00" * padding)
        for chunk in payload_chunks:
            f.write(chunk)

    return header_sha256


def update_info_plist_hash(plist_path: Path, new_hash: str):
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)

    integrity = plist_data.get("ElectronAsarIntegrity")
    if isinstance(integrity, dict) and "Resources/app.asar" in integrity:
        integrity["Resources/app.asar"]["hash"] = new_hash

    with open(plist_path, "wb") as f:
        plistlib.dump(plist_data, f)


def resign_app(app_path: Path):
    print(f"[*] 正在对 {app_path} 进行重签名（保留原有权限配置）...")
    cmd = [
        "codesign",
        "--force",
        "--deep",
        "--preserve-metadata=entitlements",
        "--sign",
        "-",
        str(app_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] 重签名警告: {res.stderr.strip()}")
    else:
        print("[+] macOS 应用重签名完成！")


def get_status_dict(app_path: Path) -> dict:
    asar_path = app_path / "Contents" / "Resources" / "app.asar"
    plist_path = app_path / "Contents" / "Info.plist"
    dict_path = resolve_dict_path()
    dict_data = json.loads(dict_path.read_text(encoding="utf-8")) if dict_path.exists() else {}

    if not asar_path.exists() or not plist_path.exists():
        return {
            "exists": False,
            "app_path": str(app_path),
            "version": "未知",
            "patched": False,
            "integrity_ok": False,
            "has_backup": False,
            "dict_path": str(dict_path),
            "exact_count": len(dict_data.get("exact", {})),
            "pattern_count": len(dict_data.get("patterns", [])),
        }

    _, _, _, header_sha256 = read_asar(asar_path)
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    version = plist_data.get("CFBundleShortVersionString", "未知")
    backup_dir = get_version_backup_dir(version)
    backup_asar = backup_dir / "app.asar.bak"
    plist_hash = (
        plist_data.get("ElectronAsarIntegrity", {})
        .get("Resources/app.asar", {})
        .get("hash", "")
    )
    return {
        "exists": True,
        "app_path": str(app_path),
        "version": version,
        "patched": is_asar_patched(asar_path),
        "integrity_ok": header_sha256 == plist_hash,
        "header_sha256": header_sha256,
        "plist_hash": plist_hash,
        "has_backup": backup_asar.exists(),
        "dict_path": str(dict_path),
        "exact_count": len(dict_data.get("exact", {})),
        "pattern_count": len(dict_data.get("patterns", [])),
    }


def cmd_install(args):
    app_path = Path(args.app).resolve()
    asar_path = app_path / "Contents" / "Resources" / "app.asar"
    plist_path = app_path / "Contents" / "Info.plist"

    if not asar_path.exists() or not plist_path.exists():
        print(f"[!] 未找到有效的 Antigravity.app: {app_path}")
        sys.exit(1)

    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    version = plist_data.get("CFBundleShortVersionString", "default")
    backup_dir = get_version_backup_dir(version)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_asar = backup_dir / "app.asar.bak"
    backup_plist = backup_dir / "Info.plist.bak"

    if not backup_asar.exists() or not is_asar_patched(asar_path):
        print(f"[*] 正在备份 v{version} 原版文件至 {backup_dir} ...")
        shutil.copy2(asar_path, backup_asar)
        shutil.copy2(plist_path, backup_plist)
    else:
        print(f"[*] 检测到已有 v{version} 原版备份，将基于干净原版重新构建汉化包...")

    dict_path = resolve_dict_path()
    dict_data = json.loads(dict_path.read_text(encoding="utf-8"))
    runtime_js = RUNTIME_I18N_PATH.read_text(encoding="utf-8")

    print(
        f"[*] 已加载中文词典 ({dict_path})：精确词条 {len(dict_data.get('exact', {}))} 条，"
        f"动态正则规则 {len(dict_data.get('patterns', []))} 条"
    )
    print("[*] 正在注入主进程菜单与渲染进程实时汉化脚本并重打包 app.asar ...")

    new_hash = build_patched_asar(backup_asar, asar_path, dict_data, runtime_js)
    print(f"[+] 新 app.asar 头部校验 SHA256: {new_hash}")

    update_info_plist_hash(plist_path, new_hash)
    print("[+] 已同步更新 Contents/Info.plist 中的 ElectronAsarIntegrity 哈希")

    if not args.no_sign:
        resign_app(app_path)

    print("\n[✓] Antigravity.app 汉化补丁安装成功！请重启 Antigravity.app 查看效果。")


def cmd_restore(args):
    app_path = Path(args.app).resolve()
    asar_path = app_path / "Contents" / "Resources" / "app.asar"
    plist_path = app_path / "Contents" / "Info.plist"

    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)
    version = plist_data.get("CFBundleShortVersionString", "default")
    backup_dir = get_version_backup_dir(version)
    backup_asar = backup_dir / "app.asar.bak"
    backup_plist = backup_dir / "Info.plist.bak"

    if not backup_asar.exists() or not backup_plist.exists():
        print(f"[!] 未找到 v{version} 的备份文件 ({backup_dir})，无法还原。")
        sys.exit(1)

    print("[*] 正在从备份恢复原版 app.asar 与 Info.plist ...")
    shutil.copy2(backup_asar, asar_path)
    shutil.copy2(backup_plist, plist_path)

    if not args.no_sign:
        resign_app(app_path)

    print("\n[✓] 已成功还原为英文原版！请重启 Antigravity.app。")


def cmd_status(args):
    st = get_status_dict(Path(args.app).resolve())
    if not st["exists"]:
        print(f"[!] 未找到应用: {st['app_path']}")
        sys.exit(1)
    print(f"应用路径:          {st['app_path']}")
    print(f"应用版本:          {st['version']}")
    print(f"汉化状态:          {'已汉化 (Patched)' if st['patched'] else '未汉化 (Original)'}")
    print(f"词典路径:          {st['dict_path']}")
    print(f"ASAR Header Hash:  {st['header_sha256']}")
    print(f"Info.plist Hash:   {st['plist_hash']}")
    print(f"完整性校验匹配:    {'一致 (OK)' if st['integrity_ok'] else '不一致 (MISMATCH)'}")


def cmd_json_status(args):
    st = get_status_dict(Path(args.app).resolve())
    print(json.dumps(st, ensure_ascii=False))


def cmd_prepare_user_dict():
    """在 .app 包内运行时，将内置词典复制到用户目录供安全编辑（不破坏 .app 签名）。"""
    if ".app/Contents/Resources" in str(BASE_DIR):
        APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
        if not USER_DICT_PATH.exists():
            shutil.copy2(BUNDLED_DICT_PATH, USER_DICT_PATH)
        print(str(USER_DICT_PATH))
    else:
        print(str(BUNDLED_DICT_PATH))


def main():
    parser = argparse.ArgumentParser(description="Antigravity.app 简体中文汉化工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in [
        ("install", "安装或更新汉化补丁"),
        ("restore", "还原为英文原版"),
        ("status", "查看当前汉化与完整性校验状态"),
        ("json-status", "以 JSON 格式输出状态"),
        ("prepare-user-dict", "准备并返回可编辑的用户词典文件路径"),
    ]:
        sub = subparsers.add_parser(name, help=help_text)
        if name != "prepare-user-dict":
            sub.add_argument(
                "--app",
                default="/Applications/Antigravity.app",
                help="Antigravity.app 路径 (默认: /Applications/Antigravity.app)",
            )
        if name in ("install", "restore"):
            sub.add_argument(
                "--no-sign",
                action="store_true",
                help="跳过 codesign 重签名（仅用于测试）",
            )

    args = parser.parse_args()
    if args.command == "install":
        cmd_install(args)
    elif args.command == "restore":
        cmd_restore(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "json-status":
        cmd_json_status(args)
    elif args.command == "prepare-user-dict":
        cmd_prepare_user_dict()


if __name__ == "__main__":
    main()
