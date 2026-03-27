"""迁移验证器测试。"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from easytransfer.core.models import (
    MigrationItemResult,
    MigrationItemStatus,
    MigrationResult,
    MigrationStatus,
)
from easytransfer.executor.verifier import MigrationVerifier


@pytest.fixture
def successful_migration():
    """成功的迁移结果。"""
    return MigrationResult(
        migration_id="test-mig-001",
        status=MigrationStatus.COMPLETED,
        total_items=3,
        success_count=3,
        items=[
            MigrationItemResult(
                item_id="item-1",
                item_type="app_install",
                item_name="Google Chrome",
                status=MigrationItemStatus.SUCCESS,
                rollback_info="winget_uninstall:Google.Chrome",
            ),
            MigrationItemResult(
                item_id="item-2",
                item_type="config_restore",
                item_name="VS Code 配置",
                status=MigrationItemStatus.SUCCESS,
                rollback_info="config_backup:/tmp/settings.json.bak.abc123",
            ),
            MigrationItemResult(
                item_id="item-3",
                item_type="file_copy",
                item_name="Documents",
                status=MigrationItemStatus.SUCCESS,
                rollback_info="",
            ),
        ],
    )


@pytest.fixture
def partial_migration():
    """部分成功的迁移结果。"""
    return MigrationResult(
        migration_id="test-mig-002",
        status=MigrationStatus.PARTIALLY_COMPLETED,
        total_items=3,
        success_count=1,
        failed_count=1,
        skipped_count=1,
        items=[
            MigrationItemResult(
                item_id="item-1",
                item_type="app_install",
                item_name="Chrome",
                status=MigrationItemStatus.SUCCESS,
                rollback_info="winget_uninstall:Google.Chrome",
            ),
            MigrationItemResult(
                item_id="item-2",
                item_type="app_install",
                item_name="Old App",
                status=MigrationItemStatus.FAILED,
                error_message="winget not found",
            ),
            MigrationItemResult(
                item_id="item-3",
                item_type="manual_action",
                item_name="登录微信",
                status=MigrationItemStatus.SKIPPED,
            ),
        ],
    )


class TestMigrationVerifier:
    """MigrationVerifier 测试。"""

    @pytest.mark.asyncio
    async def test_verify_skipped_items(self, partial_migration):
        """跳过的项目不应计入检查总数。"""
        verifier = MigrationVerifier(dry_run=True)
        report = await verifier.verify(partial_migration)

        # 1 success + 1 failed = 2 checked, 1 skipped not counted
        assert report.total_checked == 2
        # 查找 skipped detail
        skipped = [d for d in report.details if d["status"] == "skipped"]
        assert len(skipped) == 1

    @pytest.mark.asyncio
    async def test_verify_failed_items(self, partial_migration):
        """失败的项目应标记为失败。"""
        verifier = MigrationVerifier(dry_run=True)
        report = await verifier.verify(partial_migration)

        failed = [d for d in report.details if d["status"] == "failed"]
        assert len(failed) >= 1

    @pytest.mark.asyncio
    async def test_verify_app_install_dry_run(self, successful_migration):
        """dry-run 模式下应用安装验证应通过。"""
        verifier = MigrationVerifier(dry_run=True)
        report = await verifier.verify(successful_migration)

        app_items = [d for d in report.details if d["item_type"] == "app_install"]
        assert len(app_items) == 1
        assert app_items[0]["status"] == "passed"

    @pytest.mark.asyncio
    async def test_verify_file_restore_with_existing_target(self):
        """文件恢复验证 — 目标文件存在应通过。"""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "settings.json"
            target.write_text("{}")
            backup_path = str(target) + ".bak.abc123"

            migration = MigrationResult(
                migration_id="test",
                items=[
                    MigrationItemResult(
                        item_id="item-1",
                        item_type="config_restore",
                        item_name="Config",
                        status=MigrationItemStatus.SUCCESS,
                        rollback_info=f"config_backup:{backup_path}",
                    ),
                ],
            )

            verifier = MigrationVerifier()
            report = await verifier.verify(migration)

            assert report.passed == 1

    @pytest.mark.asyncio
    async def test_verify_file_restore_target_missing(self):
        """文件恢复验证 — 目标文件不存在应失败。"""
        backup_path = "/nonexistent/path/settings.json.bak.abc123"

        migration = MigrationResult(
            migration_id="test",
            items=[
                MigrationItemResult(
                    item_id="item-1",
                    item_type="config_restore",
                    item_name="Config",
                    status=MigrationItemStatus.SUCCESS,
                    rollback_info=f"config_backup:{backup_path}",
                ),
            ],
        )

        verifier = MigrationVerifier()
        report = await verifier.verify(migration)

        assert report.failed == 1

    @pytest.mark.asyncio
    async def test_verify_empty_migration(self):
        """空迁移结果的验证。"""
        migration = MigrationResult(migration_id="empty")
        verifier = MigrationVerifier()
        report = await verifier.verify(migration)

        assert report.total_checked == 0
        assert report.passed == 0
        assert report.failed == 0

    @pytest.mark.asyncio
    async def test_verify_no_rollback_info(self):
        """没有 rollback_info 的成功项目应通过。"""
        migration = MigrationResult(
            migration_id="test",
            items=[
                MigrationItemResult(
                    item_id="item-1",
                    item_type="file_copy",
                    item_name="Files",
                    status=MigrationItemStatus.SUCCESS,
                    rollback_info="",
                ),
            ],
        )

        verifier = MigrationVerifier()
        report = await verifier.verify(migration)

        assert report.passed == 1

    @pytest.mark.asyncio
    async def test_verify_report_has_migration_id(self, successful_migration):
        """验证报告应包含 migration_id。"""
        verifier = MigrationVerifier(dry_run=True)
        report = await verifier.verify(successful_migration)

        assert report.migration_id == "test-mig-001"
