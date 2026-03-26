"""core/errors.py 的单元测试。"""

import pytest

from easytransfer.core.errors import (
    ChecksumError,
    DecryptionError,
    DownloadError,
    EasyTransferError,
    EncryptionError,
    ExecutionError,
    InstallError,
    InvalidMigrationCodeError,
    InvalidProfileError,
    MCPError,
    ManifestError,
    PackageError,
    PlanningError,
    RegistryAccessError,
    RestoreError,
    RollbackError,
    ScanError,
    ScannerNotFoundError,
    SecurityError,
    ToolExecutionError,
    TransferError,
    UploadError,
)


class TestExceptionHierarchy:
    """验证异常继承关系。"""

    def test_all_inherit_from_base(self):
        """所有自定义异常都继承自 EasyTransferError。"""
        all_exceptions = [
            ScanError,
            RegistryAccessError,
            ScannerNotFoundError,
            PlanningError,
            InvalidProfileError,
            PackageError,
            ManifestError,
            TransferError,
            UploadError,
            DownloadError,
            ChecksumError,
            ExecutionError,
            InstallError,
            RestoreError,
            RollbackError,
            SecurityError,
            EncryptionError,
            DecryptionError,
            InvalidMigrationCodeError,
            MCPError,
            ToolExecutionError,
        ]
        for exc_class in all_exceptions:
            assert issubclass(exc_class, EasyTransferError)

    def test_scan_errors_hierarchy(self):
        assert issubclass(RegistryAccessError, ScanError)
        assert issubclass(ScannerNotFoundError, ScanError)

    def test_transfer_errors_hierarchy(self):
        assert issubclass(UploadError, TransferError)
        assert issubclass(DownloadError, TransferError)
        assert issubclass(ChecksumError, TransferError)

    def test_security_errors_hierarchy(self):
        assert issubclass(EncryptionError, SecurityError)
        assert issubclass(DecryptionError, SecurityError)
        assert issubclass(InvalidMigrationCodeError, SecurityError)


class TestExceptionMessages:
    """测试异常消息格式。"""

    def test_message_only(self):
        err = EasyTransferError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.message == "something went wrong"

    def test_message_with_details(self):
        err = EasyTransferError("扫描失败", details="注册表键不存在")
        assert str(err) == "扫描失败 (注册表键不存在)"

    def test_catch_as_base_class(self):
        """可以用基类捕获所有子类异常。"""
        with pytest.raises(EasyTransferError):
            raise InstallError("Chrome 安装失败")

    def test_catch_as_specific_class(self):
        with pytest.raises(InstallError):
            raise InstallError("Chrome 安装失败")
