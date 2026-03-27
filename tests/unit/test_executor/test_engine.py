"""迁移执行引擎测试。

使用 mock 数据测试引擎的编排逻辑，
不会实际安装应用或修改文件系统。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from easytransfer.core.models import (
    MigrationItemStatus,
    MigrationStatus,
)
from easytransfer.executor.engine import MigrationExecutor
from easytransfer.planner.plan_builder import MigrationPlan, PlanAction, PlanGroup


@pytest.fixture
def tmp_extract_dir():
    """创建模拟解包目录。"""
    with tempfile.TemporaryDirectory() as d:
        extract = Path(d) / "extract"
        extract.mkdir()
        # 创建 configs 子目录
        configs = extract / "configs"
        configs.mkdir()
        (configs / "settings.json").write_text('{"key": "value"}')
        # 创建 files 子目录
        files = extract / "files"
        files.mkdir()
        (files / "document.txt").write_text("hello world")
        yield extract


@pytest.fixture
def simple_plan():
    """简单的迁移计划（一个 winget 安装 + 一个配置恢复）。"""
    app_group = PlanGroup(
        group_type="app_install",
        group_name="应用安装",
        actions=[
            PlanAction(
                action_id="act-001",
                action_type="app_install",
                name="Google Chrome",
                method="winget",
                command="winget install --id Google.Chrome --accept-source-agreements --accept-package-agreements",
                details={"winget_id": "Google.Chrome"},
            ),
        ],
    )

    config_group = PlanGroup(
        group_type="config_restore",
        group_name="配置恢复",
        actions=[
            PlanAction(
                action_id="act-002",
                action_type="config_restore",
                name="VS Code 配置",
                method="copy",
                source_path="configs/settings.json",
                target_path="C:\\Users\\test\\AppData\\Roaming\\Code\\settings.json",
            ),
        ],
    )

    return MigrationPlan(
        groups=[app_group, config_group],
        total_actions=2,
    )


@pytest.fixture
def plan_with_manual_action():
    """包含手动操作的计划。"""
    group = PlanGroup(
        group_type="manual_action",
        group_name="需要手动操作",
        actions=[
            PlanAction(
                action_id="act-manual",
                action_type="manual_action",
                name="登录微信",
                description="请手动登录微信",
                requires_user_action=True,
            ),
        ],
    )
    return MigrationPlan(groups=[group], total_actions=1)


@pytest.fixture
def plan_with_file_copy():
    """包含文件复制的计划。"""
    group = PlanGroup(
        group_type="file_copy",
        group_name="文件迁移",
        actions=[
            PlanAction(
                action_id="act-file",
                action_type="file_copy",
                name="Documents",
                method="copy",
                source_path="files/document.txt",
                target_path="C:\\Users\\test\\Documents\\document.txt",
            ),
        ],
    )
    return MigrationPlan(groups=[group], total_actions=1)


class TestMigrationExecutor:
    """MigrationExecutor 测试。"""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_install(self, tmp_extract_dir, simple_plan):
        """dry-run 模式不应实际安装任何东西。"""
        executor = MigrationExecutor(
            extract_dir=tmp_extract_dir,
            plan=simple_plan,
            dry_run=True,
        )
        result = await executor.execute()

        assert result.status in (
            MigrationStatus.COMPLETED,
            MigrationStatus.PARTIALLY_COMPLETED,
        )
        assert result.total_items == 2

    @pytest.mark.asyncio
    async def test_execute_with_mock_winget(self, tmp_extract_dir, simple_plan):
        """使用 mock winget 安装器测试执行流程。"""
        with patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_app_install",
            new_callable=AsyncMock,
            return_value="winget_uninstall:Google.Chrome",
        ), patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_config_restore",
            new_callable=AsyncMock,
            return_value="config_backup:/tmp/bak",
        ):
            executor = MigrationExecutor(
                extract_dir=tmp_extract_dir,
                plan=simple_plan,
            )
            result = await executor.execute()

        assert result.status == MigrationStatus.COMPLETED
        assert result.success_count == 2
        assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_partial_failure(self, tmp_extract_dir, simple_plan):
        """单个动作失败不阻止其他动作。"""
        with patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_app_install",
            new_callable=AsyncMock,
            side_effect=Exception("winget not found"),
        ), patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_config_restore",
            new_callable=AsyncMock,
            return_value="",
        ):
            executor = MigrationExecutor(
                extract_dir=tmp_extract_dir,
                plan=simple_plan,
            )
            result = await executor.execute()

        assert result.status == MigrationStatus.PARTIALLY_COMPLETED
        assert result.success_count == 1
        assert result.failed_count == 1

    @pytest.mark.asyncio
    async def test_all_failures(self, tmp_extract_dir, simple_plan):
        """所有动作都失败时状态为 FAILED。"""
        with patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_app_install",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ), patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_config_restore",
            new_callable=AsyncMock,
            side_effect=Exception("fail"),
        ):
            executor = MigrationExecutor(
                extract_dir=tmp_extract_dir,
                plan=simple_plan,
            )
            result = await executor.execute()

        assert result.status == MigrationStatus.FAILED
        assert result.success_count == 0
        assert result.failed_count == 2

    @pytest.mark.asyncio
    async def test_manual_action_skipped(self, tmp_extract_dir, plan_with_manual_action):
        """需要手动操作的项目应被跳过并记录到 manual_actions。"""
        executor = MigrationExecutor(
            extract_dir=tmp_extract_dir,
            plan=plan_with_manual_action,
        )
        result = await executor.execute()

        assert result.skipped_count == 1
        assert len(result.manual_actions) == 1
        assert "请手动登录微信" in result.manual_actions[0]

    @pytest.mark.asyncio
    async def test_empty_plan(self, tmp_extract_dir):
        """空计划应正常完成。"""
        empty_plan = MigrationPlan(groups=[], total_actions=0)
        executor = MigrationExecutor(
            extract_dir=tmp_extract_dir,
            plan=empty_plan,
        )
        result = await executor.execute()

        assert result.status == MigrationStatus.COMPLETED
        assert result.total_items == 0

    @pytest.mark.asyncio
    async def test_result_records_duration(self, tmp_extract_dir, simple_plan):
        """每个结果项应记录执行时长。"""
        with patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_app_install",
            new_callable=AsyncMock,
            return_value="",
        ), patch(
            "easytransfer.executor.engine.MigrationExecutor._handle_config_restore",
            new_callable=AsyncMock,
            return_value="",
        ):
            executor = MigrationExecutor(
                extract_dir=tmp_extract_dir,
                plan=simple_plan,
            )
            result = await executor.execute()

        for item in result.items:
            assert item.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_result_has_migration_id(self, tmp_extract_dir, simple_plan):
        """结果应有 migration_id。"""
        with patch(
            "easytransfer.executor.engine.MigrationExecutor._dispatch_action",
            new_callable=AsyncMock,
            return_value="",
        ):
            executor = MigrationExecutor(
                extract_dir=tmp_extract_dir,
                plan=simple_plan,
            )
            result = await executor.execute()

        assert result.migration_id
        assert len(result.migration_id) > 0

    @pytest.mark.asyncio
    async def test_unknown_action_type(self, tmp_extract_dir):
        """未知动作类型应不报错。"""
        group = PlanGroup(
            group_type="unknown",
            group_name="未知",
            actions=[
                PlanAction(
                    action_id="act-unknown",
                    action_type="unknown_type",
                    name="Unknown Action",
                ),
            ],
        )
        plan = MigrationPlan(groups=[group], total_actions=1)
        executor = MigrationExecutor(
            extract_dir=tmp_extract_dir,
            plan=plan,
        )
        result = await executor.execute()

        # Unknown type dispatches but returns "", which is a success
        assert result.total_items == 1
        assert result.items[0].status == MigrationItemStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_skip_method_app_install(self, tmp_extract_dir):
        """method=skip 的应用安装应返回空字符串（成功）。"""
        group = PlanGroup(
            group_type="app_install",
            group_name="应用安装",
            actions=[
                PlanAction(
                    action_id="act-skip",
                    action_type="app_install",
                    name="System App",
                    method="skip",
                ),
            ],
        )
        plan = MigrationPlan(groups=[group], total_actions=1)
        executor = MigrationExecutor(
            extract_dir=tmp_extract_dir,
            plan=plan,
        )
        result = await executor.execute()

        assert result.success_count == 1
