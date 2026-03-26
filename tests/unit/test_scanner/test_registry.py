"""scanner/registry.py 的单元测试。"""

import pytest

from easytransfer.core.models import Priority, ScanResult, ScanScope
from easytransfer.scanner.base import BaseScanner
from easytransfer.scanner.registry import ScannerRegistry


class MockAppsScanner(BaseScanner):
    name = "installed_apps"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        return ScanResult(success=True, items_found=10, data={"apps": []})


class MockFilesScanner(BaseScanner):
    name = "user_files"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        return ScanResult(success=True, items_found=5, data={"files": []})


class MockDevScanner(BaseScanner):
    name = "dev_environment"
    priority = Priority.P1

    async def _scan(self) -> ScanResult:
        return ScanResult(success=True, items_found=3, data={"envs": []})


class MockOptionalScanner(BaseScanner):
    name = "optional"
    priority = Priority.P2

    async def _scan(self) -> ScanResult:
        return ScanResult(success=True, items_found=1, data={})


class TestScannerRegistry:

    def test_register_and_list(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())
        registry.register(MockFilesScanner())
        assert len(registry.scanners) == 2

    def test_scanners_sorted_by_priority(self):
        registry = ScannerRegistry()
        registry.register(MockDevScanner())  # P1
        registry.register(MockAppsScanner())  # P0
        registry.register(MockOptionalScanner())  # P2
        priorities = [s.priority for s in registry.scanners]
        assert priorities == sorted(priorities)

    def test_scope_full_returns_all(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())
        registry.register(MockFilesScanner())
        registry.register(MockDevScanner())
        result = registry.get_scanners_for_scope(ScanScope.FULL)
        assert len(result) == 3

    def test_scope_apps_only(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())
        registry.register(MockFilesScanner())
        registry.register(MockDevScanner())
        result = registry.get_scanners_for_scope(ScanScope.APPS_ONLY)
        assert len(result) == 1
        assert result[0].name == "installed_apps"

    def test_scope_files_only(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())
        registry.register(MockFilesScanner())
        result = registry.get_scanners_for_scope(ScanScope.FILES_ONLY)
        assert len(result) == 1
        assert result[0].name == "user_files"

    @pytest.mark.asyncio
    async def test_run_all(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())
        registry.register(MockFilesScanner())
        results = await registry.run_all()
        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_run_all_with_priority_filter(self):
        registry = ScannerRegistry()
        registry.register(MockAppsScanner())  # P0
        registry.register(MockDevScanner())  # P1
        registry.register(MockOptionalScanner())  # P2
        results = await registry.run_all(max_priority=Priority.P0)
        assert len(results) == 1
