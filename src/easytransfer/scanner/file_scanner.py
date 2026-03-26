"""用户文件扫描器。

扫描用户目录下的文件分组（文档、桌面、图片、项目等），
统计数量和大小，用于迁移规划。
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from easytransfer.core.config import load_config
from easytransfer.core.logging import get_logger
from easytransfer.core.models import FileGroup, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

_USER_HOME = Path.home()

# 默认扫描的用户目录
_USER_DIRS = [
    ("Documents", _USER_HOME / "Documents"),
    ("Desktop", _USER_HOME / "Desktop"),
    ("Downloads", _USER_HOME / "Downloads"),
    ("Pictures", _USER_HOME / "Pictures"),
    ("Videos", _USER_HOME / "Videos"),
    ("Music", _USER_HOME / "Music"),
    ("Projects", _USER_HOME / "Projects"),
    ("Source", _USER_HOME / "source"),
]


class UserFileScanner(BaseScanner):
    """扫描用户文件目录。

    遍历用户的文档、桌面等标准目录，
    统计文件数量、大小和类型分布。
    """

    name = "user_files"
    description = "扫描用户文件目录"
    priority = Priority.P0

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        config = load_config()
        self.excluded_dirs = set(config.scan.excluded_dirs)

    async def _scan(self) -> ScanResult:
        """扫描所有用户目录。"""
        groups: list[FileGroup] = []

        for group_name, dir_path in _USER_DIRS:
            if not dir_path.exists():
                continue

            group = self._scan_directory(group_name, dir_path)
            if group.file_count > 0:
                groups.append(group)

        return ScanResult(
            success=True,
            items_found=len(groups),
            data={"file_groups": [asdict(g) for g in groups]},
        )

    def _scan_directory(self, group_name: str, dir_path: Path) -> FileGroup:
        """扫描单个目录。"""
        file_count = 0
        total_size = 0
        ext_counter: Counter[str] = Counter()

        try:
            for root, dirs, files in os.walk(dir_path):
                # 计算当前深度
                depth = str(root).count(os.sep) - str(dir_path).count(os.sep)
                if depth >= self.max_depth:
                    dirs.clear()
                    continue

                # 排除不需要的目录
                dirs[:] = [
                    d for d in dirs
                    if d not in self.excluded_dirs and not d.startswith(".")
                ]

                for f in files:
                    file_path = Path(root) / f
                    try:
                        size = file_path.stat().st_size
                        file_count += 1
                        total_size += size
                        ext = file_path.suffix.lower()
                        if ext:
                            ext_counter[ext] += 1
                    except (OSError, PermissionError):
                        continue

        except PermissionError:
            logger.warning("无权限访问目录: %s", dir_path)

        # 取出现次数最多的 10 种扩展名
        top_extensions = [ext for ext, _ in ext_counter.most_common(10)]

        return FileGroup(
            group_name=group_name,
            source_path=str(dir_path),
            file_count=file_count,
            total_size_bytes=total_size,
            file_extensions=top_extensions,
            excluded_patterns=list(self.excluded_dirs),
        )
