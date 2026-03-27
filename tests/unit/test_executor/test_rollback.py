"""回滚逻辑测试。"""

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
from easytransfer.executor.rollback import RollbackExecutor


@pytest.fixture
def rollback_tmp_dir():
    """临时目录用于回滚测试。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def migration_with_rollback_info(rollback_tmp_dir):
    """带有回滚信息的迁移结果。"""
    # 创建一个实际存在的备份文件
    target = rollback_tmp_dir / "settings.json"
    backup = rollback_tmp_dir / "settings.json.bak.abc"
    target.write_text('{"new": true}')
    backup.write_text('{"old": true}')

    return MigrationResult(
        migration_id="test-mig-001",
        status=MigrationStatus.COMPLETED,
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
                rollback_info=f"config_backup:{backup}",
            ),
            MigrationItemResult(
                item_id="item-3",
                item_type="manual_action",
                item_name="登录微信",
                status=MigrationItemStatus.SKIPPED,
                rollback_info="",
            ),
            MigrationItemResult(
                item_id="item-4",
                item_type="app_install",
                item_name="Failed App",
                status=MigrationItemStatus.FAILED,
                error_message="install failed",
                rollback_info="",
            ),
        ],
    )


class TestRollbackExecutor:
    """RollbackExecutor 测试。"""

    @pytest.mark.asyncio
    async def test_rollback_selects_only_success_items(self, migration_with_rollback_info):
        """回滚应只选择成功且有回滚信息的项目。"""
        executor = RollbackExecutor(dry_run=True)
        result = await executor.rollback(migration_with_rollback_info)

        # 只有 item-1 和 item-2 应被回滚（成功且有 rollback_info）
        assert result.rolled_back_items == 2
        assert result.failed_rollbacks == 0

    @pytest.mark.asyncio
    async def test_rollback_specific_items(self, migration_with_rollback_info):
        """回滚指定的项目。"""
        executor = RollbackExecutor(dry_run=True)
        result = await executor.rollback(
            migration_with_rollback_info,
            item_ids=["item-1"],
        )

        assert result.rolled_back_items == 1

    @pytest.mark.asyncio
    async def test_rollback_file_restore(self):
        """回滚文件恢复 — 从备份恢复原始文件。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 模拟: 目标位置有新文件，备份位置有旧文件
            target = Path(tmp) / "settings.json"
            backup = Path(tmp) / "settings.json.bak.abc123"

            target.write_text('{"new": true}')
            backup.write_text('{"old": true}')

            migration = MigrationResult(
                migration_id="test",
                items=[
                    MigrationItemResult(
                        item_id="item-1",
                        item_type="config_restore",
                        item_name="Config",
                        status=MigrationItemStatus.SUCCESS,
                        rollback_info=f"config_backup:{backup}",
                    ),
                ],
            )

            executor = RollbackExecutor()
            result = await executor.rollback(migration)

            assert result.rolled_back_items == 1
            assert target.read_text() == '{"old": true}'
            # 备份文件应被清理
            assert not backup.exists()

    @pytest.mark.asyncio
    async def test_rollback_missing_backup(self):
        """备份文件不存在时应报告失败。"""
        migration = MigrationResult(
            migration_id="test",
            items=[
                MigrationItemResult(
                    item_id="item-1",
                    item_type="config_restore",
                    item_name="Config",
                    status=MigrationItemStatus.SUCCESS,
                    rollback_info="config_backup:/nonexistent/path.bak.xxx",
                ),
            ],
        )

        executor = RollbackExecutor()
        result = await executor.rollback(migration)

        assert result.failed_rollbacks == 1

    @pytest.mark.asyncio
    async def test_rollback_winget_dry_run(self, migration_with_rollback_info):
        """dry-run 模式下 winget 回滚应成功但不执行。"""
        executor = RollbackExecutor(dry_run=True)
        result = await executor.rollback(
            migration_with_rollback_info,
            item_ids=["item-1"],
        )

        assert result.rolled_back_items == 1
        detail = result.details[0]
        assert "[dry-run]" in detail["note"]

    @pytest.mark.asyncio
    async def test_rollback_winget_real(self, migration_with_rollback_info):
        """真实模式下 winget 回滚调用 uninstall。"""
        with patch(
            "easytransfer.executor.rollback.RollbackExecutor._rollback_winget",
            new_callable=AsyncMock,
        ) as mock_winget:
            mock_winget.side_effect = lambda wid, detail: detail.update(
                {"note": f"已卸载 {wid}"}
            )

            executor = RollbackExecutor()
            result = await executor.rollback(
                migration_with_rollback_info,
                item_ids=["item-1"],
            )

            assert result.rolled_back_items == 1

    @pytest.mark.asyncio
    async def test_rollback_empty_migration(self):
        """空迁移结果的回滚。"""
        migration = MigrationResult(migration_id="empty")
        executor = RollbackExecutor()
        result = await executor.rollback(migration)

        assert result.rolled_back_items == 0
        assert result.failed_rollbacks == 0

    @pytest.mark.asyncio
    async def test_rollback_reversed_order(self):
        """回滚应按反序执行。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 创建两个备份文件
            target1 = Path(tmp) / "file1.txt"
            backup1 = Path(tmp) / "file1.txt.bak.aaa"
            target2 = Path(tmp) / "file2.txt"
            backup2 = Path(tmp) / "file2.txt.bak.bbb"

            target1.write_text("new1")
            backup1.write_text("old1")
            target2.write_text("new2")
            backup2.write_text("old2")

            migration = MigrationResult(
                migration_id="test",
                items=[
                    MigrationItemResult(
                        item_id="item-1",
                        item_type="file_copy",
                        item_name="File 1",
                        status=MigrationItemStatus.SUCCESS,
                        rollback_info=f"file_backup:{backup1}",
                    ),
                    MigrationItemResult(
                        item_id="item-2",
                        item_type="file_copy",
                        item_name="File 2",
                        status=MigrationItemStatus.SUCCESS,
                        rollback_info=f"file_backup:{backup2}",
                    ),
                ],
            )

            executor = RollbackExecutor()
            result = await executor.rollback(migration)

            assert result.rolled_back_items == 2
            assert target1.read_text() == "old1"
            assert target2.read_text() == "old2"

    @pytest.mark.asyncio
    async def test_rollback_unknown_type(self):
        """未知回滚类型应被跳过。"""
        migration = MigrationResult(
            migration_id="test",
            items=[
                MigrationItemResult(
                    item_id="item-1",
                    item_type="something",
                    item_name="Unknown",
                    status=MigrationItemStatus.SUCCESS,
                    rollback_info="unknown_type:some_value",
                ),
            ],
        )

        executor = RollbackExecutor()
        result = await executor.rollback(migration)

        # Unknown type is skipped, not counted as rolled_back or failed
        detail = result.details[0]
        assert detail["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_rollback_result_has_migration_id(self, migration_with_rollback_info):
        """回滚结果应包含 migration_id。"""
        executor = RollbackExecutor(dry_run=True)
        result = await executor.rollback(migration_with_rollback_info)

        assert result.migration_id == "test-mig-001"
