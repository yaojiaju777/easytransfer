"""迁移执行引擎。

处理迁移计划的主引擎，按组顺序执行每个动作，
记录结果并支持 dry-run 模式。

核心原则：
- 优雅降级：单个动作失败不阻止其他动作
- 每个动作记录回滚信息
- 支持 dry-run 模式（仅模拟，不真正执行）
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from easytransfer.core.errors import ExecutionError
from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    MigrationItemResult,
    MigrationItemStatus,
    MigrationResult,
    MigrationStatus,
)
from easytransfer.planner.plan_builder import MigrationPlan, PlanAction, PlanGroup

logger = get_logger(__name__)


class MigrationExecutor:
    """迁移执行引擎。

    从解包后的迁移目录读取数据，按照迁移计划逐步执行恢复操作。

    Attributes:
        extract_dir: 解包后的迁移包目录。
        plan: 迁移执行计划。
        dry_run: 是否为干跑模式（仅模拟，不真正执行）。
    """

    def __init__(
        self,
        extract_dir: str | Path,
        plan: MigrationPlan,
        dry_run: bool = False,
    ) -> None:
        self.extract_dir = Path(extract_dir)
        self.plan = plan
        self.dry_run = dry_run
        self._results: list[MigrationItemResult] = []
        self._manual_actions: list[str] = []

    async def execute(self) -> MigrationResult:
        """执行迁移计划。

        按组顺序执行每个动作，记录结果。
        单个动作失败不阻止其他动作执行（优雅降级）。

        Returns:
            迁移执行结果。
        """
        migration_result = MigrationResult(
            status=MigrationStatus.RESTORING,
            started_at=datetime.now(),
            total_items=self.plan.total_actions,
        )

        logger.info(
            "开始执行迁移计划: %d 个组, %d 个动作, dry_run=%s",
            len(self.plan.groups),
            self.plan.total_actions,
            self.dry_run,
        )

        for group in self.plan.groups:
            await self._execute_group(group)

        # 汇总结果
        migration_result.items = self._results
        migration_result.manual_actions = self._manual_actions
        migration_result.completed_at = datetime.now()
        migration_result.success_count = sum(
            1 for r in self._results if r.status == MigrationItemStatus.SUCCESS
        )
        migration_result.failed_count = sum(
            1 for r in self._results if r.status == MigrationItemStatus.FAILED
        )
        migration_result.skipped_count = sum(
            1 for r in self._results if r.status == MigrationItemStatus.SKIPPED
        )
        migration_result.total_items = len(self._results)

        if migration_result.failed_count == 0:
            migration_result.status = MigrationStatus.COMPLETED
        elif migration_result.success_count > 0:
            migration_result.status = MigrationStatus.PARTIALLY_COMPLETED
        else:
            migration_result.status = MigrationStatus.FAILED

        logger.info(
            "迁移执行完成: 成功=%d, 失败=%d, 跳过=%d",
            migration_result.success_count,
            migration_result.failed_count,
            migration_result.skipped_count,
        )

        return migration_result

    async def _execute_group(self, group: PlanGroup) -> None:
        """执行一个动作组。"""
        logger.info("执行组: %s (%d 个动作)", group.group_name, len(group.actions))

        for action in group.actions:
            await self._execute_action(action)

    async def _execute_action(self, action: PlanAction) -> None:
        """执行单个动作。

        根据 action_type 分发到对应的处理器。
        任何异常都会被捕获并记录为失败，不中断后续执行。
        """
        start_time = time.time()
        item_result = MigrationItemResult(
            item_id=action.action_id,
            item_type=action.action_type,
            item_name=action.name,
            status=MigrationItemStatus.IN_PROGRESS,
        )

        # 需要用户手动操作的动作直接跳过并记录
        if action.requires_user_action:
            item_result.status = MigrationItemStatus.SKIPPED
            item_result.error_message = "需要用户手动操作"
            self._manual_actions.append(action.description)
            self._results.append(item_result)
            logger.info("跳过手动操作: %s", action.name)
            return

        try:
            rollback_info = await self._dispatch_action(action)
            item_result.status = MigrationItemStatus.SUCCESS
            item_result.rollback_info = rollback_info or ""
            logger.info("动作成功: %s", action.name)
        except Exception as e:
            item_result.status = MigrationItemStatus.FAILED
            item_result.error_message = str(e)
            logger.warning("动作失败: %s — %s", action.name, e)

        item_result.duration_seconds = round(time.time() - start_time, 2)
        self._results.append(item_result)

    async def _dispatch_action(self, action: PlanAction) -> str:
        """根据动作类型分发到具体处理器。

        Returns:
            回滚信息字符串。
        """
        if action.action_type == "app_install":
            return await self._handle_app_install(action)
        elif action.action_type == "config_restore":
            return await self._handle_config_restore(action)
        elif action.action_type == "file_copy":
            return await self._handle_file_copy(action)
        elif action.action_type == "manual_action":
            # 不应该到达这里（上面已处理）
            return ""
        else:
            # 未知类型直接跳过
            logger.warning("未知动作类型: %s, 跳过", action.action_type)
            return ""

    async def _handle_app_install(self, action: PlanAction) -> str:
        """处理应用安装动作。"""
        from easytransfer.executor.installers.winget_installer import WingetInstaller

        if action.method == "winget" and action.command:
            installer = WingetInstaller(dry_run=self.dry_run)
            winget_id = action.details.get("winget_id", "")
            # 从 command 中提取 winget_id
            if not winget_id and "--id" in action.command:
                parts = action.command.split("--id")
                if len(parts) > 1:
                    winget_id = parts[1].strip().split()[0]
            await installer.install(winget_id, action.command)
            return f"winget_uninstall:{winget_id}"
        elif action.method == "skip":
            return ""
        else:
            raise ExecutionError(
                f"不支持的安装方式: {action.method}",
                details=action.name,
            )

    async def _handle_config_restore(self, action: PlanAction) -> str:
        """处理配置恢复动作。"""
        from easytransfer.executor.restorers.config_restorer import ConfigRestorer

        restorer = ConfigRestorer(
            extract_dir=self.extract_dir,
            dry_run=self.dry_run,
        )
        backup_path = await restorer.restore(
            source_path=action.source_path,
            target_path=action.target_path,
        )
        return f"config_backup:{backup_path}" if backup_path else ""

    async def _handle_file_copy(self, action: PlanAction) -> str:
        """处理文件复制动作。"""
        from easytransfer.executor.restorers.file_restorer import FileRestorer

        restorer = FileRestorer(
            extract_dir=self.extract_dir,
            dry_run=self.dry_run,
        )
        backup_path = await restorer.restore(
            source_path=action.source_path,
            target_path=action.target_path,
        )
        return f"file_backup:{backup_path}" if backup_path else ""
