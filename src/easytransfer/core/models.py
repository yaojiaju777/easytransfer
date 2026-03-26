"""EasyTransfer 核心数据模型。

所有模块共享的数据结构定义。使用 dataclass 保持简洁，
使用 Type Hints 确保类型安全。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ============================================================
# 枚举类型
# ============================================================


class ScanScope(str, Enum):
    """扫描范围。"""

    FULL = "full"
    APPS_ONLY = "apps_only"
    FILES_ONLY = "files_only"
    DEV_ONLY = "dev_only"


class InstallSource(str, Enum):
    """应用安装来源。"""

    WINGET = "winget"
    MSI = "msi"
    EXE = "exe"
    PORTABLE = "portable"
    STORE = "store"
    UNKNOWN = "unknown"


class MigrationStatus(str, Enum):
    """迁移状态机。"""

    IDLE = "idle"
    SCANNING = "scanning"
    ANALYZED = "analyzed"
    PACKAGING = "packaging"
    PACKAGED = "packaged"
    DOWNLOADING = "downloading"
    RESTORING = "restoring"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class MigrationItemStatus(str, Enum):
    """单个迁移项目的状态。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class StorageMode(str, Enum):
    """迁移包存储方式。"""

    CLOUD = "cloud"
    LOCAL = "local"


class Priority(int, Enum):
    """扫描器/迁移项目优先级。"""

    P0 = 0  # 核心功能，必须迁移
    P1 = 1  # 重要，默认迁移
    P2 = 2  # 可选，用户选择


# ============================================================
# 系统信息
# ============================================================


@dataclass
class SystemInfo:
    """操作系统和硬件信息。"""

    hostname: str = ""
    os_name: str = ""  # e.g., "Windows 11 Pro"
    os_version: str = ""  # e.g., "10.0.22631"
    os_build: str = ""
    architecture: str = ""  # e.g., "AMD64"
    cpu: str = ""
    total_memory_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    username: str = ""
    user_profile_path: str = ""  # e.g., "C:\\Users\\john"


# ============================================================
# 应用相关
# ============================================================


@dataclass
class AppInfo:
    """单个已安装应用的信息。"""

    name: str = ""
    version: str = ""
    publisher: str = ""
    install_path: str = ""
    install_source: InstallSource = InstallSource.UNKNOWN
    winget_id: str | None = None
    config_paths: list[str] = field(default_factory=list)
    data_paths: list[str] = field(default_factory=list)
    size_bytes: int = 0
    last_used: datetime | None = None
    can_auto_install: bool = False
    install_command: str | None = None
    notes: str = ""


@dataclass
class ConfigInfo:
    """应用配置文件信息。"""

    app_name: str = ""
    config_path: str = ""
    config_type: str = ""  # e.g., "json", "ini", "registry"
    size_bytes: int = 0
    description: str = ""


# ============================================================
# 文件相关
# ============================================================


@dataclass
class FileGroup:
    """一组用户文件（按目录分组）。"""

    group_name: str = ""  # e.g., "Documents", "Desktop", "Projects"
    source_path: str = ""
    file_count: int = 0
    total_size_bytes: int = 0
    file_extensions: list[str] = field(default_factory=list)  # e.g., [".docx", ".pdf"]
    excluded_patterns: list[str] = field(default_factory=list)  # 排除的模式


# ============================================================
# 浏览器相关
# ============================================================


@dataclass
class BrowserProfile:
    """浏览器画像。"""

    browser_name: str = ""  # e.g., "Chrome", "Edge", "Firefox"
    profile_path: str = ""
    bookmarks_count: int = 0
    extensions: list[str] = field(default_factory=list)
    has_saved_passwords: bool = False
    history_count: int = 0
    data_size_bytes: int = 0


# ============================================================
# 开发环境相关
# ============================================================


@dataclass
class DevEnvInfo:
    """开发环境信息。"""

    name: str = ""  # e.g., "Python", "Node.js", "Git"
    version: str = ""
    install_path: str = ""
    global_packages: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)


# ============================================================
# 凭证相关
# ============================================================


@dataclass
class CredentialInfo:
    """凭证信息（仅元数据，不含实际凭证内容）。"""

    credential_type: str = ""  # e.g., "ssh_key", "gpg_key", "api_token"
    name: str = ""  # e.g., "id_rsa", "github_token"
    path: str = ""
    description: str = ""


# ============================================================
# 顶层数据结构
# ============================================================


@dataclass
class ScanResult:
    """单个扫描器的输出。"""

    scanner_name: str = ""
    success: bool = True
    error_message: str = ""
    items_found: int = 0
    data: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


@dataclass
class EnvironmentProfile:
    """一台电脑的完整环境画像 — 扫描的最终产出物。"""

    profile_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scan_time: datetime = field(default_factory=datetime.now)
    system_info: SystemInfo = field(default_factory=SystemInfo)
    installed_apps: list[AppInfo] = field(default_factory=list)
    app_configs: list[ConfigInfo] = field(default_factory=list)
    user_files: list[FileGroup] = field(default_factory=list)
    browser_profiles: list[BrowserProfile] = field(default_factory=list)
    dev_environments: list[DevEnvInfo] = field(default_factory=list)
    credentials: list[CredentialInfo] = field(default_factory=list)
    system_settings: dict = field(default_factory=dict)
    total_size_bytes: int = 0


@dataclass
class MigrationAnalysis:
    """迁移分析结果 — analyze_migration 工具的输出。"""

    profile_id: str = ""
    total_apps: int = 0
    auto_installable_apps: int = 0
    manual_install_apps: int = 0
    total_data_size_bytes: int = 0
    estimated_time_minutes: int = 0
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    app_details: list[dict] = field(default_factory=list)


@dataclass
class MigrationPackageInfo:
    """迁移包信息 — create_migration_package 工具的输出。"""

    package_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    migration_code: str = ""  # 6 位迁移码
    package_size_bytes: int = 0
    item_count: int = 0
    storage_mode: StorageMode = StorageMode.LOCAL
    storage_path: str = ""
    expires_at: datetime | None = None
    encryption_info: str = "AES-256-GCM with PBKDF2 key derivation"


@dataclass
class MigrationItemResult:
    """单个迁移项目的结果。"""

    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    item_type: str = ""  # "app_install", "config_restore", "file_copy", etc.
    item_name: str = ""
    status: MigrationItemStatus = MigrationItemStatus.PENDING
    error_message: str = ""
    duration_seconds: float = 0.0
    rollback_info: str = ""  # 回滚所需的信息


@dataclass
class MigrationResult:
    """迁移执行结果 — restore_from_package 工具的输出。"""

    migration_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: MigrationStatus = MigrationStatus.IDLE
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    items: list[MigrationItemResult] = field(default_factory=list)
    manual_actions: list[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """验证报告 — verify_migration 工具的输出。"""

    migration_id: str = ""
    verified_at: datetime = field(default_factory=datetime.now)
    total_checked: int = 0
    passed: int = 0
    failed: int = 0
    details: list[dict] = field(default_factory=list)


@dataclass
class RollbackResult:
    """回滚结果 — rollback_migration 工具的输出。"""

    migration_id: str = ""
    rolled_back_items: int = 0
    failed_rollbacks: int = 0
    details: list[dict] = field(default_factory=list)
