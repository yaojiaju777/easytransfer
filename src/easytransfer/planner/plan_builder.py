"""迁移计划构建器。

基于 MigrationAnalysis 构建结构化的迁移执行计划（JSON）。
计划按动作类型分组，供后续的执行器（M5）逐步执行。

动作类型：
- app_install: 应用安装（winget / 手动）
- config_restore: 配置文件恢复
- file_copy: 用户文件复制
- browser_restore: 浏览器数据恢复
- dev_env_setup: 开发环境恢复
- credential_migrate: 凭证迁移
- manual_action: 需要用户手动操作的步骤
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    EnvironmentProfile,
    MigrationAnalysis,
)
from easytransfer.planner.app_knowledge import MigrationStrategy, lookup_app

logger = get_logger(__name__)


# ============================================================
# 计划数据结构
# ============================================================


@dataclass
class PlanAction:
    """单个迁移动作。"""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: str = ""  # app_install, config_restore, file_copy, etc.
    name: str = ""  # 人类可读名称
    description: str = ""
    priority: int = 1  # 0=最高, 1=普通, 2=可选
    method: str = ""  # e.g., "winget", "copy", "manual"
    command: str = ""  # 执行命令（如 winget install --id ...）
    source_path: str = ""  # 源路径
    target_path: str = ""  # 目标路径
    estimated_minutes: float = 0.0
    requires_admin: bool = False
    requires_user_action: bool = False  # 需要用户手动操作
    details: dict = field(default_factory=dict)


@dataclass
class PlanGroup:
    """按类型分组的动作组。"""

    group_type: str = ""
    group_name: str = ""
    actions: list[PlanAction] = field(default_factory=list)
    total_estimated_minutes: float = 0.0


@dataclass
class MigrationPlan:
    """完整的迁移执行计划。"""

    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    profile_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    groups: list[PlanGroup] = field(default_factory=list)
    total_actions: int = 0
    total_estimated_minutes: float = 0.0
    summary: dict = field(default_factory=dict)


# ============================================================
# 计划构建
# ============================================================


def build_plan(
    profile: EnvironmentProfile,
    analysis: MigrationAnalysis,
    include_files: bool = True,
    include_browser: bool = True,
    include_dev_env: bool = True,
    include_credentials: bool = False,
) -> MigrationPlan:
    """构建迁移执行计划。

    Args:
        profile: 环境画像。
        analysis: 迁移分析结果。
        include_files: 是否包含用户文件迁移。
        include_browser: 是否包含浏览器数据。
        include_dev_env: 是否包含开发环境。
        include_credentials: 是否包含凭证迁移。

    Returns:
        结构化的迁移执行计划。
    """
    logger.info("开始构建迁移计划: profile=%s", profile.profile_id)

    groups: list[PlanGroup] = []

    # 1. 应用安装组
    app_group = _build_app_install_group(analysis)
    if app_group.actions:
        groups.append(app_group)

    # 2. 配置恢复组
    config_group = _build_config_restore_group(profile, analysis)
    if config_group.actions:
        groups.append(config_group)

    # 3. 用户文件复制组
    if include_files:
        file_group = _build_file_copy_group(profile)
        if file_group.actions:
            groups.append(file_group)

    # 4. 浏览器数据恢复组
    if include_browser:
        browser_group = _build_browser_restore_group(profile)
        if browser_group.actions:
            groups.append(browser_group)

    # 5. 开发环境恢复组
    if include_dev_env:
        dev_group = _build_dev_env_group(profile)
        if dev_group.actions:
            groups.append(dev_group)

    # 6. 凭证迁移组
    if include_credentials:
        cred_group = _build_credential_group(profile)
        if cred_group.actions:
            groups.append(cred_group)

    # 7. 手动操作组（总是包含）
    manual_group = _build_manual_action_group(analysis)
    if manual_group.actions:
        groups.append(manual_group)

    # 汇总
    total_actions = sum(len(g.actions) for g in groups)
    total_minutes = sum(g.total_estimated_minutes for g in groups)

    plan = MigrationPlan(
        profile_id=profile.profile_id,
        groups=groups,
        total_actions=total_actions,
        total_estimated_minutes=round(total_minutes, 1),
        summary={
            "total_groups": len(groups),
            "total_actions": total_actions,
            "estimated_minutes": round(total_minutes, 1),
            "auto_install_apps": analysis.auto_installable_apps,
            "manual_install_apps": analysis.manual_install_apps,
            "file_groups": len(profile.user_files) if include_files else 0,
            "browsers": len(profile.browser_profiles) if include_browser else 0,
            "dev_environments": len(profile.dev_environments) if include_dev_env else 0,
            "credentials": len(profile.credentials) if include_credentials else 0,
        },
    )

    logger.info(
        "迁移计划构建完成: %d 个组, %d 个动作, 预计 %.0f 分钟",
        len(groups),
        total_actions,
        total_minutes,
    )

    return plan


def plan_to_dict(plan: MigrationPlan) -> dict:
    """将迁移计划转为可序列化的字典。"""
    return asdict(plan)


# ============================================================
# 各组构建函数
# ============================================================


def _build_app_install_group(analysis: MigrationAnalysis) -> PlanGroup:
    """构建应用安装组。"""
    group = PlanGroup(
        group_type="app_install",
        group_name="应用安装",
    )

    for detail in analysis.app_details:
        category = detail.get("category", "")
        if category == "not_available":
            continue

        strategy = detail.get("strategy", "")
        winget_id = detail.get("winget_id", "")

        action = PlanAction(
            action_type="app_install",
            name=detail["name"],
            estimated_minutes=detail.get("estimated_install_minutes", 2.0),
        )

        if strategy == MigrationStrategy.WINGET_INSTALL.value and winget_id:
            action.method = "winget"
            action.command = f"winget install --id {winget_id} --accept-source-agreements --accept-package-agreements"
            action.description = f"通过 winget 安装 {detail['name']}"
            action.requires_admin = False
        elif strategy == MigrationStrategy.STORE_INSTALL.value:
            action.method = "store"
            action.description = f"从 Microsoft Store 安装 {detail['name']}"
            action.requires_user_action = True
        elif strategy == MigrationStrategy.NOT_NEEDED.value:
            action.method = "skip"
            action.description = detail.get("notes", "新系统自带")
            action.estimated_minutes = 0.0
        elif strategy == MigrationStrategy.MANUAL_DOWNLOAD.value:
            action.method = "manual"
            action.description = f"需要手动下载安装 {detail['name']}"
            action.requires_user_action = True
            if detail.get("notes"):
                action.description += f" — {detail['notes']}"
        elif strategy == MigrationStrategy.PORTABLE_COPY.value:
            action.method = "copy"
            action.description = f"复制便携版 {detail['name']}"
        elif strategy == MigrationStrategy.ACCOUNT_SYNC.value:
            action.method = "sync"
            action.description = f"通过账号同步 {detail['name']}"
            action.requires_user_action = True
        else:
            # 从扫描结果中获取的 winget 信息
            if winget_id:
                action.method = "winget"
                action.command = f"winget install --id {winget_id} --accept-source-agreements --accept-package-agreements"
                action.description = f"通过 winget 安装 {detail['name']}"
            else:
                action.method = "manual"
                action.description = f"需要手动安装 {detail['name']}"
                action.requires_user_action = True

        # 设置优先级
        if category == "auto_installable":
            action.priority = 1
        else:
            action.priority = 2

        action.details = {
            "version": detail.get("version", ""),
            "requires_login": detail.get("requires_login", False),
        }

        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_config_restore_group(
    profile: EnvironmentProfile,
    analysis: MigrationAnalysis,
) -> PlanGroup:
    """构建配置恢复组。"""
    group = PlanGroup(
        group_type="config_restore",
        group_name="配置恢复",
    )

    # 从应用配置列表构建
    for config in profile.app_configs:
        action = PlanAction(
            action_type="config_restore",
            name=f"{config.app_name} 配置",
            description=f"恢复 {config.app_name} 的配置文件",
            method="copy",
            source_path=config.config_path,
            estimated_minutes=0.5,
            details={
                "config_type": config.config_type,
                "size_bytes": config.size_bytes,
            },
        )
        group.actions.append(action)

    # 从知识库补充应用特定配置
    seen_apps: set[str] = {c.app_name for c in profile.app_configs}
    for detail in analysis.app_details:
        app_name = detail["name"]
        if app_name in seen_apps:
            continue
        config_paths = detail.get("config_paths", [])
        if config_paths:
            for cfg_path in config_paths:
                action = PlanAction(
                    action_type="config_restore",
                    name=f"{app_name} 配置",
                    description=f"恢复 {app_name} 的配置",
                    method="copy",
                    source_path=cfg_path,
                    estimated_minutes=0.5,
                )
                group.actions.append(action)
            seen_apps.add(app_name)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_file_copy_group(profile: EnvironmentProfile) -> PlanGroup:
    """构建文件复制组。"""
    group = PlanGroup(
        group_type="file_copy",
        group_name="用户文件迁移",
    )

    for fg in profile.user_files:
        size_gb = fg.total_size_bytes / (1024**3)
        est_minutes = max(0.5, size_gb * 2.0)

        action = PlanAction(
            action_type="file_copy",
            name=fg.group_name,
            description=f"迁移 {fg.group_name} ({fg.file_count} 个文件, {size_gb:.1f}GB)",
            method="copy",
            source_path=fg.source_path,
            estimated_minutes=round(est_minutes, 1),
            details={
                "file_count": fg.file_count,
                "size_bytes": fg.total_size_bytes,
                "extensions": fg.file_extensions,
            },
        )
        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_browser_restore_group(profile: EnvironmentProfile) -> PlanGroup:
    """构建浏览器恢复组。"""
    group = PlanGroup(
        group_type="browser_restore",
        group_name="浏览器数据恢复",
    )

    for bp in profile.browser_profiles:
        action = PlanAction(
            action_type="browser_restore",
            name=f"{bp.browser_name} 数据",
            description=f"恢复 {bp.browser_name} 浏览器数据",
            method="copy",
            source_path=bp.profile_path,
            estimated_minutes=3.0,
            details={
                "bookmarks_count": bp.bookmarks_count,
                "extensions": bp.extensions,
                "has_saved_passwords": bp.has_saved_passwords,
                "data_size_bytes": bp.data_size_bytes,
            },
        )

        if bp.has_saved_passwords:
            action.requires_user_action = True
            action.description += "（含已保存密码，建议通过账号同步）"

        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_dev_env_group(profile: EnvironmentProfile) -> PlanGroup:
    """构建开发环境恢复组。"""
    group = PlanGroup(
        group_type="dev_env_setup",
        group_name="开发环境恢复",
    )

    for dev in profile.dev_environments:
        action = PlanAction(
            action_type="dev_env_setup",
            name=f"{dev.name} 环境",
            description=f"恢复 {dev.name} {dev.version} 开发环境",
            method="install_and_configure",
            estimated_minutes=3.0,
            details={
                "version": dev.version,
                "global_packages": dev.global_packages,
                "config_files": dev.config_files,
            },
        )
        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_credential_group(profile: EnvironmentProfile) -> PlanGroup:
    """构建凭证迁移组。"""
    group = PlanGroup(
        group_type="credential_migrate",
        group_name="凭证迁移",
    )

    for cred in profile.credentials:
        action = PlanAction(
            action_type="credential_migrate",
            name=f"{cred.credential_type}: {cred.name}",
            description=f"迁移 {cred.credential_type} — {cred.name}",
            method="encrypted_copy",
            source_path=cred.path,
            estimated_minutes=1.0,
            requires_admin=False,
            details={
                "credential_type": cred.credential_type,
                "description": cred.description,
            },
        )
        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group


def _build_manual_action_group(analysis: MigrationAnalysis) -> PlanGroup:
    """构建需要用户手动操作的步骤组。"""
    group = PlanGroup(
        group_type="manual_action",
        group_name="需要手动操作",
    )

    # 需要登录的应用
    login_apps = [
        d for d in analysis.app_details
        if d.get("requires_login") and d.get("category") != "not_available"
    ]
    if login_apps:
        action = PlanAction(
            action_type="manual_action",
            name="应用登录",
            description="以下应用安装后需要重新登录: " + ", ".join(
                a["name"] for a in login_apps
            ),
            method="user_action",
            requires_user_action=True,
            estimated_minutes=len(login_apps) * 1.0,
            details={
                "apps": [a["name"] for a in login_apps],
            },
        )
        group.actions.append(action)

    # 不可用应用的建议
    unavailable = [
        d for d in analysis.app_details
        if d.get("category") == "not_available"
        and d.get("notes")
    ]
    if unavailable:
        action = PlanAction(
            action_type="manual_action",
            name="手动处理应用",
            description="以下应用需要手动处理: " + ", ".join(
                f"{a['name']} ({a.get('notes', '')})" for a in unavailable[:10]
            ),
            method="user_action",
            requires_user_action=True,
            estimated_minutes=len(unavailable) * 2.0,
        )
        group.actions.append(action)

    group.total_estimated_minutes = sum(a.estimated_minutes for a in group.actions)
    return group
