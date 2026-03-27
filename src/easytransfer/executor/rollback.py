"""迁移回滚器。

根据 MigrationResult 中记录的回滚信息，
撤销已完成的迁移操作。

支持的回滚类型：
- winget_uninstall:<winget_id> — 卸载通过 winget 安装的应用
- config_backup:<path> — 恢复配置文件的备份
- file_backup:<path> — 恢复用户文件的备份
"""

from __future__ import annotations

import shutil
from pathlib import Path

from easytransfer.core.errors import RollbackError
from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    MigrationItemResult,
    MigrationItemStatus,
    MigrationResult,
    RollbackResult,
)

logger = get_logger(__name__)


class RollbackExecutor:
    """迁移回滚执行器。"""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    async def rollback(
        self,
        migration_result: MigrationResult,
        item_ids: list[str] | None = None,
    ) -> RollbackResult:
        """回滚迁移操作。

        Args:
            migration_result: 迁移执行结果。
            item_ids: 要回滚的项目 ID 列表。None 表示回滚全部。

        Returns:
            回滚结果。
        """
        result = RollbackResult(
            migration_id=migration_result.migration_id,
        )

        items_to_rollback = self._select_items(migration_result, item_ids)

        logger.info("开始回滚: %d 个项目", len(items_to_rollback))

        details: list[dict] = []
        for item in items_to_rollback:
            detail = await self._rollback_item(item)
            details.append(detail)
            if detail["status"] == "success":
                result.rolled_back_items += 1
            else:
                result.failed_rollbacks += 1

        result.details = details

        logger.info(
            "回滚完成: 成功=%d, 失败=%d",
            result.rolled_back_items,
            result.failed_rollbacks,
        )

        return result

    def _select_items(
        self,
        migration_result: MigrationResult,
        item_ids: list[str] | None,
    ) -> list[MigrationItemResult]:
        """选择需要回滚的项目。"""
        candidates = [
            item
            for item in migration_result.items
            if item.status == MigrationItemStatus.SUCCESS and item.rollback_info
        ]

        if item_ids is not None:
            id_set = set(item_ids)
            candidates = [item for item in candidates if item.item_id in id_set]

        # 反转顺序：后执行的先回滚
        return list(reversed(candidates))

    async def _rollback_item(self, item: MigrationItemResult) -> dict:
        """回滚单个迁移项目。"""
        detail = {
            "item_id": item.item_id,
            "item_name": item.item_name,
            "item_type": item.item_type,
            "status": "success",
            "note": "",
        }

        if not item.rollback_info:
            detail["status"] = "skipped"
            detail["note"] = "没有回滚信息"
            return detail

        try:
            prefix, _, value = item.rollback_info.partition(":")
            if prefix == "winget_uninstall":
                await self._rollback_winget(value, detail)
            elif prefix in ("config_backup", "file_backup"):
                await self._rollback_file(value, detail)
            else:
                detail["status"] = "skipped"
                detail["note"] = f"未知回滚类型: {prefix}"
        except Exception as e:
            detail["status"] = "failed"
            detail["note"] = str(e)
            logger.warning("回滚失败: %s — %s", item.item_name, e)

        return detail

    async def _rollback_winget(self, winget_id: str, detail: dict) -> None:
        """回滚 winget 安装（卸载应用）。"""
        if not winget_id:
            detail["status"] = "skipped"
            detail["note"] = "winget_id 为空"
            return

        logger.info("回滚: 卸载 %s", winget_id)

        if self.dry_run:
            detail["note"] = f"[dry-run] 将卸载 {winget_id}"
            return

        from easytransfer.executor.installers.winget_installer import WingetInstaller

        installer = WingetInstaller()
        try:
            await installer.uninstall(winget_id)
            detail["note"] = f"已卸载 {winget_id}"
        except Exception as e:
            raise RollbackError(
                f"卸载失败: {winget_id}",
                details=str(e),
            ) from e

    async def _rollback_file(self, backup_path: str, detail: dict) -> None:
        """回滚文件恢复（从备份恢复）。"""
        if not backup_path:
            detail["status"] = "skipped"
            detail["note"] = "备份路径为空"
            return

        backup = Path(backup_path)
        if not backup.exists():
            detail["status"] = "failed"
            detail["note"] = f"备份文件不存在: {backup_path}"
            return

        # 从备份路径推断目标路径: target_path.bak.XXXX -> target_path
        target_path = backup_path.rsplit(".bak.", 1)[0]
        target = Path(target_path)

        logger.info("回滚: 从备份恢复 %s", target)

        if self.dry_run:
            detail["note"] = f"[dry-run] 将从备份恢复 {target}"
            return

        try:
            # 删除当前文件，恢复备份
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(str(target))
                else:
                    target.unlink()

            if backup.is_dir():
                shutil.copytree(str(backup), str(target))
            else:
                shutil.copy2(str(backup), str(target))

            # 清理备份文件
            if backup.is_dir():
                shutil.rmtree(str(backup))
            else:
                backup.unlink()

            detail["note"] = f"已从备份恢复: {target}"

        except OSError as e:
            raise RollbackError(
                f"文件回滚失败: {target}",
                details=str(e),
            ) from e
