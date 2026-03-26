"""pytest 共享 fixtures。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from easytransfer.core.config import AppConfig, load_config
from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    CredentialInfo,
    DevEnvInfo,
    EnvironmentProfile,
    FileGroup,
    InstallSource,
    SystemInfo,
)


@pytest.fixture
def app_config() -> AppConfig:
    """返回默认配置。"""
    return AppConfig()


@pytest.fixture
def sample_system_info() -> SystemInfo:
    """样例系统信息。"""
    return SystemInfo(
        hostname="TEST-PC",
        os_name="Windows 11 Pro",
        os_version="10.0.22631",
        os_build="22631",
        architecture="AMD64",
        cpu="Intel Core i7-12700",
        total_memory_gb=16.0,
        disk_total_gb=512.0,
        disk_free_gb=200.0,
        username="testuser",
        user_profile_path="C:\\Users\\testuser",
    )


@pytest.fixture
def sample_apps() -> list[AppInfo]:
    """样例应用列表。"""
    return [
        AppInfo(
            name="Google Chrome",
            version="122.0.6261.112",
            publisher="Google LLC",
            install_path="C:\\Program Files\\Google\\Chrome",
            install_source=InstallSource.WINGET,
            winget_id="Google.Chrome",
            can_auto_install=True,
            install_command="winget install --id Google.Chrome",
            size_bytes=500_000_000,
        ),
        AppInfo(
            name="Visual Studio Code",
            version="1.87.0",
            publisher="Microsoft Corporation",
            install_path="C:\\Users\\testuser\\AppData\\Local\\Programs\\Microsoft VS Code",
            install_source=InstallSource.WINGET,
            winget_id="Microsoft.VisualStudioCode",
            config_paths=["C:\\Users\\testuser\\AppData\\Roaming\\Code\\User\\settings.json"],
            can_auto_install=True,
            install_command="winget install --id Microsoft.VisualStudioCode",
            size_bytes=350_000_000,
        ),
        AppInfo(
            name="Some Old App",
            version="1.0",
            publisher="Unknown",
            install_path="C:\\Program Files\\OldApp",
            install_source=InstallSource.UNKNOWN,
            can_auto_install=False,
            notes="此应用已停止更新",
            size_bytes=50_000_000,
        ),
    ]


@pytest.fixture
def sample_profile(sample_system_info, sample_apps) -> EnvironmentProfile:
    """样例环境画像。"""
    return EnvironmentProfile(
        profile_id="test-001",
        system_info=sample_system_info,
        installed_apps=sample_apps,
        user_files=[
            FileGroup(
                group_name="Documents",
                source_path="C:\\Users\\testuser\\Documents",
                file_count=150,
                total_size_bytes=2_000_000_000,
                file_extensions=[".docx", ".pdf", ".xlsx"],
            ),
        ],
        browser_profiles=[
            BrowserProfile(
                browser_name="Chrome",
                profile_path="C:\\Users\\testuser\\AppData\\Local\\Google\\Chrome",
                bookmarks_count=234,
                extensions=["uBlock Origin", "Bitwarden"],
                has_saved_passwords=True,
                data_size_bytes=350_000_000,
            ),
        ],
        dev_environments=[
            DevEnvInfo(
                name="Python",
                version="3.11.8",
                install_path="C:\\Python311",
                global_packages=["pip", "poetry", "black", "ruff"],
                config_files=["C:\\Users\\testuser\\pip\\pip.ini"],
            ),
            DevEnvInfo(
                name="Node.js",
                version="20.11.0",
                install_path="C:\\Program Files\\nodejs",
                global_packages=["npm", "yarn", "pnpm"],
            ),
        ],
        credentials=[
            CredentialInfo(
                credential_type="ssh_key",
                name="id_rsa",
                path="C:\\Users\\testuser\\.ssh\\id_rsa",
            ),
        ],
        total_size_bytes=3_200_000_000,
    )


@pytest.fixture
def tmp_dir():
    """临时目录，用于测试文件操作。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_profile_path(sample_profile, tmp_dir) -> Path:
    """将样例 profile 写入临时 JSON 文件并返回路径。"""
    from dataclasses import asdict

    path = tmp_dir / "profile.json"
    data = asdict(sample_profile)
    # datetime 需要转为字符串
    path.write_text(json.dumps(data, default=str, ensure_ascii=False), encoding="utf-8")
    return path
