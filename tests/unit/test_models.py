"""core/models.py 的单元测试。"""

from datetime import datetime

from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    ConfigInfo,
    CredentialInfo,
    DevEnvInfo,
    EnvironmentProfile,
    FileGroup,
    InstallSource,
    MigrationAnalysis,
    MigrationItemResult,
    MigrationItemStatus,
    MigrationPackageInfo,
    MigrationResult,
    MigrationStatus,
    Priority,
    RollbackResult,
    ScanResult,
    ScanScope,
    StorageMode,
    SystemInfo,
    VerificationReport,
)


class TestEnums:
    """枚举类型测试。"""

    def test_scan_scope_values(self):
        assert ScanScope.FULL == "full"
        assert ScanScope.APPS_ONLY == "apps_only"
        assert ScanScope.FILES_ONLY == "files_only"
        assert ScanScope.DEV_ONLY == "dev_only"

    def test_install_source_values(self):
        assert InstallSource.WINGET == "winget"
        assert InstallSource.UNKNOWN == "unknown"

    def test_migration_status_flow(self):
        """验证状态机包含所有预期状态。"""
        expected = {
            "idle", "scanning", "analyzed", "packaging", "packaged",
            "downloading", "restoring", "verifying", "completed",
            "partially_completed", "failed",
        }
        actual = {s.value for s in MigrationStatus}
        assert actual == expected

    def test_priority_ordering(self):
        assert Priority.P0 < Priority.P1 < Priority.P2


class TestSystemInfo:
    """SystemInfo 数据模型测试。"""

    def test_default_values(self):
        info = SystemInfo()
        assert info.hostname == ""
        assert info.total_memory_gb == 0.0

    def test_with_values(self, sample_system_info):
        assert sample_system_info.hostname == "TEST-PC"
        assert sample_system_info.os_name == "Windows 11 Pro"
        assert sample_system_info.total_memory_gb == 16.0


class TestAppInfo:
    """AppInfo 数据模型测试。"""

    def test_default_app(self):
        app = AppInfo()
        assert app.name == ""
        assert app.install_source == InstallSource.UNKNOWN
        assert app.can_auto_install is False
        assert app.config_paths == []
        assert app.data_paths == []

    def test_winget_app(self):
        app = AppInfo(
            name="Git",
            winget_id="Git.Git",
            install_source=InstallSource.WINGET,
            can_auto_install=True,
        )
        assert app.winget_id == "Git.Git"
        assert app.can_auto_install is True

    def test_config_paths_are_independent(self):
        """确保不同实例的 config_paths 列表不共享。"""
        app1 = AppInfo()
        app2 = AppInfo()
        app1.config_paths.append("/some/path")
        assert len(app2.config_paths) == 0


class TestEnvironmentProfile:
    """EnvironmentProfile 数据模型测试。"""

    def test_default_profile_has_id(self):
        profile = EnvironmentProfile()
        assert profile.profile_id != ""
        assert len(profile.profile_id) == 8

    def test_default_profile_has_scan_time(self):
        profile = EnvironmentProfile()
        assert isinstance(profile.scan_time, datetime)

    def test_sample_profile(self, sample_profile):
        assert sample_profile.profile_id == "test-001"
        assert len(sample_profile.installed_apps) == 3
        assert len(sample_profile.browser_profiles) == 1
        assert len(sample_profile.dev_environments) == 2
        assert sample_profile.total_size_bytes == 3_200_000_000

    def test_lists_are_independent(self):
        """确保不同实例的列表不共享。"""
        p1 = EnvironmentProfile()
        p2 = EnvironmentProfile()
        p1.installed_apps.append(AppInfo(name="Test"))
        assert len(p2.installed_apps) == 0


class TestMigrationPackageInfo:
    """MigrationPackageInfo 测试。"""

    def test_default_encryption_info(self):
        pkg = MigrationPackageInfo()
        assert "AES-256-GCM" in pkg.encryption_info

    def test_default_storage_mode(self):
        pkg = MigrationPackageInfo()
        assert pkg.storage_mode == StorageMode.LOCAL


class TestMigrationResult:
    """MigrationResult 测试。"""

    def test_default_status_is_idle(self):
        result = MigrationResult()
        assert result.status == MigrationStatus.IDLE

    def test_counts_default_to_zero(self):
        result = MigrationResult()
        assert result.total_items == 0
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.skipped_count == 0


class TestScanResult:
    """ScanResult 测试。"""

    def test_default_success(self):
        result = ScanResult()
        assert result.success is True
        assert result.error_message == ""

    def test_failed_scan(self):
        result = ScanResult(success=False, error_message="注册表访问被拒绝")
        assert result.success is False
        assert "注册表" in result.error_message
