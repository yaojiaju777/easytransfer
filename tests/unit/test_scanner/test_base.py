"""scanner/base.py 的单元测试。"""

import pytest

from easytransfer.core.models import Priority, ScanResult
from easytransfer.scanner.base import BaseScanner


class SuccessScanner(BaseScanner):
    name = "test_success"
    description = "总是成功的扫描器"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        return ScanResult(success=True, items_found=5, data={"items": [1, 2, 3, 4, 5]})


class FailScanner(BaseScanner):
    name = "test_fail"
    description = "总是失败的扫描器"
    priority = Priority.P1

    async def _scan(self) -> ScanResult:
        raise RuntimeError("模拟扫描失败")


class TestBaseScanner:

    @pytest.mark.asyncio
    async def test_successful_scan(self):
        scanner = SuccessScanner()
        result = await scanner.scan()
        assert result.success is True
        assert result.items_found == 5
        assert result.scanner_name == "test_success"
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_failed_scan_returns_error_result(self):
        """失败的扫描不应抛出异常，而是返回失败的 ScanResult。"""
        scanner = FailScanner()
        result = await scanner.scan()
        assert result.success is False
        assert "模拟扫描失败" in result.error_message
        assert result.scanner_name == "test_fail"
