"""环境扫描模块 — 扫描当前电脑的软件环境。"""

from easytransfer.scanner.registry import ScannerRegistry, create_default_registry

__all__ = ["ScannerRegistry", "create_default_registry"]
