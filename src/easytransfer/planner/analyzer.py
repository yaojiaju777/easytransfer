"""迁移分析器。

分析 EnvironmentProfile，匹配应用知识库，生成 MigrationAnalysis。
这是 MCP 工具 analyze_migration 和 CLI analyze 命令的核心逻辑。

分析内容：
- 将应用分类为 auto_installable / manual / not_available
- 估算迁移时间
- 生成建议和警告
- 汇总数据量
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from easytransfer.core.errors import InvalidProfileError
from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    EnvironmentProfile,
    InstallSource,
    MigrationAnalysis,
)
from easytransfer.planner.app_knowledge import (
    AppKnowledge,
    MigrationStrategy,
    lookup_app,
)

logger = get_logger(__name__)


# ============================================================
# 分析常量
# ============================================================

# 每 GB 文件传输的估计时间（分钟）
_MINUTES_PER_GB_FILE_COPY = 2.0

# 配置恢复的基础时间（分钟）
_BASE_CONFIG_RESTORE_MINUTES = 5.0

# 浏览器数据恢复的基础时间（分钟）
_BROWSER_RESTORE_MINUTES = 3.0

# 凭证迁移的时间（分钟）
_CREDENTIAL_MIGRATE_MINUTES = 2.0


# ============================================================
# 核心分析函数
# ============================================================


async def analyze_profile(profile: EnvironmentProfile) -> MigrationAnalysis:
    """分析环境画像，生成迁移分析结果。

    Args:
        profile: 从扫描阶段获得的环境画像。

    Returns:
        完整的迁移分析结果。
    """
    logger.info("开始分析环境画像: %s", profile.profile_id)

    # 1. 分析每个应用
    app_details: list[dict] = []
    auto_count = 0
    manual_count = 0
    not_available_count = 0
    total_install_minutes = 0.0
    apps_needing_login: list[str] = []

    for app in profile.installed_apps:
        detail = _analyze_single_app(app)
        app_details.append(detail)

        category = detail["category"]
        if category == "auto_installable":
            auto_count += 1
            total_install_minutes += detail.get("estimated_install_minutes", 2.0)
        elif category == "manual_install":
            manual_count += 1
            total_install_minutes += detail.get("estimated_install_minutes", 5.0)
        else:
            not_available_count += 1

        if detail.get("requires_login"):
            apps_needing_login.append(detail["name"])

    # 2. 估算总迁移时间
    estimated_time = _estimate_total_time(
        install_minutes=total_install_minutes,
        total_data_bytes=profile.total_size_bytes,
        config_count=len(profile.app_configs),
        browser_count=len(profile.browser_profiles),
        credential_count=len(profile.credentials),
    )

    # 3. 生成建议和警告
    recommendations = _generate_recommendations(
        profile=profile,
        app_details=app_details,
        auto_count=auto_count,
        manual_count=manual_count,
        apps_needing_login=apps_needing_login,
    )
    warnings = _generate_warnings(
        profile=profile,
        app_details=app_details,
        not_available_count=not_available_count,
    )

    analysis = MigrationAnalysis(
        profile_id=profile.profile_id,
        total_apps=len(profile.installed_apps),
        auto_installable_apps=auto_count,
        manual_install_apps=manual_count,
        total_data_size_bytes=profile.total_size_bytes,
        estimated_time_minutes=int(estimated_time),
        recommendations=recommendations,
        warnings=warnings,
        app_details=app_details,
    )

    logger.info(
        "分析完成: %d 个应用 (%d 自动, %d 手动, %d 不可用), 预计 %d 分钟",
        analysis.total_apps,
        auto_count,
        manual_count,
        not_available_count,
        analysis.estimated_time_minutes,
    )

    return analysis


async def analyze_from_file(profile_path: str) -> MigrationAnalysis:
    """从 JSON 文件加载环境画像并分析。

    Args:
        profile_path: 环境画像 JSON 文件路径。

    Returns:
        迁移分析结果。

    Raises:
        InvalidProfileError: 文件不存在或格式无效。
    """
    path = Path(profile_path)
    if not path.exists():
        raise InvalidProfileError(f"环境画像文件不存在: {profile_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise InvalidProfileError(f"环境画像文件格式无效: {e}") from e

    profile = _dict_to_profile(data)
    return await analyze_profile(profile)


# ============================================================
# 内部辅助函数
# ============================================================


def _analyze_single_app(app: AppInfo) -> dict:
    """分析单个应用的迁移方式。

    Returns:
        包含分析结果的字典。
    """
    knowledge = lookup_app(app.name)

    result: dict = {
        "name": app.name,
        "version": app.version,
        "publisher": app.publisher,
        "size_bytes": app.size_bytes,
    }

    if knowledge:
        result["matched_knowledge"] = knowledge.display_name
        result["winget_id"] = knowledge.winget_id or app.winget_id or ""
        result["strategy"] = knowledge.strategy.value
        result["notes"] = knowledge.notes
        result["requires_login"] = knowledge.requires_login
        result["estimated_install_minutes"] = knowledge.estimated_install_minutes
        result["config_paths"] = knowledge.config_paths
        result["alternatives"] = knowledge.alternatives

        if knowledge.strategy in (
            MigrationStrategy.WINGET_INSTALL,
            MigrationStrategy.STORE_INSTALL,
        ):
            result["category"] = "auto_installable"
        elif knowledge.strategy == MigrationStrategy.NOT_NEEDED:
            result["category"] = "auto_installable"  # 不需要安装也算自动处理
            result["notes"] = knowledge.notes or "新系统自带"
        elif knowledge.strategy == MigrationStrategy.SKIP:
            result["category"] = "not_available"
            result["notes"] = knowledge.notes or "建议跳过"
        else:
            result["category"] = "manual_install"
    elif app.can_auto_install and app.winget_id:
        # 知识库没有，但扫描时已识别为可自动安装
        result["winget_id"] = app.winget_id
        result["strategy"] = MigrationStrategy.WINGET_INSTALL.value
        result["category"] = "auto_installable"
        result["notes"] = app.notes
        result["requires_login"] = False
        result["estimated_install_minutes"] = 2.0
        result["config_paths"] = app.config_paths
        result["alternatives"] = []
    else:
        # 未知应用
        result["winget_id"] = app.winget_id or ""
        result["strategy"] = "unknown"
        result["category"] = "not_available"
        result["notes"] = app.notes or "未在知识库中找到，可能需要手动安装"
        result["requires_login"] = False
        result["estimated_install_minutes"] = 0.0
        result["config_paths"] = app.config_paths
        result["alternatives"] = []

    return result


def _estimate_total_time(
    install_minutes: float,
    total_data_bytes: int,
    config_count: int,
    browser_count: int,
    credential_count: int,
) -> float:
    """估算总迁移时间（分钟）。"""
    data_gb = total_data_bytes / (1024**3)
    file_copy_time = data_gb * _MINUTES_PER_GB_FILE_COPY

    config_time = _BASE_CONFIG_RESTORE_MINUTES if config_count > 0 else 0.0
    browser_time = _BROWSER_RESTORE_MINUTES * browser_count
    credential_time = _CREDENTIAL_MIGRATE_MINUTES if credential_count > 0 else 0.0

    total = install_minutes + file_copy_time + config_time + browser_time + credential_time

    # 最少 5 分钟
    return max(5.0, total)


def _generate_recommendations(
    profile: EnvironmentProfile,
    app_details: list[dict],
    auto_count: int,
    manual_count: int,
    apps_needing_login: list[str],
) -> list[str]:
    """生成迁移建议列表。"""
    recs: list[str] = []

    total = len(profile.installed_apps)
    if total > 0 and auto_count > 0:
        pct = int(auto_count / total * 100)
        recs.append(f"{auto_count}/{total} 个应用({pct}%)可自动安装，建议优先使用自动迁移")

    # 开发环境建议
    if profile.dev_environments:
        dev_names = [d.name for d in profile.dev_environments]
        recs.append(f"建议优先迁移开发环境配置（{', '.join(dev_names[:5])}）")

    # 浏览器建议
    for bp in profile.browser_profiles:
        if bp.has_saved_passwords:
            recs.append(
                f"{bp.browser_name} 保存了密码，建议通过账号同步而非迁移文件"
            )
        if bp.bookmarks_count > 100:
            recs.append(
                f"{bp.browser_name} 有 {bp.bookmarks_count} 个书签，"
                f"建议通过账号同步"
            )

    # 凭证建议
    if profile.credentials:
        cred_types = set(c.credential_type for c in profile.credentials)
        if "ssh_key" in cred_types:
            recs.append("检测到 SSH 密钥，建议安全迁移（加密传输）")

    # 需要登录的应用
    if apps_needing_login:
        login_list = ", ".join(apps_needing_login[:5])
        suffix = f" 等 {len(apps_needing_login)} 个应用" if len(apps_needing_login) > 5 else ""
        recs.append(f"以下应用安装后需要重新登录: {login_list}{suffix}")

    # 大数据量提示
    data_gb = profile.total_size_bytes / (1024**3)
    if data_gb > 50:
        recs.append(
            f"总数据量 {data_gb:.1f}GB 较大，建议使用有线连接或 USB 传输"
        )
    elif data_gb > 10:
        recs.append(
            f"总数据量 {data_gb:.1f}GB，预计传输需要一些时间"
        )

    return recs


def _generate_warnings(
    profile: EnvironmentProfile,
    app_details: list[dict],
    not_available_count: int,
) -> list[str]:
    """生成迁移警告列表。"""
    warns: list[str] = []

    # 不可用应用警告
    if not_available_count > 0:
        unknown_apps = [
            d["name"] for d in app_details if d["category"] == "not_available"
        ]
        if len(unknown_apps) <= 5:
            warns.append(
                f"{not_available_count} 个应用未在知识库中: "
                + ", ".join(unknown_apps)
            )
        else:
            warns.append(
                f"{not_available_count} 个应用未在知识库中，"
                f"可能需要手动安装"
            )

    # 手动安装应用警告
    manual_apps = [
        d["name"] for d in app_details if d["category"] == "manual_install"
    ]
    if manual_apps:
        warns.append(
            f"{len(manual_apps)} 个应用需要手动安装: "
            + ", ".join(manual_apps[:5])
        )

    # 磁盘空间警告
    if profile.system_info.disk_free_gb > 0:
        data_gb = profile.total_size_bytes / (1024**3)
        if data_gb > profile.system_info.disk_free_gb * 0.8:
            warns.append(
                f"迁移数据 ({data_gb:.1f}GB) 接近可用磁盘空间 "
                f"({profile.system_info.disk_free_gb:.1f}GB)，请确保新电脑有足够空间"
            )

    # 凭证安全警告
    if profile.credentials:
        warns.append(
            f"检测到 {len(profile.credentials)} 个凭证/密钥，"
            f"迁移时请确保使用加密传输"
        )

    return warns


def _dict_to_profile(data: dict) -> EnvironmentProfile:
    """从字典数据重建 EnvironmentProfile。

    Args:
        data: 从 JSON 反序列化的字典。

    Returns:
        重建的 EnvironmentProfile。

    Raises:
        InvalidProfileError: 数据格式无效。
    """
    from easytransfer.core.models import (
        BrowserProfile,
        ConfigInfo,
        CredentialInfo,
        DevEnvInfo,
        FileGroup,
        SystemInfo,
    )

    try:
        profile = EnvironmentProfile(
            profile_id=data.get("profile_id", ""),
        )

        # 系统信息
        if "system_info" in data and isinstance(data["system_info"], dict):
            si = data["system_info"]
            profile.system_info = SystemInfo(
                hostname=si.get("hostname", ""),
                os_name=si.get("os_name", ""),
                os_version=si.get("os_version", ""),
                os_build=si.get("os_build", ""),
                architecture=si.get("architecture", ""),
                cpu=si.get("cpu", ""),
                total_memory_gb=si.get("total_memory_gb", 0.0),
                disk_total_gb=si.get("disk_total_gb", 0.0),
                disk_free_gb=si.get("disk_free_gb", 0.0),
                username=si.get("username", ""),
                user_profile_path=si.get("user_profile_path", ""),
            )

        # 已安装应用
        if "installed_apps" in data:
            for a in data["installed_apps"]:
                source = a.get("install_source", "unknown")
                try:
                    install_source = InstallSource(source)
                except ValueError:
                    install_source = InstallSource.UNKNOWN
                profile.installed_apps.append(
                    AppInfo(
                        name=a.get("name", ""),
                        version=a.get("version", ""),
                        publisher=a.get("publisher", ""),
                        install_path=a.get("install_path", ""),
                        install_source=install_source,
                        winget_id=a.get("winget_id"),
                        config_paths=a.get("config_paths", []),
                        data_paths=a.get("data_paths", []),
                        size_bytes=a.get("size_bytes", 0),
                        can_auto_install=a.get("can_auto_install", False),
                        install_command=a.get("install_command"),
                        notes=a.get("notes", ""),
                    )
                )

        # 应用配置
        if "app_configs" in data:
            for c in data["app_configs"]:
                profile.app_configs.append(
                    ConfigInfo(
                        app_name=c.get("app_name", ""),
                        config_path=c.get("config_path", ""),
                        config_type=c.get("config_type", ""),
                        size_bytes=c.get("size_bytes", 0),
                        description=c.get("description", ""),
                    )
                )

        # 用户文件
        if "user_files" in data:
            for f in data["user_files"]:
                profile.user_files.append(
                    FileGroup(
                        group_name=f.get("group_name", ""),
                        source_path=f.get("source_path", ""),
                        file_count=f.get("file_count", 0),
                        total_size_bytes=f.get("total_size_bytes", 0),
                        file_extensions=f.get("file_extensions", []),
                        excluded_patterns=f.get("excluded_patterns", []),
                    )
                )

        # 浏览器
        if "browser_profiles" in data:
            for b in data["browser_profiles"]:
                profile.browser_profiles.append(
                    BrowserProfile(
                        browser_name=b.get("browser_name", ""),
                        profile_path=b.get("profile_path", ""),
                        bookmarks_count=b.get("bookmarks_count", 0),
                        extensions=b.get("extensions", []),
                        has_saved_passwords=b.get("has_saved_passwords", False),
                        history_count=b.get("history_count", 0),
                        data_size_bytes=b.get("data_size_bytes", 0),
                    )
                )

        # 开发环境
        if "dev_environments" in data:
            for d in data["dev_environments"]:
                profile.dev_environments.append(
                    DevEnvInfo(
                        name=d.get("name", ""),
                        version=d.get("version", ""),
                        install_path=d.get("install_path", ""),
                        global_packages=d.get("global_packages", []),
                        config_files=d.get("config_files", []),
                    )
                )

        # 凭证
        if "credentials" in data:
            for c in data["credentials"]:
                profile.credentials.append(
                    CredentialInfo(
                        credential_type=c.get("credential_type", ""),
                        name=c.get("name", ""),
                        path=c.get("path", ""),
                        description=c.get("description", ""),
                    )
                )

        # 总大小
        profile.total_size_bytes = data.get("total_size_bytes", 0)

        return profile

    except Exception as e:
        raise InvalidProfileError(f"无法解析环境画像: {e}") from e
