"""planner/analyzer.py 的单元测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from easytransfer.core.errors import InvalidProfileError
from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    CredentialInfo,
    DevEnvInfo,
    EnvironmentProfile,
    FileGroup,
    InstallSource,
    MigrationAnalysis,
    SystemInfo,
)
from easytransfer.planner.analyzer import analyze_from_file, analyze_profile


@pytest.fixture
def rich_profile() -> EnvironmentProfile:
    """包含多种数据的丰富环境画像。"""
    return EnvironmentProfile(
        profile_id="test-rich",
        system_info=SystemInfo(
            hostname="DEV-PC",
            os_name="Windows 11 Pro",
            disk_free_gb=200.0,
        ),
        installed_apps=[
            AppInfo(
                name="Google Chrome",
                version="122.0",
                publisher="Google LLC",
                install_source=InstallSource.WINGET,
                winget_id="Google.Chrome",
                can_auto_install=True,
                size_bytes=500_000_000,
            ),
            AppInfo(
                name="Visual Studio Code",
                version="1.87.0",
                publisher="Microsoft",
                install_source=InstallSource.WINGET,
                winget_id="Microsoft.VisualStudioCode",
                can_auto_install=True,
                size_bytes=350_000_000,
            ),
            AppInfo(
                name="Adobe Photoshop",
                version="25.0",
                publisher="Adobe",
                install_source=InstallSource.EXE,
                can_auto_install=False,
                size_bytes=2_000_000_000,
            ),
            AppInfo(
                name="7-Zip",
                version="24.01",
                publisher="Igor Pavlov",
                install_source=InstallSource.WINGET,
                winget_id="7zip.7zip",
                can_auto_install=True,
                size_bytes=5_000_000,
            ),
            AppInfo(
                name="Some Weird Tool",
                version="1.0",
                publisher="Unknown",
                install_source=InstallSource.UNKNOWN,
                can_auto_install=False,
                size_bytes=10_000_000,
            ),
        ],
        user_files=[
            FileGroup(
                group_name="Documents",
                source_path="C:\\Users\\dev\\Documents",
                file_count=500,
                total_size_bytes=5_000_000_000,
            ),
        ],
        browser_profiles=[
            BrowserProfile(
                browser_name="Chrome",
                profile_path="C:\\Users\\dev\\AppData\\Local\\Google\\Chrome",
                bookmarks_count=300,
                extensions=["uBlock Origin"],
                has_saved_passwords=True,
                data_size_bytes=400_000_000,
            ),
        ],
        dev_environments=[
            DevEnvInfo(
                name="Python",
                version="3.11.8",
                install_path="C:\\Python311",
                global_packages=["pip", "poetry"],
            ),
        ],
        credentials=[
            CredentialInfo(
                credential_type="ssh_key",
                name="id_rsa",
                path="C:\\Users\\dev\\.ssh\\id_rsa",
            ),
        ],
        total_size_bytes=8_265_000_000,
    )


@pytest.fixture
def minimal_profile() -> EnvironmentProfile:
    """最小环境画像（无应用）。"""
    return EnvironmentProfile(
        profile_id="test-minimal",
        system_info=SystemInfo(hostname="EMPTY-PC"),
    )


class TestAnalyzeProfile:
    """analyze_profile 测试。"""

    @pytest.mark.asyncio
    async def test_basic_analysis(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        assert isinstance(analysis, MigrationAnalysis)
        assert analysis.profile_id == "test-rich"
        assert analysis.total_apps == 5

    @pytest.mark.asyncio
    async def test_auto_installable_count(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        # Chrome, VS Code, 7-Zip are auto (known winget)
        # Photoshop is manual (known, MANUAL_DOWNLOAD)
        # Some Weird Tool is not_available
        assert analysis.auto_installable_apps >= 3

    @pytest.mark.asyncio
    async def test_manual_install_count(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        # Adobe Photoshop should be manual
        assert analysis.manual_install_apps >= 1

    @pytest.mark.asyncio
    async def test_estimated_time_positive(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        assert analysis.estimated_time_minutes > 0

    @pytest.mark.asyncio
    async def test_has_recommendations(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        assert len(analysis.recommendations) > 0

    @pytest.mark.asyncio
    async def test_has_warnings(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        # Should warn about unknown apps and credentials
        assert len(analysis.warnings) > 0

    @pytest.mark.asyncio
    async def test_app_details_populated(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        assert len(analysis.app_details) == 5
        for detail in analysis.app_details:
            assert "name" in detail
            assert "category" in detail
            assert detail["category"] in ("auto_installable", "manual_install", "not_available")

    @pytest.mark.asyncio
    async def test_data_size_preserved(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        assert analysis.total_data_size_bytes == rich_profile.total_size_bytes

    @pytest.mark.asyncio
    async def test_empty_profile(self, minimal_profile):
        analysis = await analyze_profile(minimal_profile)
        assert analysis.total_apps == 0
        assert analysis.auto_installable_apps == 0
        assert analysis.manual_install_apps == 0
        assert analysis.estimated_time_minutes >= 5  # 最小值

    @pytest.mark.asyncio
    async def test_ssh_key_recommendation(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        ssh_recs = [r for r in analysis.recommendations if "SSH" in r]
        assert len(ssh_recs) > 0

    @pytest.mark.asyncio
    async def test_browser_password_recommendation(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        pw_recs = [r for r in analysis.recommendations if "密码" in r]
        assert len(pw_recs) > 0

    @pytest.mark.asyncio
    async def test_credential_warning(self, rich_profile):
        analysis = await analyze_profile(rich_profile)
        cred_warns = [w for w in analysis.warnings if "凭证" in w or "密钥" in w]
        assert len(cred_warns) > 0


class TestAnalyzeFromFile:
    """analyze_from_file 测试。"""

    @pytest.mark.asyncio
    async def test_load_and_analyze(self, sample_profile_path):
        """从 JSON 文件加载并分析。"""
        analysis = await analyze_from_file(str(sample_profile_path))
        assert isinstance(analysis, MigrationAnalysis)
        assert analysis.total_apps > 0

    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        with pytest.raises(InvalidProfileError, match="不存在"):
            await analyze_from_file("C:\\nonexistent\\profile.json")

    @pytest.mark.asyncio
    async def test_invalid_json(self, tmp_dir):
        bad_file = tmp_dir / "bad.json"
        bad_file.write_text("not json at all", encoding="utf-8")
        with pytest.raises(InvalidProfileError, match="格式无效"):
            await analyze_from_file(str(bad_file))

    @pytest.mark.asyncio
    async def test_empty_json_object(self, tmp_dir):
        """空 JSON 对象应该能处理（返回空分析）。"""
        empty_file = tmp_dir / "empty.json"
        empty_file.write_text("{}", encoding="utf-8")
        analysis = await analyze_from_file(str(empty_file))
        assert analysis.total_apps == 0
