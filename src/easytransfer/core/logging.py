"""EasyTransfer 日志系统。

基于 Python 标准 logging 模块，集成 rich 美化输出。
支持文件日志和控制台日志两个通道。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# 默认日志目录
_DEFAULT_LOG_DIR = Path.home() / ".easytransfer" / "logs"

# 全局 rich console 实例
console = Console(stderr=True)

# 是否已初始化
_initialized = False


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: Path | None = None,
) -> None:
    """初始化日志系统。

    Args:
        level: 日志级别，默认 INFO。
        log_to_file: 是否同时写入文件。
        log_dir: 日志文件目录，默认 ~/.easytransfer/logs/。
    """
    global _initialized
    if _initialized:
        return

    root_logger = logging.getLogger("easytransfer")
    root_logger.setLevel(level)

    # 控制台输出（使用 rich 美化）
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(level)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 文件输出
    if log_to_file:
        log_path = log_dir or _DEFAULT_LOG_DIR
        log_path.mkdir(parents=True, exist_ok=True)
        log_file = log_path / "easytransfer.log"

        file_handler = logging.FileHandler(
            log_file, encoding="utf-8", mode="a"
        )
        file_handler.setLevel(logging.DEBUG)  # 文件始终记录 DEBUG 级别
        file_format = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取模块专用 logger。

    Args:
        name: 模块名，通常传入 __name__。

    Returns:
        配置好的 Logger 实例。

    Example:
        >>> from easytransfer.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("扫描开始")
    """
    # 确保日志系统已初始化
    if not _initialized:
        setup_logging()

    return logging.getLogger(name)
