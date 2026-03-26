"""打包/解包往返测试。"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from easytransfer.core.errors import DecryptionError, PackageError
from easytransfer.core.models import (
    AppInfo,
    ConfigInfo,
    DevEnvInfo,
    EnvironmentProfile,
    InstallSource,
    MigrationAnalysis,
    SystemInfo,
)
from easytransfer.packager.packer import pack_migration
from easytransfer.packager.unpacker import unpack_migration, unpack_migration_to_memory


def _make_profile() -> EnvironmentProfile:
    """创建测试用的环境画像。"""
    return EnvironmentProfile(
        profile_id="roundtrip-test",
        system_info=SystemInfo(
            hostname="test-pc",
            os_name="Windows 11",
            os_version="10.0.22631",
            username="testuser",
            user_profile_path="C:\\Users\\testuser",
        ),
        installed_apps=[
            AppInfo(
                name="VS Code",
                version="1.85",
                winget_id="Microsoft.VisualStudioCode",
                can_auto_install=True,
                install_source=InstallSource.WINGET,
                size_bytes=300 * 1024 * 1024,
            ),
            AppInfo(
                name="Chrome",
                version="120",
                winget_id="Google.Chrome",
                can_auto_install=True,
                install_source=InstallSource.EXE,
                size_bytes=200 * 1024 * 1024,
            ),
        ],
        app_configs=[
            ConfigInfo(
                app_name="VS Code",
                config_path="C:\\Users\\testuser\\AppData\\Roaming\\Code\\User\\settings.json",
                config_type="json",
                size_bytes=2048,
            ),
        ],
        total_size_bytes=500 * 1024 * 1024,
    )


def _make_analysis() -> MigrationAnalysis:
    """创建测试用的迁移分析结果。"""
    return MigrationAnalysis(
        profile_id="roundtrip-test",
        total_apps=2,
        auto_installable_apps=2,
        manual_install_apps=0,
        total_data_size_bytes=500 * 1024 * 1024,
        estimated_time_minutes=15,
        app_details=[
            {
                "name": "VS Code",
                "version": "1.85",
                "category": "auto_installable",
                "strategy": "winget_install",
                "winget_id": "Microsoft.VisualStudioCode",
                "notes": "",
                "requires_login": False,
                "estimated_install_minutes": 2.0,
                "config_paths": [],
                "alternatives": [],
            },
            {
                "name": "Chrome",
                "version": "120",
                "category": "auto_installable",
                "strategy": "winget_install",
                "winget_id": "Google.Chrome",
                "notes": "",
                "requires_login": True,
                "estimated_install_minutes": 2.0,
                "config_paths": [],
                "alternatives": [],
            },
        ],
    )


@pytest.fixture
def tmp_dir():
    """临时目录 fixture。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestPackUnpackRoundtrip:
    """打包解包往返测试。"""

    @pytest.mark.asyncio
    async def test_basic_roundtrip(self, tmp_dir):
        """基本往返：打包 -> 解包，验证 manifest 完整。"""
        profile = _make_profile()
        analysis = _make_analysis()
        output_path = str(tmp_dir / "test.etpkg")

        # 打包
        pkg_info = await pack_migration(
            profile=profile,
            analysis=analysis,
            output_path=output_path,
        )

        assert pkg_info.migration_code
        assert len(pkg_info.migration_code) == 6
        assert pkg_info.package_size_bytes > 0
        assert Path(output_path).exists()

        # 解包
        extract_dir = str(tmp_dir / "extracted")
        result = await unpack_migration(
            package_path=output_path,
            migration_code=pkg_info.migration_code,
            extract_dir=extract_dir,
        )

        assert result.manifest is not None
        assert result.manifest["profile_id"] == "roundtrip-test"
        assert result.manifest["contents"]["installed_apps"] == 2
        assert result.install_plan is not None

        # 验证解压目录中有 manifest.json
        assert (result.extract_dir / "manifest.json").exists()
        assert (result.extract_dir / "install_plan.json").exists()
        assert (result.extract_dir / "profile.json").exists()

    @pytest.mark.asyncio
    async def test_wrong_code_fails(self, tmp_dir):
        """使用错误迁移码应解密失败。"""
        profile = _make_profile()
        analysis = _make_analysis()
        output_path = str(tmp_dir / "test.etpkg")

        pkg_info = await pack_migration(
            profile=profile,
            analysis=analysis,
            output_path=output_path,
        )

        # 使用错误迁移码
        wrong_code = "000000" if pkg_info.migration_code != "000000" else "111111"

        with pytest.raises(DecryptionError):
            await unpack_migration(
                package_path=output_path,
                migration_code=wrong_code,
                extract_dir=str(tmp_dir / "bad_extract"),
            )

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, tmp_dir):
        """不存在的文件应抛出 PackageError。"""
        with pytest.raises(PackageError, match="不存在"):
            await unpack_migration(
                package_path=str(tmp_dir / "nonexistent.etpkg"),
                migration_code="123456",
            )

    @pytest.mark.asyncio
    async def test_corrupted_file(self, tmp_dir):
        """损坏的文件应抛出 DecryptionError。"""
        corrupt_path = tmp_dir / "corrupt.etpkg"
        corrupt_path.write_bytes(b"\x00" * 100)

        with pytest.raises(DecryptionError):
            await unpack_migration(
                package_path=str(corrupt_path),
                migration_code="123456",
            )

    @pytest.mark.asyncio
    async def test_package_info_fields(self, tmp_dir):
        """验证 MigrationPackageInfo 各字段。"""
        profile = _make_profile()
        analysis = _make_analysis()
        output_path = str(tmp_dir / "test.etpkg")

        pkg_info = await pack_migration(
            profile=profile,
            analysis=analysis,
            output_path=output_path,
        )

        assert pkg_info.package_id
        assert pkg_info.migration_code.isdigit()
        assert len(pkg_info.migration_code) == 6
        assert pkg_info.package_size_bytes > 0
        assert pkg_info.storage_path == output_path
        assert pkg_info.encryption_info == "AES-256-GCM with PBKDF2 key derivation"
        assert pkg_info.expires_at is not None
        assert pkg_info.item_count > 0

    @pytest.mark.asyncio
    async def test_memory_unpack(self, tmp_dir):
        """内存解包测试。"""
        profile = _make_profile()
        analysis = _make_analysis()
        output_path = str(tmp_dir / "test.etpkg")

        pkg_info = await pack_migration(
            profile=profile,
            analysis=analysis,
            output_path=output_path,
        )

        encrypted_data = Path(output_path).read_bytes()
        manifest, tar_data = await unpack_migration_to_memory(
            encrypted_data=encrypted_data,
            migration_code=pkg_info.migration_code,
        )

        assert manifest["profile_id"] == "roundtrip-test"
        assert len(tar_data) > 0
