"""扫描器注册表。

管理所有扫描器的注册、发现和批量执行。
"""

from __future__ import annotations

import asyncio

from easytransfer.core.logging import get_logger
from easytransfer.core.models import Priority, ScanResult, ScanScope
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)


class ScannerRegistry:
    """扫描器注册和管理中心。

    Example:
        >>> registry = ScannerRegistry()
        >>> registry.register(InstalledAppScanner())
        >>> results = await registry.run_all()
    """

    def __init__(self) -> None:
        self._scanners: list[BaseScanner] = []

    def register(self, scanner: BaseScanner) -> None:
        """注册一个扫描器。"""
        self._scanners.append(scanner)
        logger.debug("注册扫描器: %s (P%d)", scanner.name, scanner.priority)

    @property
    def scanners(self) -> list[BaseScanner]:
        """返回所有已注册的扫描器（按优先级排序）。"""
        return sorted(self._scanners, key=lambda s: s.priority)

    def get_scanners_for_scope(self, scope: ScanScope) -> list[BaseScanner]:
        """根据扫描范围筛选扫描器。

        Args:
            scope: 扫描范围。

        Returns:
            匹配的扫描器列表。
        """
        if scope == ScanScope.FULL:
            return self.scanners

        # 扫描器名到范围的映射
        scope_map: dict[ScanScope, set[str]] = {
            ScanScope.APPS_ONLY: {"installed_apps", "app_configs"},
            ScanScope.FILES_ONLY: {"user_files"},
            ScanScope.DEV_ONLY: {"dev_environment", "git_ssh"},
        }

        allowed_names = scope_map.get(scope, set())
        return [s for s in self.scanners if s.name in allowed_names]

    async def run_all(
        self,
        scope: ScanScope = ScanScope.FULL,
        max_priority: Priority = Priority.P2,
    ) -> list[ScanResult]:
        """运行所有匹配的扫描器。

        Args:
            scope: 扫描范围。
            max_priority: 最大优先级（包含），P2 表示运行所有。

        Returns:
            所有扫描结果列表。
        """
        scanners = self.get_scanners_for_scope(scope)
        scanners = [s for s in scanners if s.priority <= max_priority]

        logger.info("准备运行 %d 个扫描器 (scope=%s)", len(scanners), scope.value)

        # 按优先级分组：P0 先运行完，再运行 P1，再 P2
        results: list[ScanResult] = []
        for priority in Priority:
            if priority > max_priority:
                break
            group = [s for s in scanners if s.priority == priority]
            if not group:
                continue

            logger.info("运行 P%d 扫描器: %s", priority, [s.name for s in group])
            group_results = await asyncio.gather(
                *(s.scan() for s in group),
                return_exceptions=False,
            )
            results.extend(group_results)

        success = sum(1 for r in results if r.success)
        logger.info("扫描完成: %d/%d 成功", success, len(results))
        return results


def create_default_registry() -> ScannerRegistry:
    """创建包含所有默认扫描器的注册表。

    Returns:
        配置好的 ScannerRegistry。
    """
    from easytransfer.scanner.app_scanner import InstalledAppScanner
    from easytransfer.scanner.browser_scanner import BrowserScanner
    from easytransfer.scanner.config_scanner import AppConfigScanner
    from easytransfer.scanner.dev_env_scanner import DevEnvScanner
    from easytransfer.scanner.file_scanner import UserFileScanner
    from easytransfer.scanner.git_ssh_scanner import GitSshScanner

    registry = ScannerRegistry()
    registry.register(InstalledAppScanner())
    registry.register(AppConfigScanner())
    registry.register(UserFileScanner())
    registry.register(BrowserScanner())
    registry.register(DevEnvScanner())
    registry.register(GitSshScanner())

    return registry
