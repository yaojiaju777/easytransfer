"""已安装应用扫描器。

从以下来源识别已安装应用：
1. Windows 注册表 Uninstall 键
2. winget 包列表匹配
"""

from __future__ import annotations

import asyncio
import subprocess
import winreg
from dataclasses import asdict

from easytransfer.core.logging import get_logger
from easytransfer.core.models import AppInfo, InstallSource, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

# 注册表中 Uninstall 的路径
_UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]


class InstalledAppScanner(BaseScanner):
    """扫描 Windows 系统中已安装的应用程序。

    通过读取注册表 Uninstall 键获取应用列表，
    再用 winget 匹配可自动安装的应用。
    """

    name = "installed_apps"
    description = "扫描已安装的应用程序"
    priority = Priority.P0

    def __init__(self, skip_system_apps: bool = True):
        self.skip_system_apps = skip_system_apps

    async def _scan(self) -> ScanResult:
        """执行应用扫描。"""
        # 1. 从注册表读取已安装应用
        apps = await asyncio.to_thread(self._scan_registry)

        # 2. 尝试用 winget 匹配
        winget_map = await self._get_winget_map()
        for app in apps:
            if app.name in winget_map:
                app.winget_id = winget_map[app.name]
                app.install_source = InstallSource.WINGET
                app.can_auto_install = True
                app.install_command = f"winget install --id {app.winget_id} --accept-source-agreements --accept-package-agreements"

        return ScanResult(
            success=True,
            items_found=len(apps),
            data={"apps": [asdict(a) for a in apps]},
        )

    def _scan_registry(self) -> list[AppInfo]:
        """从注册表读取已安装应用列表。"""
        apps: list[AppInfo] = []
        seen_names: set[str] = set()

        for hive, key_path in _UNINSTALL_KEYS:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    subkey_count = winreg.QueryInfoKey(key)[0]
                    for i in range(subkey_count):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            app = self._parse_app_key(hive, key_path, subkey_name)
                            if app and app.name not in seen_names:
                                seen_names.add(app.name)
                                apps.append(app)
                        except OSError:
                            continue
            except OSError:
                continue

        logger.info("从注册表发现 %d 个应用", len(apps))
        return apps

    def _parse_app_key(
        self, hive: int, parent_path: str, subkey_name: str
    ) -> AppInfo | None:
        """解析单个注册表 Uninstall 子键。"""
        full_path = f"{parent_path}\\{subkey_name}"
        try:
            with winreg.OpenKey(hive, full_path) as key:
                name = self._get_reg_value(key, "DisplayName")
                if not name:
                    return None

                # 过滤系统更新和补丁
                if self.skip_system_apps:
                    if self._is_system_app(name, subkey_name):
                        return None

                version = self._get_reg_value(key, "DisplayVersion") or ""
                publisher = self._get_reg_value(key, "Publisher") or ""
                install_path = self._get_reg_value(key, "InstallLocation") or ""

                size_str = self._get_reg_value(key, "EstimatedSize")
                size_bytes = int(size_str) * 1024 if size_str else 0

                return AppInfo(
                    name=name,
                    version=version,
                    publisher=publisher,
                    install_path=install_path,
                    size_bytes=size_bytes,
                )

        except OSError:
            return None

    @staticmethod
    def _get_reg_value(key, value_name: str) -> str | None:
        """安全读取注册表值。"""
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return str(value) if value else None
        except OSError:
            return None

    @staticmethod
    def _is_system_app(name: str, key_name: str) -> bool:
        """判断是否为系统应用/更新/补丁。"""
        skip_patterns = [
            "Update for",
            "Security Update",
            "Hotfix for",
            "Service Pack",
            "Microsoft Visual C++ 20",  # VC++ 运行时太多了
            "Microsoft .NET",
            "Windows SDK",
            "vs_",  # Visual Studio 内部组件
        ]
        name_lower = name.lower()
        key_lower = key_name.lower()

        for pattern in skip_patterns:
            if pattern.lower() in name_lower:
                return True

        # KB 开头的是 Windows 补丁
        if key_lower.startswith("kb") and key_lower[2:].isdigit():
            return True

        return False

    async def _get_winget_map(self) -> dict[str, str]:
        """通过 winget list 获取已安装应用的 winget ID 映射。

        Returns:
            {应用显示名称: winget ID} 的字典。
        """
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["winget", "list", "--disable-interactivity"],
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                logger.warning("winget list 执行失败: %s", result.stderr[:200])
                return {}

            return self._parse_winget_output(result.stdout)
        except FileNotFoundError:
            logger.warning("winget 未安装，跳过 winget 匹配")
            return {}
        except subprocess.TimeoutExpired:
            logger.warning("winget list 超时")
            return {}
        except Exception as e:
            logger.warning("winget 匹配失败: %s", e)
            return {}

    @staticmethod
    def _parse_winget_output(output: str) -> dict[str, str]:
        """解析 winget list 输出。

        winget list 的输出格式（列位置不固定，需要从表头推断）：
        Name            Id                     Version
        -----------------------------------------------
        Google Chrome   Google.Chrome           122.0.6261
        VS Code         Microsoft.VisualStudioCode  1.87.0
        """
        lines = output.strip().split("\n")
        mapping: dict[str, str] = {}

        # 找到分隔线（全是 - 的行）来确定表头位置
        header_idx = -1
        sep_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and all(c in "-─" for c in stripped.replace(" ", "")):
                sep_idx = i
                header_idx = i - 1
                break

        if sep_idx < 0 or header_idx < 0:
            return mapping

        header = lines[header_idx]
        # 找到 Id 列的起始位置
        id_start = header.lower().find("id")
        if id_start < 0:
            return mapping

        # 找到 Version 列的起始位置
        version_start = header.lower().find("version")
        if version_start < 0:
            version_start = header.lower().find("ver")

        id_end = version_start if version_start > id_start else len(header)

        for line in lines[sep_idx + 1:]:
            if len(line) < id_start + 2:
                continue
            name = line[:id_start].strip()
            winget_id = line[id_start:id_end].strip()

            if name and winget_id and "." in winget_id:
                mapping[name] = winget_id

        return mapping
