"""应用配置扫描器。

识别常见应用的配置文件位置，用于后续打包迁移。
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from easytransfer.core.logging import get_logger
from easytransfer.core.models import ConfigInfo, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

# 用户目录
_USER_HOME = Path.home()
_APPDATA = Path(os.environ.get("APPDATA", _USER_HOME / "AppData" / "Roaming"))
_LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", _USER_HOME / "AppData" / "Local"))

# 已知应用的配置路径映射
# (app_name, config_description, relative_path_from_base, base_dir)
_KNOWN_CONFIGS: list[tuple[str, str, str, Path]] = [
    # VS Code
    ("Visual Studio Code", "用户设置", "Code/User/settings.json", _APPDATA),
    ("Visual Studio Code", "快捷键设置", "Code/User/keybindings.json", _APPDATA),
    ("Visual Studio Code", "代码片段", "Code/User/snippets", _APPDATA),
    # Windows Terminal
    ("Windows Terminal", "配置文件", "Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json", _LOCAL_APPDATA),
    # PowerShell
    ("PowerShell", "Profile", "PowerShell/Microsoft.PowerShell_profile.ps1", str(_USER_HOME / "Documents")),
    # Git
    ("Git", "全局配置", ".gitconfig", _USER_HOME),
    ("Git", "全局忽略规则", ".gitignore_global", _USER_HOME),
    # npm
    ("npm", "全局配置", ".npmrc", _USER_HOME),
    # pip
    ("pip", "配置文件", "pip/pip.ini", _APPDATA),
    # SSH
    ("SSH", "配置文件", ".ssh/config", _USER_HOME),
    # WSL
    ("WSL", "配置文件", ".wslconfig", _USER_HOME),
    # Clash / 代理
    ("Clash for Windows", "配置", "clash_win/config.yaml", _USER_HOME / ".config"),
    # Notepad++
    ("Notepad++", "配置", "Notepad++/config.xml", _APPDATA),
    # JetBrains (通用)
    ("JetBrains", "配置目录", "JetBrains", _APPDATA),
]


class AppConfigScanner(BaseScanner):
    """扫描应用配置文件。

    根据已知应用配置路径列表，检测哪些配置文件存在，
    收集元数据用于后续打包。
    """

    name = "app_configs"
    description = "扫描应用配置文件"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        """扫描所有已知应用的配置文件。"""
        configs: list[ConfigInfo] = []

        for app_name, desc, rel_path, base in _KNOWN_CONFIGS:
            base_path = Path(base) if isinstance(base, str) else base
            full_path = base_path / rel_path

            if full_path.exists():
                size = self._get_size(full_path)
                config_type = "directory" if full_path.is_dir() else full_path.suffix.lstrip(".")

                configs.append(
                    ConfigInfo(
                        app_name=app_name,
                        config_path=str(full_path),
                        config_type=config_type,
                        size_bytes=size,
                        description=desc,
                    )
                )
                logger.debug("发现配置: %s — %s (%s)", app_name, desc, full_path)

        # 额外扫描 VS Code 扩展列表
        vscode_extensions = self._scan_vscode_extensions()
        if vscode_extensions:
            configs.append(vscode_extensions)

        return ScanResult(
            success=True,
            items_found=len(configs),
            data={"configs": [asdict(c) for c in configs]},
        )

    def _scan_vscode_extensions(self) -> ConfigInfo | None:
        """扫描 VS Code 已安装的扩展列表。"""
        extensions_dir = _USER_HOME / ".vscode" / "extensions"
        if not extensions_dir.exists():
            return None

        # 列出扩展目录名，每个目录就是一个扩展
        extensions = [
            d.name for d in extensions_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        if not extensions:
            return None

        logger.info("发现 %d 个 VS Code 扩展", len(extensions))
        return ConfigInfo(
            app_name="Visual Studio Code",
            config_path=str(extensions_dir),
            config_type="extensions_list",
            size_bytes=0,  # 不需要迁移扩展文件本身，只需要名称列表
            description=f"已安装扩展列表 ({len(extensions)} 个)",
        )

    @staticmethod
    def _get_size(path: Path) -> int:
        """获取文件或目录大小。"""
        try:
            if path.is_file():
                return path.stat().st_size
            if path.is_dir():
                return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        except (OSError, PermissionError):
            pass
        return 0
