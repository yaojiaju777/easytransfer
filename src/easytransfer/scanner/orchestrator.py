"""扫描编排器。

将各个扫描器的结果汇总为一个完整的 EnvironmentProfile。
是 MCP 工具和 CLI 调用扫描功能的统一入口。
"""

from __future__ import annotations

import json
import platform
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    ConfigInfo,
    CredentialInfo,
    DevEnvInfo,
    EnvironmentProfile,
    FileGroup,
    InstallSource,
    ScanScope,
    SystemInfo,
)
from easytransfer.scanner.registry import create_default_registry

logger = get_logger(__name__)


async def run_full_scan(
    scope: ScanScope = ScanScope.FULL,
    skip_system_apps: bool = True,
    include_file_sizes: bool = True,
) -> EnvironmentProfile:
    """执行完整的环境扫描。

    这是扫描功能的统一入口，MCP 工具和 CLI 都调用此函数。

    Args:
        scope: 扫描范围。
        skip_system_apps: 是否跳过系统应用。
        include_file_sizes: 是否统计文件大小。

    Returns:
        完整的环境画像。
    """
    logger.info("开始环境扫描, scope=%s", scope.value)

    # 1. 收集系统信息
    system_info = _collect_system_info()

    # 2. 运行所有扫描器
    registry = create_default_registry()
    results = await registry.run_all(scope=scope)

    # 3. 汇总结果到 EnvironmentProfile
    profile = EnvironmentProfile(
        scan_time=datetime.now(),
        system_info=system_info,
    )

    for result in results:
        if not result.success:
            logger.warning("扫描器 %s 失败: %s", result.scanner_name, result.error_message)
            continue

        data = result.data

        if result.scanner_name == "installed_apps" and "apps" in data:
            profile.installed_apps = [_dict_to_app_info(a) for a in data["apps"]]

        elif result.scanner_name == "app_configs" and "configs" in data:
            profile.app_configs = [ConfigInfo(**c) for c in data["configs"]]

        elif result.scanner_name == "user_files" and "file_groups" in data:
            profile.user_files = [FileGroup(**g) for g in data["file_groups"]]

        elif result.scanner_name == "browser_data" and "browser_profiles" in data:
            profile.browser_profiles = [BrowserProfile(**p) for p in data["browser_profiles"]]

        elif result.scanner_name == "dev_environment" and "dev_environments" in data:
            profile.dev_environments = [DevEnvInfo(**e) for e in data["dev_environments"]]

        elif result.scanner_name == "git_ssh":
            if "ssh_keys" in data:
                profile.credentials = [CredentialInfo(**k) for k in data["ssh_keys"]]
            if "git_configs" in data:
                for g in data["git_configs"]:
                    profile.dev_environments.append(DevEnvInfo(**g))

    # 4. 计算总大小
    profile.total_size_bytes = sum(
        fg.total_size_bytes for fg in profile.user_files
    ) + sum(
        bp.data_size_bytes for bp in profile.browser_profiles
    ) + sum(
        app.size_bytes for app in profile.installed_apps
    )

    logger.info(
        "扫描完成: %d 个应用, %d 个文件组, %d 个浏览器, %d 个开发环境, 总计 %.1fGB",
        len(profile.installed_apps),
        len(profile.user_files),
        len(profile.browser_profiles),
        len(profile.dev_environments),
        profile.total_size_bytes / (1024**3),
    )

    return profile


def save_profile(profile: EnvironmentProfile, output_path: Path) -> None:
    """将环境画像保存为 JSON 文件。"""
    data = asdict(profile)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("环境画像已保存: %s", output_path)


def _collect_system_info() -> SystemInfo:
    """收集当前系统信息。"""
    import os

    disk = shutil.disk_usage(Path.home())

    return SystemInfo(
        hostname=platform.node(),
        os_name=f"{platform.system()} {platform.release()}",
        os_version=platform.version(),
        os_build=platform.win32_ver()[1] if hasattr(platform, "win32_ver") else "",
        architecture=platform.machine(),
        cpu=platform.processor(),
        total_memory_gb=_get_memory_gb(),
        disk_total_gb=round(disk.total / (1024**3), 1),
        disk_free_gb=round(disk.free / (1024**3), 1),
        username=os.getlogin(),
        user_profile_path=str(Path.home()),
    )


def _get_memory_gb() -> float:
    """获取系统内存大小。"""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        mem_status = ctypes.c_ulonglong()
        kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_status))
        return round(mem_status.value / (1024 * 1024), 1)
    except Exception:
        return 0.0


def _dict_to_app_info(d: dict) -> AppInfo:
    """将字典转为 AppInfo，处理枚举类型。"""
    if "install_source" in d and isinstance(d["install_source"], str):
        try:
            d["install_source"] = InstallSource(d["install_source"])
        except ValueError:
            d["install_source"] = InstallSource.UNKNOWN
    # 移除 AppInfo 不接受的字段
    valid_fields = {f.name for f in AppInfo.__dataclass_fields__.values()}
    filtered = {k: v for k, v in d.items() if k in valid_fields}
    return AppInfo(**filtered)
