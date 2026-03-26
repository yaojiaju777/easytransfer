"""清单文件处理的单元测试。"""

import json

import pytest

from easytransfer.core.errors import ManifestError
from easytransfer.core.models import (
    AppInfo,
    EnvironmentProfile,
    InstallSource,
    MigrationAnalysis,
    SystemInfo,
)
from easytransfer.packager.manifest import (
    generate_manifest,
    parse_manifest,
    serialize_manifest,
)


def _make_profile() -> EnvironmentProfile:
    """创建测试用的环境画像。"""
    return EnvironmentProfile(
        profile_id="test-001",
        system_info=SystemInfo(
            hostname="test-pc",
            os_name="Windows 11",
            os_version="10.0.22631",
            username="testuser",
        ),
        installed_apps=[
            AppInfo(
                name="VS Code",
                version="1.85",
                winget_id="Microsoft.VisualStudioCode",
                can_auto_install=True,
                install_source=InstallSource.WINGET,
            ),
            AppInfo(
                name="Chrome",
                version="120",
                winget_id="Google.Chrome",
                can_auto_install=True,
                install_source=InstallSource.EXE,
            ),
        ],
        total_size_bytes=1024 * 1024 * 100,
    )


class TestGenerateManifest:
    """清单生成测试。"""

    def test_basic_manifest(self):
        profile = _make_profile()
        manifest = generate_manifest(profile)

        assert manifest["manifest_version"] == "1.0"
        assert manifest["profile_id"] == "test-001"
        assert manifest["source_system"]["hostname"] == "test-pc"
        assert manifest["contents"]["installed_apps"] == 2
        assert len(manifest["apps"]) == 2

    def test_options_reflected(self):
        profile = _make_profile()
        manifest = generate_manifest(
            profile,
            include_files=False,
            include_browser=False,
        )

        assert manifest["options"]["include_files"] is False
        assert manifest["options"]["include_browser"] is False

    def test_with_analysis(self):
        profile = _make_profile()
        analysis = MigrationAnalysis(
            profile_id="test-001",
            total_apps=2,
            auto_installable_apps=2,
            manual_install_apps=0,
        )
        manifest = generate_manifest(profile, analysis=analysis)

        assert "analysis_summary" in manifest
        assert manifest["analysis_summary"]["auto_installable_apps"] == 2


class TestSerializeManifest:
    """清单序列化测试。"""

    def test_serialize_deserialize(self):
        profile = _make_profile()
        manifest = generate_manifest(profile)

        data = serialize_manifest(manifest)
        assert isinstance(data, bytes)

        parsed = json.loads(data.decode("utf-8"))
        assert parsed["profile_id"] == "test-001"


class TestParseManifest:
    """清单解析测试。"""

    def test_valid_manifest(self):
        manifest_data = {
            "manifest_version": "1.0",
            "package_id": "abc123",
            "contents": {"installed_apps": 5},
        }
        data = json.dumps(manifest_data).encode("utf-8")
        result = parse_manifest(data)
        assert result["package_id"] == "abc123"

    def test_invalid_json(self):
        with pytest.raises(ManifestError, match="解析失败"):
            parse_manifest(b"not valid json {{{")

    def test_missing_required_field(self):
        manifest_data = {"manifest_version": "1.0"}
        data = json.dumps(manifest_data).encode("utf-8")
        with pytest.raises(ManifestError, match="缺少必需字段"):
            parse_manifest(data)

    def test_non_object_top_level(self):
        data = json.dumps([1, 2, 3]).encode("utf-8")
        with pytest.raises(ManifestError, match="顶层必须是对象"):
            parse_manifest(data)
