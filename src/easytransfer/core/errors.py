"""EasyTransfer 自定义异常体系。

所有异常继承自 EasyTransferError，方便统一捕获和处理。
每个业务模块有自己的异常子类。
"""


class EasyTransferError(Exception):
    """EasyTransfer 所有异常的基类。"""

    def __init__(self, message: str = "", details: str = ""):
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


# ============================================================
# 扫描模块异常
# ============================================================


class ScanError(EasyTransferError):
    """扫描过程中的通用错误。"""


class RegistryAccessError(ScanError):
    """Windows 注册表访问失败。"""


class ScannerNotFoundError(ScanError):
    """指定的扫描器不存在。"""


# ============================================================
# 分析/规划模块异常
# ============================================================


class PlanningError(EasyTransferError):
    """迁移规划过程中的错误。"""


class InvalidProfileError(PlanningError):
    """环境画像数据无效或损坏。"""


# ============================================================
# 打包模块异常
# ============================================================


class PackageError(EasyTransferError):
    """打包过程中的错误。"""


class InsufficientSpaceError(PackageError):
    """磁盘空间不足。"""


class ManifestError(PackageError):
    """清单文件处理错误。"""


# ============================================================
# 传输模块异常
# ============================================================


class TransferError(EasyTransferError):
    """数据传输过程中的错误。"""


class UploadError(TransferError):
    """上传失败。"""


class DownloadError(TransferError):
    """下载失败。"""


class ChecksumError(TransferError):
    """文件校验和不匹配。"""


# ============================================================
# 执行/恢复模块异常
# ============================================================


class ExecutionError(EasyTransferError):
    """恢复执行过程中的错误。"""


class InstallError(ExecutionError):
    """应用安装失败。"""


class RestoreError(ExecutionError):
    """配置/文件恢复失败。"""


class RollbackError(ExecutionError):
    """回滚操作失败。"""


# ============================================================
# 安全模块异常
# ============================================================


class SecurityError(EasyTransferError):
    """安全相关的错误。"""


class EncryptionError(SecurityError):
    """加密失败。"""


class DecryptionError(SecurityError):
    """解密失败（通常是密码错误）。"""


class InvalidMigrationCodeError(SecurityError):
    """迁移码无效。"""


# ============================================================
# MCP 模块异常
# ============================================================


class MCPError(EasyTransferError):
    """MCP Server 相关错误。"""


class ToolExecutionError(MCPError):
    """MCP 工具执行失败。"""
