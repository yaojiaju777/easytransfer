"""恢复执行引擎模块。

包含迁移恢复的核心逻辑：
- engine: 主执行引擎（编排器）
- installers: 应用安装器（winget 等）
- restorers: 配置/文件恢复器
- verifier: 迁移结果验证器
- rollback: 回滚支持
"""

from easytransfer.executor.engine import MigrationExecutor
from easytransfer.executor.rollback import RollbackExecutor
from easytransfer.executor.verifier import MigrationVerifier

__all__ = [
    "MigrationExecutor",
    "MigrationVerifier",
    "RollbackExecutor",
]
