# Antigravity.app 简体中文汉化包

专为 macOS 版 **Antigravity.app**（v2.27.0+）打造的零依赖全量汉化工具与原生 macOS 汉化助手客户端。

## 功能特点

1. **全量汉化覆盖**：
   - **macOS 原生壳层（Electron 主进程）**：顶部应用菜单栏（`Antigravity` / `文件` / `编辑` / `视图` / `窗口` / `帮助`）、Dock 右键菜单、系统状态栏托盘菜单、退出确认弹窗、检查更新弹窗、文件选择框、IDE 安装向导。
   - **主界面 Web UI（渲染进程）**：通过向 `preload.js` 注入轻量级实时汉化引擎（`TreeWalker` + `MutationObserver`），自动汉化侧边栏、对话区、模型与配额设置、权限管理、技能（Skills）、钩子（Hooks）、插件与扩展市场、模型上下文协议（MCP）、子智能体（Subagents）、后台任务、产物（Artifacts）、文件变更与终端面板，并拦截翻译界面右键菜单与系统通知。
2. **代码与终端安全隔离**：
   - 自动跳过 `<pre>`、`<code>`、`<textarea>`、`<input>`、Monaco/CodeMirror 编辑器、Xterm 终端、KaTeX 公式等节点，不破坏任何代码内容或命令输出。
3. **原生 ASAR 完整性校验与 macOS 重签名支持**：
   - 纯 Python 3 标准库直接读写 `app.asar`，保留全部 `app.asar.unpacked` 映射，自动计算每个文件的 4MB 分块 SHA256 以及 ASAR 头部 SHA256，同步更新 `Contents/Info.plist` 中的 `ElectronAsarIntegrity`，并通过 `codesign` 保留原有权限（Entitlements）完成重签名。
4. **跨机器独立备份与多架构兼容**：
   - 支持一键打包为 **Universal 通用双架构（Apple Silicon M芯片 + Intel 芯片通用）** 的 **`Antigravity 汉化助手.app`**。
   - 原版备份按版本号独立存放在每台电脑自己的 `~/Library/Application Support/AntigravityZhPatcher/backups/<version>/` 下，分发 `.app` 不会携带本机备份文件。

---

## 目录结构

```text
antigravity-zh-patch/
├── .gitignore            # Git 忽略规则（忽略构建产物与备份）
├── README.md             # 项目说明文档
├── build-app.sh          # 一键编译打包 macOS 原生「Antigravity 汉化助手.app」脚本
├── install.sh            # 命令行一键安装汉化脚本
├── restore.sh            # 命令行一键还原脚本
├── patch.py              # 核心汉化/还原与 ASAR 完整性校验脚本
├── runtime-i18n.js       # 渲染进程实时汉化引擎
├── zh-CN.json            # 简体中文词典（含精确匹配词条与动态正则规则）
└── macos-app/            # macOS 原生客户端源码
    ├── Info.plist        # 应用包配置
    └── launcher.m        # Objective-C Cocoa 原生窗口启动器源码
```

---

## 方式一：打包并使用可视化 `Antigravity 汉化助手.app`

### 1. 编译打包 `.app`（本地运行）

```bash
cd ~/Desktop/antigravity-zh-patch
chmod +x build-app.sh install.sh restore.sh patch.py
./build-app.sh
```

执行后会在 `dist/` 目录下生成：
- `dist/Antigravity 汉化助手.app`：双击即可弹出原生图形界面（支持一键安装汉化、还原英文原版、编辑词典文件、重启生效）。
- `dist/Antigravity-汉化助手-macOS.zip`：可直接发给其他 Mac 用户的通用分发包。

### 2. 其他 Mac 用户首次打开说明

若通过微信/网盘/AirDrop 发送给其他 Mac 用户，由于未经过 Apple 付费开发者公证（Notarization），对方首次打开若遇到系统拦截提示，只需：
- 在访达中**按住 Control 键右键点击 `Antigravity 汉化助手.app` -> 选择“打开”**；
- 或在终端执行一次：
  ```bash
  xattr -cr "Antigravity 汉化助手.app"
  ```

---

## 方式二：命令行直接使用

### 1. 一键安装汉化

```bash
cd ~/Desktop/antigravity-zh-patch
./install.sh
```

安装完成后，**重启 `Antigravity.app`** 即可生效。

### 2. 查看当前汉化与完整性校验状态

```bash
python3 patch.py status
```

### 3. 一键还原英文原版

```bash
./restore.sh
```

---

## 自定义增补词典

- **命令行模式**：直接修改仓库根目录下的 `zh-CN.json`，然后重新执行 `./install.sh`。
- **App 模式**：双击 `Antigravity 汉化助手.app` -> 点击 **“编辑词典文件”**，会自动在 `~/Library/Application Support/AntigravityZhPatcher/zh-CN.json` 创建并定位打开你的个人词典文件（避免修改 `.app` 内部文件破坏签名），保存后再次点击 **“重新汉化 / 更新词典”** 即可生效。
