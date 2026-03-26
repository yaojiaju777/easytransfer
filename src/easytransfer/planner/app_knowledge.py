"""常见 Windows 应用知识库。

包含 50+ 常见应用的 winget ID、已知配置路径、迁移策略和备注。
用于匹配扫描结果中的应用，判断是否可自动安装，以及需要迁移哪些配置。

知识库结构：
- key: 用于匹配的规范化应用名（小写）
- value: AppKnowledge dataclass，包含完整的迁移信息
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from easytransfer.core.models import InstallSource


class MigrationStrategy(str, Enum):
    """应用迁移策略。"""

    WINGET_INSTALL = "winget_install"  # 通过 winget 自动安装
    STORE_INSTALL = "store_install"  # 通过 Microsoft Store 安装
    MANUAL_DOWNLOAD = "manual_download"  # 需要用户手动下载安装
    ACCOUNT_SYNC = "account_sync"  # 通过账号同步（如 Chrome、OneDrive）
    PORTABLE_COPY = "portable_copy"  # 便携版直接复制
    NOT_NEEDED = "not_needed"  # 新系统自带，无需迁移
    SKIP = "skip"  # 建议跳过（如系统组件、运行时）


@dataclass
class AppKnowledge:
    """单个应用的迁移知识。"""

    display_name: str  # 显示名称
    winget_id: str = ""  # winget 包 ID
    install_source: InstallSource = InstallSource.WINGET
    strategy: MigrationStrategy = MigrationStrategy.WINGET_INSTALL
    config_paths: list[str] = field(default_factory=list)
    data_paths: list[str] = field(default_factory=list)
    notes: str = ""
    alternatives: list[str] = field(default_factory=list)  # 替代品建议
    estimated_install_minutes: float = 2.0  # 估计安装时间（分钟）
    requires_login: bool = False  # 安装后是否需要登录


# ============================================================
# 匹配关键词 → 知识库条目
# ============================================================

# 用于模糊匹配的关键词映射：keyword → knowledge base key
# 当应用名包含某个关键词时，匹配到对应的知识库条目
_MATCH_KEYWORDS: dict[str, str] = {
    "chrome": "google_chrome",
    "firefox": "mozilla_firefox",
    "edge": "microsoft_edge",
    "brave": "brave_browser",
    "opera": "opera_browser",
    "visual studio code": "vscode",
    "vs code": "vscode",
    "vscode": "vscode",
    "notepad++": "notepadplusplus",
    "sublime text": "sublime_text",
    "jetbrains": "jetbrains_toolbox",
    "intellij": "intellij_idea",
    "pycharm": "pycharm",
    "webstorm": "webstorm",
    "git": "git",
    "github desktop": "github_desktop",
    "tortoisegit": "tortoisegit",
    "python": "python",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "java": "java_jdk",
    "openjdk": "java_jdk",
    "rust": "rustup",
    "rustup": "rustup",
    "golang": "golang",
    "docker desktop": "docker_desktop",
    "docker": "docker_desktop",
    "postman": "postman",
    "7-zip": "7zip",
    "7zip": "7zip",
    "winrar": "winrar",
    "bandizip": "bandizip",
    "vlc": "vlc",
    "potplayer": "potplayer",
    "spotify": "spotify",
    "foobar2000": "foobar2000",
    "obs studio": "obs_studio",
    "obs": "obs_studio",
    "steam": "steam",
    "discord": "discord",
    "telegram": "telegram",
    "slack": "slack",
    "zoom": "zoom",
    "teams": "microsoft_teams",
    "wechat": "wechat",
    "微信": "wechat",
    "qq": "tencent_qq",
    "腾讯qq": "tencent_qq",
    "dingtalk": "dingtalk",
    "钉钉": "dingtalk",
    "feishu": "feishu",
    "飞书": "feishu",
    "notion": "notion",
    "obsidian": "obsidian",
    "typora": "typora",
    "evernote": "evernote",
    "adobe acrobat": "adobe_acrobat",
    "acrobat reader": "adobe_acrobat",
    "photoshop": "adobe_photoshop",
    "illustrator": "adobe_illustrator",
    "premiere": "adobe_premiere",
    "figma": "figma",
    "gimp": "gimp",
    "paint.net": "paintnet",
    "everything": "everything",
    "powertoys": "powertoys",
    "autohotkey": "autohotkey",
    "bitwarden": "bitwarden",
    "keepass": "keepass",
    "1password": "1password",
    "onedrive": "onedrive",
    "dropbox": "dropbox",
    "google drive": "google_drive",
    "putty": "putty",
    "winscp": "winscp",
    "filezilla": "filezilla",
    "windows terminal": "windows_terminal",
    "terminal": "windows_terminal",
    "powershell": "powershell",
    "wsl": "wsl",
    "virtualbox": "virtualbox",
    "vmware": "vmware_workstation",
    "clash": "clash_for_windows",
    "v2ray": "v2rayn",
    "draw.io": "drawio",
    "calibre": "calibre",
    "qbittorrent": "qbittorrent",
    "foxmail": "foxmail",
    "thunderbird": "thunderbird",
    "libreoffice": "libreoffice",
    "snipaste": "snipaste",
    "flameshot": "flameshot",
    "ditto": "ditto",
    "cursor": "cursor",
}


# ============================================================
# 应用知识库（50+ 条目）
# ============================================================

APP_KNOWLEDGE_BASE: dict[str, AppKnowledge] = {
    # ---- 浏览器 ----
    "google_chrome": AppKnowledge(
        display_name="Google Chrome",
        winget_id="Google.Chrome",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Bookmarks",
            "%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Preferences",
        ],
        notes="书签和扩展建议通过 Google 账号同步",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "mozilla_firefox": AppKnowledge(
        display_name="Mozilla Firefox",
        winget_id="Mozilla.Firefox",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Mozilla\\Firefox\\Profiles",
        ],
        notes="配置文件可整体迁移",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "microsoft_edge": AppKnowledge(
        display_name="Microsoft Edge",
        winget_id="Microsoft.Edge",
        strategy=MigrationStrategy.NOT_NEEDED,
        notes="Windows 自带，通过 Microsoft 账号同步数据",
        requires_login=True,
        estimated_install_minutes=0.0,
    ),
    "brave_browser": AppKnowledge(
        display_name="Brave Browser",
        winget_id="Brave.Brave",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data",
        ],
        estimated_install_minutes=3.0,
    ),
    "opera_browser": AppKnowledge(
        display_name="Opera",
        winget_id="Opera.Opera",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=3.0,
    ),

    # ---- 开发工具 ----
    "vscode": AppKnowledge(
        display_name="Visual Studio Code",
        winget_id="Microsoft.VisualStudioCode",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Code\\User\\settings.json",
            "%APPDATA%\\Code\\User\\keybindings.json",
            "%APPDATA%\\Code\\User\\snippets",
        ],
        data_paths=[
            "%USERPROFILE%\\.vscode\\extensions",
        ],
        notes="扩展列表可通过 code --list-extensions 导出",
        estimated_install_minutes=3.0,
    ),
    "cursor": AppKnowledge(
        display_name="Cursor",
        winget_id="Anysphere.Cursor",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Cursor\\User\\settings.json",
            "%APPDATA%\\Cursor\\User\\keybindings.json",
        ],
        notes="基于 VS Code 的 AI 编辑器",
        estimated_install_minutes=3.0,
    ),
    "notepadplusplus": AppKnowledge(
        display_name="Notepad++",
        winget_id="Notepad++.Notepad++",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Notepad++\\config.xml",
            "%APPDATA%\\Notepad++\\shortcuts.xml",
        ],
        estimated_install_minutes=1.0,
    ),
    "sublime_text": AppKnowledge(
        display_name="Sublime Text",
        winget_id="SublimeHQ.SublimeText.4",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Sublime Text\\Packages\\User",
        ],
        estimated_install_minutes=1.0,
    ),
    "jetbrains_toolbox": AppKnowledge(
        display_name="JetBrains Toolbox",
        winget_id="JetBrains.Toolbox",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="安装 Toolbox 后可管理所有 JetBrains IDE",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "intellij_idea": AppKnowledge(
        display_name="IntelliJ IDEA",
        winget_id="JetBrains.IntelliJIDEA.Community",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\JetBrains\\IntelliJIdea*",
        ],
        requires_login=True,
        estimated_install_minutes=5.0,
    ),
    "pycharm": AppKnowledge(
        display_name="PyCharm",
        winget_id="JetBrains.PyCharm.Community",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\JetBrains\\PyCharm*",
        ],
        requires_login=True,
        estimated_install_minutes=5.0,
    ),
    "webstorm": AppKnowledge(
        display_name="WebStorm",
        winget_id="JetBrains.WebStorm",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\JetBrains\\WebStorm*",
        ],
        requires_login=True,
        estimated_install_minutes=5.0,
    ),

    # ---- 版本控制 ----
    "git": AppKnowledge(
        display_name="Git",
        winget_id="Git.Git",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%USERPROFILE%\\.gitconfig",
            "%USERPROFILE%\\.gitignore_global",
        ],
        notes="全局配置文件建议迁移",
        estimated_install_minutes=2.0,
    ),
    "github_desktop": AppKnowledge(
        display_name="GitHub Desktop",
        winget_id="GitHub.GitHubDesktop",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "tortoisegit": AppKnowledge(
        display_name="TortoiseGit",
        winget_id="TortoiseGit.TortoiseGit",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=2.0,
    ),

    # ---- 编程语言运行时 ----
    "python": AppKnowledge(
        display_name="Python",
        winget_id="Python.Python.3.12",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\pip\\pip.ini",
            "%USERPROFILE%\\.pypirc",
        ],
        notes="全局包建议通过 requirements.txt 重新安装",
        estimated_install_minutes=3.0,
    ),
    "nodejs": AppKnowledge(
        display_name="Node.js",
        winget_id="OpenJS.NodeJS.LTS",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%USERPROFILE%\\.npmrc",
        ],
        notes="全局包建议重新安装",
        estimated_install_minutes=2.0,
    ),
    "java_jdk": AppKnowledge(
        display_name="Java JDK",
        winget_id="EclipseAdoptium.Temurin.21.JDK",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="注意 JAVA_HOME 环境变量",
        estimated_install_minutes=3.0,
    ),
    "rustup": AppKnowledge(
        display_name="Rust (rustup)",
        winget_id="Rustlang.Rustup",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%USERPROFILE%\\.cargo\\config.toml",
        ],
        estimated_install_minutes=5.0,
    ),
    "golang": AppKnowledge(
        display_name="Go",
        winget_id="GoLang.Go",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="注意 GOPATH 环境变量",
        estimated_install_minutes=2.0,
    ),

    # ---- 容器/虚拟化 ----
    "docker_desktop": AppKnowledge(
        display_name="Docker Desktop",
        winget_id="Docker.DockerDesktop",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="需要 WSL2 或 Hyper-V 支持",
        requires_login=True,
        estimated_install_minutes=10.0,
    ),
    "virtualbox": AppKnowledge(
        display_name="VirtualBox",
        winget_id="Oracle.VirtualBox",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="虚拟机文件需要单独迁移",
        estimated_install_minutes=5.0,
    ),
    "vmware_workstation": AppKnowledge(
        display_name="VMware Workstation",
        winget_id="VMware.WorkstationPro",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=5.0,
    ),
    "wsl": AppKnowledge(
        display_name="WSL",
        strategy=MigrationStrategy.NOT_NEEDED,
        install_source=InstallSource.STORE,
        notes="通过 wsl --install 安装，发行版需单独导出/导入",
        estimated_install_minutes=0.0,
    ),

    # ---- API/网络工具 ----
    "postman": AppKnowledge(
        display_name="Postman",
        winget_id="Postman.Postman",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据建议通过 Postman 账号同步",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- 压缩工具 ----
    "7zip": AppKnowledge(
        display_name="7-Zip",
        winget_id="7zip.7zip",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),
    "winrar": AppKnowledge(
        display_name="WinRAR",
        winget_id="RARLab.WinRAR",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),
    "bandizip": AppKnowledge(
        display_name="Bandizip",
        winget_id="Bandisoft.Bandizip",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),

    # ---- 媒体播放 ----
    "vlc": AppKnowledge(
        display_name="VLC Media Player",
        winget_id="VideoLAN.VLC",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=2.0,
    ),
    "potplayer": AppKnowledge(
        display_name="PotPlayer",
        winget_id="Daum.PotPlayer",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=2.0,
    ),
    "spotify": AppKnowledge(
        display_name="Spotify",
        winget_id="Spotify.Spotify",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "foobar2000": AppKnowledge(
        display_name="foobar2000",
        winget_id="PeterPawlowski.foobar2000",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\foobar2000",
        ],
        estimated_install_minutes=1.0,
    ),

    # ---- 录屏/直播 ----
    "obs_studio": AppKnowledge(
        display_name="OBS Studio",
        winget_id="OBSProject.OBSStudio",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\obs-studio",
        ],
        estimated_install_minutes=3.0,
    ),

    # ---- 游戏平台 ----
    "steam": AppKnowledge(
        display_name="Steam",
        winget_id="Valve.Steam",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="游戏需要在 Steam 中重新下载",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- 社交通讯 ----
    "discord": AppKnowledge(
        display_name="Discord",
        winget_id="Discord.Discord",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "telegram": AppKnowledge(
        display_name="Telegram Desktop",
        winget_id="Telegram.TelegramDesktop",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "slack": AppKnowledge(
        display_name="Slack",
        winget_id="SlackTechnologies.Slack",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "zoom": AppKnowledge(
        display_name="Zoom",
        winget_id="Zoom.Zoom",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "microsoft_teams": AppKnowledge(
        display_name="Microsoft Teams",
        winget_id="Microsoft.Teams",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "wechat": AppKnowledge(
        display_name="微信 (WeChat)",
        winget_id="Tencent.WeChat",
        strategy=MigrationStrategy.WINGET_INSTALL,
        data_paths=[
            "%USERPROFILE%\\Documents\\WeChat Files",
        ],
        notes="聊天记录迁移需要使用微信内置功能",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "tencent_qq": AppKnowledge(
        display_name="腾讯 QQ",
        winget_id="Tencent.QQ.NT",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "dingtalk": AppKnowledge(
        display_name="钉钉 (DingTalk)",
        winget_id="Alibaba.DingTalk",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "feishu": AppKnowledge(
        display_name="飞书 (Feishu)",
        winget_id="ByteDance.Feishu",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- 笔记/知识管理 ----
    "notion": AppKnowledge(
        display_name="Notion",
        winget_id="Notion.Notion",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据存储在云端，安装后登录即可",
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "obsidian": AppKnowledge(
        display_name="Obsidian",
        winget_id="Obsidian.Obsidian",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="vault 目录需要单独迁移",
        estimated_install_minutes=2.0,
    ),
    "typora": AppKnowledge(
        display_name="Typora",
        winget_id="Typora.Typora",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Typora",
        ],
        estimated_install_minutes=1.0,
    ),
    "evernote": AppKnowledge(
        display_name="Evernote",
        winget_id="evernote.evernote",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据存储在云端",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- Adobe 系列 ----
    "adobe_acrobat": AppKnowledge(
        display_name="Adobe Acrobat Reader",
        winget_id="Adobe.Acrobat.Reader.64-bit",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=5.0,
    ),
    "adobe_photoshop": AppKnowledge(
        display_name="Adobe Photoshop",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.EXE,
        notes="需要通过 Adobe Creative Cloud 安装并激活许可证",
        requires_login=True,
        estimated_install_minutes=15.0,
    ),
    "adobe_illustrator": AppKnowledge(
        display_name="Adobe Illustrator",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.EXE,
        notes="需要通过 Adobe Creative Cloud 安装并激活许可证",
        requires_login=True,
        estimated_install_minutes=15.0,
    ),
    "adobe_premiere": AppKnowledge(
        display_name="Adobe Premiere Pro",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.EXE,
        notes="需要通过 Adobe Creative Cloud 安装并激活许可证",
        requires_login=True,
        estimated_install_minutes=15.0,
    ),

    # ---- 设计工具 ----
    "figma": AppKnowledge(
        display_name="Figma",
        winget_id="Figma.Figma",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据存储在云端",
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "gimp": AppKnowledge(
        display_name="GIMP",
        winget_id="GIMP.GIMP",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=3.0,
    ),
    "paintnet": AppKnowledge(
        display_name="Paint.NET",
        winget_id="dotPDN.PaintDotNet",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=2.0,
    ),
    "drawio": AppKnowledge(
        display_name="draw.io",
        winget_id="JGraph.Draw",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=2.0,
    ),

    # ---- 效率工具 ----
    "everything": AppKnowledge(
        display_name="Everything",
        winget_id="voidtools.Everything",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),
    "powertoys": AppKnowledge(
        display_name="Microsoft PowerToys",
        winget_id="Microsoft.PowerToys",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%LOCALAPPDATA%\\Microsoft\\PowerToys",
        ],
        estimated_install_minutes=2.0,
    ),
    "autohotkey": AppKnowledge(
        display_name="AutoHotkey",
        winget_id="AutoHotkey.AutoHotkey",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="脚本文件需要单独迁移",
        estimated_install_minutes=1.0,
    ),
    "snipaste": AppKnowledge(
        display_name="Snipaste",
        winget_id="Snipaste.Snipaste",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),
    "ditto": AppKnowledge(
        display_name="Ditto Clipboard Manager",
        winget_id="ditto.ditto",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),

    # ---- 密码管理 ----
    "bitwarden": AppKnowledge(
        display_name="Bitwarden",
        winget_id="Bitwarden.Bitwarden",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据存储在云端",
        requires_login=True,
        estimated_install_minutes=2.0,
    ),
    "keepass": AppKnowledge(
        display_name="KeePass",
        winget_id="DominikReichl.KeePass",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据库文件 (.kdbx) 需要单独迁移",
        estimated_install_minutes=1.0,
    ),
    "1password": AppKnowledge(
        display_name="1Password",
        winget_id="AgileBits.1Password",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="数据存储在云端",
        requires_login=True,
        estimated_install_minutes=2.0,
    ),

    # ---- 云存储 ----
    "onedrive": AppKnowledge(
        display_name="OneDrive",
        strategy=MigrationStrategy.NOT_NEEDED,
        install_source=InstallSource.STORE,
        notes="Windows 自带，登录 Microsoft 账号即可同步",
        requires_login=True,
        estimated_install_minutes=0.0,
    ),
    "dropbox": AppKnowledge(
        display_name="Dropbox",
        winget_id="Dropbox.Dropbox",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "google_drive": AppKnowledge(
        display_name="Google Drive",
        winget_id="Google.GoogleDrive",
        strategy=MigrationStrategy.WINGET_INSTALL,
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- 远程连接 ----
    "putty": AppKnowledge(
        display_name="PuTTY",
        winget_id="PuTTY.PuTTY",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="保存的会话在注册表中，需要导出迁移",
        estimated_install_minutes=1.0,
    ),
    "winscp": AppKnowledge(
        display_name="WinSCP",
        winget_id="WinSCP.WinSCP",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\WinSCP.ini",
        ],
        estimated_install_minutes=1.0,
    ),
    "filezilla": AppKnowledge(
        display_name="FileZilla",
        winget_id="TimKosse.FileZilla.Client",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\FileZilla\\sitemanager.xml",
        ],
        estimated_install_minutes=1.0,
    ),

    # ---- 终端 ----
    "windows_terminal": AppKnowledge(
        display_name="Windows Terminal",
        winget_id="Microsoft.WindowsTerminal",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%LOCALAPPDATA%\\Packages\\Microsoft.WindowsTerminal_8wekyb3d8bbwe\\LocalState\\settings.json",
        ],
        estimated_install_minutes=1.0,
    ),
    "powershell": AppKnowledge(
        display_name="PowerShell",
        winget_id="Microsoft.PowerShell",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%USERPROFILE%\\Documents\\PowerShell\\Microsoft.PowerShell_profile.ps1",
        ],
        estimated_install_minutes=2.0,
    ),

    # ---- 下载工具 ----
    "qbittorrent": AppKnowledge(
        display_name="qBittorrent",
        winget_id="qBittorrent.qBittorrent",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),

    # ---- 邮件客户端 ----
    "foxmail": AppKnowledge(
        display_name="Foxmail",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.EXE,
        notes="需要从官网下载，邮件数据需单独迁移",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),
    "thunderbird": AppKnowledge(
        display_name="Thunderbird",
        winget_id="Mozilla.Thunderbird",
        strategy=MigrationStrategy.WINGET_INSTALL,
        config_paths=[
            "%APPDATA%\\Thunderbird\\Profiles",
        ],
        notes="配置文件可整体迁移",
        requires_login=True,
        estimated_install_minutes=3.0,
    ),

    # ---- 办公套件 ----
    "libreoffice": AppKnowledge(
        display_name="LibreOffice",
        winget_id="TheDocumentFoundation.LibreOffice",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=5.0,
    ),

    # ---- 网络代理 ----
    "clash_for_windows": AppKnowledge(
        display_name="Clash for Windows",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.PORTABLE,
        config_paths=[
            "%USERPROFILE%\\.config\\clash",
        ],
        notes="配置文件和订阅链接需要手动迁移",
        estimated_install_minutes=2.0,
    ),
    "v2rayn": AppKnowledge(
        display_name="V2RayN",
        strategy=MigrationStrategy.MANUAL_DOWNLOAD,
        install_source=InstallSource.PORTABLE,
        notes="便携版，直接复制文件夹即可",
        estimated_install_minutes=1.0,
    ),

    # ---- 电子书 ----
    "calibre": AppKnowledge(
        display_name="calibre",
        winget_id="calibre.calibre",
        strategy=MigrationStrategy.WINGET_INSTALL,
        notes="书库目录需要单独迁移",
        estimated_install_minutes=3.0,
    ),

    # ---- 截图 ----
    "flameshot": AppKnowledge(
        display_name="Flameshot",
        winget_id="Flameshot.Flameshot",
        strategy=MigrationStrategy.WINGET_INSTALL,
        estimated_install_minutes=1.0,
    ),
}


# ============================================================
# 查询接口
# ============================================================


def lookup_app(app_name: str) -> AppKnowledge | None:
    """根据应用名查找知识库条目。

    使用模糊匹配：将应用名转为小写，检查是否包含已知关键词。

    Args:
        app_name: 应用显示名称（从扫描结果中获取）。

    Returns:
        匹配的 AppKnowledge，未找到时返回 None。
    """
    name_lower = app_name.lower()

    # 1. 尝试关键词匹配
    for keyword, kb_key in _MATCH_KEYWORDS.items():
        if keyword in name_lower:
            return APP_KNOWLEDGE_BASE.get(kb_key)

    return None


def get_all_known_apps() -> dict[str, AppKnowledge]:
    """返回完整的知识库。"""
    return APP_KNOWLEDGE_BASE.copy()


def get_knowledge_count() -> int:
    """返回知识库条目数。"""
    return len(APP_KNOWLEDGE_BASE)
