"""浏览器数据扫描器。

扫描 Chrome 和 Edge 的用户配置数据：
书签、扩展列表、是否有已保存密码等。
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

from easytransfer.core.logging import get_logger
from easytransfer.core.models import BrowserProfile, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

_LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))

# 浏览器数据目录
_BROWSERS = [
    ("Chrome", _LOCAL_APPDATA / "Google" / "Chrome" / "User Data"),
    ("Edge", _LOCAL_APPDATA / "Microsoft" / "Edge" / "User Data"),
]


class BrowserScanner(BaseScanner):
    """扫描浏览器数据。

    检测 Chrome 和 Edge 浏览器的：
    - 书签数量
    - 已安装扩展
    - 是否有已保存的密码
    - 数据目录大小
    """

    name = "browser_data"
    description = "扫描浏览器数据（Chrome/Edge）"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        """扫描所有浏览器。"""
        profiles: list[BrowserProfile] = []

        for browser_name, data_dir in _BROWSERS:
            if not data_dir.exists():
                continue

            profile = self._scan_browser(browser_name, data_dir)
            if profile:
                profiles.append(profile)

        return ScanResult(
            success=True,
            items_found=len(profiles),
            data={"browser_profiles": [asdict(p) for p in profiles]},
        )

    def _scan_browser(self, name: str, data_dir: Path) -> BrowserProfile | None:
        """扫描单个浏览器。"""
        # 默认使用 Default profile
        profile_dir = data_dir / "Default"
        if not profile_dir.exists():
            # 尝试 Profile 1
            profile_dir = data_dir / "Profile 1"
            if not profile_dir.exists():
                return None

        bookmarks_count = self._count_bookmarks(profile_dir)
        extensions = self._list_extensions(profile_dir)
        has_passwords = self._check_passwords(profile_dir)
        data_size = self._get_dir_size(profile_dir)

        profile = BrowserProfile(
            browser_name=name,
            profile_path=str(profile_dir),
            bookmarks_count=bookmarks_count,
            extensions=extensions,
            has_saved_passwords=has_passwords,
            data_size_bytes=data_size,
        )

        logger.info(
            "浏览器 %s: %d 个书签, %d 个扩展, 密码=%s, 大小=%.1fMB",
            name,
            bookmarks_count,
            len(extensions),
            has_passwords,
            data_size / (1024 * 1024),
        )
        return profile

    def _count_bookmarks(self, profile_dir: Path) -> int:
        """统计书签数量。"""
        bookmarks_file = profile_dir / "Bookmarks"
        if not bookmarks_file.exists():
            return 0
        try:
            data = json.loads(bookmarks_file.read_text(encoding="utf-8"))
            return self._count_bookmark_nodes(data.get("roots", {}))
        except (json.JSONDecodeError, OSError):
            return 0

    def _count_bookmark_nodes(self, node: dict | list) -> int:
        """递归统计书签节点。"""
        count = 0
        if isinstance(node, dict):
            if node.get("type") == "url":
                count += 1
            for child in node.get("children", []):
                count += self._count_bookmark_nodes(child)
            for key in ("bookmark_bar", "other", "synced"):
                if key in node:
                    count += self._count_bookmark_nodes(node[key])
        return count

    def _list_extensions(self, profile_dir: Path) -> list[str]:
        """列出已安装的扩展名称。"""
        extensions_dir = profile_dir / "Extensions"
        if not extensions_dir.exists():
            return []

        ext_names: list[str] = []
        for ext_dir in extensions_dir.iterdir():
            if not ext_dir.is_dir():
                continue
            # 尝试从 manifest.json 读取扩展名称
            name = self._get_extension_name(ext_dir)
            if name:
                ext_names.append(name)

        return ext_names

    def _get_extension_name(self, ext_dir: Path) -> str | None:
        """从扩展目录的 manifest.json 读取名称。"""
        # 扩展目录结构: Extensions/<ext_id>/<version>/manifest.json
        for version_dir in ext_dir.iterdir():
            if not version_dir.is_dir():
                continue
            manifest = version_dir / "manifest.json"
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    name = data.get("name", "")
                    # 过滤掉 Chrome 内部扩展
                    if name and not name.startswith("__MSG_") and len(name) < 100:
                        return name
                except (json.JSONDecodeError, OSError):
                    pass
        return None

    def _check_passwords(self, profile_dir: Path) -> bool:
        """检查是否有已保存的密码。

        注意：只检查是否存在，不读取密码内容。
        """
        login_data = profile_dir / "Login Data"
        if not login_data.exists():
            return False
        try:
            # Login Data 是 SQLite 数据库，检查是否有记录
            # 需要复制一份因为浏览器可能正在使用
            import shutil
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            shutil.copy2(login_data, tmp_path)

            try:
                conn = sqlite3.connect(tmp_path)
                cursor = conn.execute("SELECT COUNT(*) FROM logins")
                count = cursor.fetchone()[0]
                conn.close()
                return count > 0
            finally:
                os.unlink(tmp_path)

        except Exception:
            # 如果无法读取，假设有密码（安全侧）
            return True

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """计算目录大小（只计算顶层，不深度遍历）。"""
        total = 0
        try:
            for item in path.iterdir():
                if item.is_file():
                    total += item.stat().st_size
                elif item.is_dir():
                    # 只统计一层子目录大小，避免太慢
                    try:
                        for f in item.iterdir():
                            if f.is_file():
                                total += f.stat().st_size
                    except PermissionError:
                        pass
        except PermissionError:
            pass
        return total
