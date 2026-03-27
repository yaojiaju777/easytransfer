"""Winget 应用安装器。

通过 winget 命令行工具安装应用程序。
支持 dry-run 模式（仅记录日志，不真正执行）。
"""

from __future__ import annotations

import asyncio
import subprocess

from easytransfer.core.errors import InstallError
from easytransfer.core.logging import get_logger

logger = get_logger(__name__)


class WingetInstaller:
    """通过 winget 安装应用。

    Attributes:
        dry_run: 是否为干跑模式。
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    async def install(self, winget_id: str, command: str | None = None) -> None:
        """安装指定的应用。

        Args:
            winget_id: winget 包 ID，例如 "Google.Chrome"。
            command: 完整的安装命令。如未指定，自动构建。

        Raises:
            InstallError: 安装失败。
        """
        if not winget_id:
            raise InstallError("winget_id 不能为空")

        install_cmd = command or self.build_install_command(winget_id)
        logger.info("安装应用: %s (command=%s)", winget_id, install_cmd)

        if self.dry_run:
            logger.info("[dry-run] 跳过实际安装: %s", winget_id)
            return

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                install_cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 分钟超时
                shell=True,
            )

            if result.returncode != 0:
                error_output = result.stderr or result.stdout or "未知错误"
                raise InstallError(
                    f"winget 安装失败: {winget_id}",
                    details=error_output[:500],
                )

            logger.info("应用安装成功: %s", winget_id)

        except subprocess.TimeoutExpired:
            raise InstallError(
                f"安装超时: {winget_id}",
                details="安装过程超过 10 分钟",
            )
        except OSError as e:
            raise InstallError(
                f"无法执行 winget: {e}",
                details="请确认 winget 已安装",
            )

    async def uninstall(self, winget_id: str) -> None:
        """卸载指定的应用（用于回滚）。

        Args:
            winget_id: winget 包 ID。

        Raises:
            InstallError: 卸载失败。
        """
        if not winget_id:
            raise InstallError("winget_id 不能为空")

        cmd = f"winget uninstall --id {winget_id} --accept-source-agreements"
        logger.info("卸载应用: %s", winget_id)

        if self.dry_run:
            logger.info("[dry-run] 跳过实际卸载: %s", winget_id)
            return

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                shell=True,
            )

            if result.returncode != 0:
                error_output = result.stderr or result.stdout or "未知错误"
                raise InstallError(
                    f"winget 卸载失败: {winget_id}",
                    details=error_output[:500],
                )

            logger.info("应用卸载成功: %s", winget_id)

        except subprocess.TimeoutExpired:
            raise InstallError(
                f"卸载超时: {winget_id}",
                details="卸载过程超过 5 分钟",
            )

    async def is_installed(self, winget_id: str) -> bool:
        """检查应用是否已安装。

        Args:
            winget_id: winget 包 ID。

        Returns:
            True 如果应用已安装。
        """
        if self.dry_run:
            logger.info("[dry-run] 检查安装状态: %s", winget_id)
            return False

        cmd = f"winget list --id {winget_id} --accept-source-agreements"

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )
            # winget list 返回 0 且输出包含 ID 时表示已安装
            return result.returncode == 0 and winget_id in (result.stdout or "")
        except (subprocess.TimeoutExpired, OSError):
            return False

    @staticmethod
    def build_install_command(winget_id: str) -> str:
        """构建 winget 安装命令。

        Args:
            winget_id: winget 包 ID。

        Returns:
            完整的 winget 安装命令字符串。
        """
        return (
            f"winget install --id {winget_id} "
            f"--accept-source-agreements --accept-package-agreements"
        )
