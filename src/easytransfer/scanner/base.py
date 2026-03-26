"""扫描器基类。

所有具体扫描器继承此基类，实现统一的扫描接口。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from easytransfer.core.logging import get_logger
from easytransfer.core.models import Priority, ScanResult

logger = get_logger(__name__)


class BaseScanner(ABC):
    """扫描器抽象基类。

    所有扫描器必须实现 _scan() 方法。
    基类提供统一的错误处理、计时和日志。

    Attributes:
        name: 扫描器名称。
        description: 扫描器描述。
        priority: 优先级（P0=核心, P1=重要, P2=可选）。
    """

    name: str = ""
    description: str = ""
    priority: Priority = Priority.P0

    async def scan(self) -> ScanResult:
        """执行扫描（外部调用入口）。

        自动处理计时、日志和异常捕获。

        Returns:
            ScanResult: 扫描结果。
        """
        logger.info("开始扫描: %s", self.name)
        start = time.time()

        try:
            result = await self._scan()
            result.scanner_name = self.name
            result.duration_seconds = round(time.time() - start, 2)
            logger.info(
                "扫描完成: %s, 发现 %d 项, 耗时 %.1fs",
                self.name,
                result.items_found,
                result.duration_seconds,
            )
            return result
        except Exception as e:
            duration = round(time.time() - start, 2)
            logger.error("扫描失败: %s, 错误: %s", self.name, e)
            return ScanResult(
                scanner_name=self.name,
                success=False,
                error_message=str(e),
                duration_seconds=duration,
            )

    @abstractmethod
    async def _scan(self) -> ScanResult:
        """执行实际扫描逻辑（子类实现）。

        Returns:
            ScanResult: 包含扫描数据的结果。
        """
        ...
