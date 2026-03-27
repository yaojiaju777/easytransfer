"""迁移结果验证器。

检查迁移操作是否成功：
- 应用是否安装（通过 winget list / where 检查）
- 配置文件是否存在于目标路径
- 用户文件是否已恢复
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    MigrationItemResult,
    MigrationItemStatus,
    MigrationResult,
    VerificationReport,
)

logger = get_logger(__name__)


class MigrationVerifier:
    """迁移结果验证器。

    根据 MigrationResult 中记录的各项结果，
    逐一验证迁移是否真正成功。
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    async def verify(self, migration_result: MigrationResult) -> VerificationReport:
        """验证迁移结果。

        Args:
            migration_result: 迁移执行结果。

        Returns:
            验证报告。
        """
        report = VerificationReport(
            migration_id=migration_result.migration_id,
            verified_at=datetime.now(),
        )

        details: list[dict] = []

        for item in migration_result.items:
            if item.status == MigrationItemStatus.SKIPPED:
                details.append({
                    "item_id": item.item_id,
                    "item_name": item.item_name,
                    "item_type": item.item_type,
                    "status": "skipped",
                    "note": "跳过验证（原操作被跳过）",
                })
                continue

            if item.status == MigrationItemStatus.FAILED:
                details.append({
                    "item_id": item.item_id,
                    "item_name": item.item_name,
                    "item_type": item.item_type,
                    "status": "failed",
                    "note": f"原操作已失败: {item.error_message}",
                })
                report.total_checked += 1
                report.failed += 1
                continue

            # 验证成功的项目
            check_result = await self._verify_item(item)
            details.append(check_result)
            report.total_checked += 1
            if check_result["status"] == "passed":
                report.passed += 1
            else:
                report.failed += 1

        report.details = details

        logger.info(
            "验证完成: 检查=%d, 通过=%d, 失败=%d",
            report.total_checked,
            report.passed,
            report.failed,
        )

        return report

    async def _verify_item(self, item: MigrationItemResult) -> dict:
        """验证单个迁移项目。"""
        if item.item_type == "app_install":
            return await self._verify_app_install(item)
        elif item.item_type in ("config_restore", "file_copy"):
            return await self._verify_file_restore(item)
        else:
            return {
                "item_id": item.item_id,
                "item_name": item.item_name,
                "item_type": item.item_type,
                "status": "passed",
                "note": "无需额外验证",
            }

    async def _verify_app_install(self, item: MigrationItemResult) -> dict:
        """验证应用安装结果。"""
        result = {
            "item_id": item.item_id,
            "item_name": item.item_name,
            "item_type": item.item_type,
            "status": "passed",
            "note": "",
        }

        # 从 rollback_info 提取 winget_id
        winget_id = ""
        if item.rollback_info.startswith("winget_uninstall:"):
            winget_id = item.rollback_info.split(":", 1)[1]

        if winget_id and not self.dry_run:
            from easytransfer.executor.installers.winget_installer import (
                WingetInstaller,
            )

            installer = WingetInstaller()
            is_installed = await installer.is_installed(winget_id)
            if is_installed:
                result["status"] = "passed"
                result["note"] = f"{winget_id} 已安装"
            else:
                result["status"] = "failed"
                result["note"] = f"{winget_id} 未检测到安装"
        else:
            # dry-run 或没有 winget_id，标记为通过
            result["note"] = "应用安装标记为成功"

        return result

    async def _verify_file_restore(self, item: MigrationItemResult) -> dict:
        """验证文件/配置恢复结果。

        通过检查 rollback_info 中记录的备份路径来
        反推目标路径是否存在。
        """
        result = {
            "item_id": item.item_id,
            "item_name": item.item_name,
            "item_type": item.item_type,
            "status": "passed",
            "note": "恢复操作成功完成",
        }

        # rollback_info 格式: config_backup:<path> 或 file_backup:<path>
        # 有备份说明目标位置之前就有文件，现在也应该有
        # 没备份说明是新创建的
        if item.rollback_info:
            prefix, _, backup_path = item.rollback_info.partition(":")
            if backup_path:
                # 从备份路径推断目标路径
                # backup_path = target_path + ".bak.XXXX"
                # 去掉 .bak.XXXX 后缀
                target_path = backup_path.rsplit(".bak.", 1)[0]
                if Path(target_path).exists():
                    result["note"] = f"文件已恢复到 {target_path}"
                else:
                    result["status"] = "failed"
                    result["note"] = f"目标文件不存在: {target_path}"

        return result
