"""配置文件恢复器。

将迁移包中的应用配置文件恢复到目标位置。
恢复前会备份已存在的文件，支持 dry-run 模式。
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from easytransfer.core.errors import RestoreError
from easytransfer.core.logging import get_logger

logger = get_logger(__name__)


class ConfigRestorer:
    """配置文件恢复器。

    Attributes:
        extract_dir: 解包后的迁移包目录。
        dry_run: 是否为干跑模式。
    """

    def __init__(
        self,
        extract_dir: str | Path,
        dry_run: bool = False,
    ) -> None:
        self.extract_dir = Path(extract_dir)
        self.dry_run = dry_run

    async def restore(
        self,
        source_path: str,
        target_path: str,
    ) -> str:
        """恢复配置文件到目标位置。

        Args:
            source_path: 包内的相对路径或原始绝对路径（用于在包目录中查找）。
            target_path: 目标位置的绝对路径。

        Returns:
            备份文件路径（如果有备份）；空字符串表示没有备份。

        Raises:
            RestoreError: 恢复失败。
        """
        if not source_path:
            raise RestoreError("source_path 不能为空")

        # 在解包目录中定位源文件
        src = self._resolve_source(source_path)
        dst = Path(target_path) if target_path else None

        if src is None:
            logger.warning("配置文件不在迁移包中: %s", source_path)
            raise RestoreError(
                f"配置文件不在迁移包中: {source_path}",
                details=f"extract_dir={self.extract_dir}",
            )

        if dst is None:
            raise RestoreError("target_path 不能为空")

        logger.info("恢复配置: %s -> %s", src, dst)

        if self.dry_run:
            logger.info("[dry-run] 跳过实际配置恢复: %s", dst)
            return ""

        backup_path = ""
        try:
            # 创建目标目录
            dst.parent.mkdir(parents=True, exist_ok=True)

            # 备份已存在的文件
            if dst.exists():
                backup_path = str(dst) + f".bak.{uuid.uuid4().hex[:8]}"
                shutil.copy2(str(dst), backup_path)
                logger.info("已备份现有文件: %s -> %s", dst, backup_path)

            # 复制配置文件（如果源是目录则递归复制）
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(str(dst))
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))

            logger.info("配置恢复成功: %s", dst)

        except OSError as e:
            raise RestoreError(
                f"配置恢复失败: {dst}",
                details=str(e),
            ) from e

        return backup_path

    def _resolve_source(self, source_path: str) -> Path | None:
        """在解包目录中定位源文件。

        尝试多种方式查找：
        1. 直接作为相对路径
        2. 在 configs/ 子目录下查找
        3. 从原始绝对路径提取相对路径

        Returns:
            找到的源文件路径，找不到则返回 None。
        """
        # 1. 直接作为相对路径
        candidate = self.extract_dir / source_path
        if candidate.exists():
            return candidate

        # 2. 在 configs/ 子目录下查找
        candidate = self.extract_dir / "configs" / source_path
        if candidate.exists():
            return candidate

        # 3. 从绝对路径提取文件名，在 configs/ 下查找
        src_path = Path(source_path)
        if src_path.is_absolute():
            # 尝试用相对于盘符的路径
            try:
                relative = str(src_path.relative_to(src_path.anchor))
            except ValueError:
                relative = src_path.name

            candidate = self.extract_dir / "configs" / relative
            if candidate.exists():
                return candidate

            # 仅用文件名查找
            candidate = self.extract_dir / "configs" / src_path.name
            if candidate.exists():
                return candidate

        return None
