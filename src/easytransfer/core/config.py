"""EasyTransfer 配置系统。

管理应用配置，支持从文件加载和环境变量覆盖。
配置文件默认位于 ~/.easytransfer/config.json。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


# 默认配置目录
APP_DIR = Path.home() / ".easytransfer"
CONFIG_FILE = APP_DIR / "config.json"

# 版本号
VERSION = "0.1.0"

# 项目名称
APP_NAME = "EasyTransfer"


@dataclass
class ScanConfig:
    """扫描相关配置。"""

    skip_system_apps: bool = True
    include_file_sizes: bool = True
    max_file_scan_depth: int = 5
    excluded_dirs: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".venv",
            "__pycache__",
            ".git",
            ".tox",
            "dist",
            "build",
            ".cache",
        ]
    )


@dataclass
class PackageConfig:
    """打包相关配置。"""

    chunk_size_bytes: int = 10 * 1024 * 1024  # 10MB per chunk
    compression_level: int = 6  # zlib compression level (1-9)
    max_package_size_gb: float = 50.0


@dataclass
class TransferConfig:
    """传输相关配置。"""

    relay_server_url: str = ""  # 中转服务器 URL（MVP 阶段暂不启用）
    max_retries: int = 3
    retry_delay_seconds: int = 5
    migration_code_length: int = 6
    migration_code_expiry_hours: int = 24


@dataclass
class SecurityConfig:
    """安全相关配置。"""

    pbkdf2_iterations: int = 600_000
    encryption_algorithm: str = "AES-256-GCM"


@dataclass
class AppConfig:
    """应用总配置。"""

    version: str = VERSION
    app_name: str = APP_NAME
    data_dir: str = str(APP_DIR)
    scan: ScanConfig = field(default_factory=ScanConfig)
    package: PackageConfig = field(default_factory=PackageConfig)
    transfer: TransferConfig = field(default_factory=TransferConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


def load_config(config_path: Path | None = None) -> AppConfig:
    """加载配置。

    优先级：环境变量 > 配置文件 > 默认值。

    Args:
        config_path: 配置文件路径，默认 ~/.easytransfer/config.json。

    Returns:
        加载完成的 AppConfig 实例。
    """
    config = AppConfig()
    path = config_path or CONFIG_FILE

    # 从文件加载
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _apply_dict_to_config(config, data)
        except (json.JSONDecodeError, KeyError):
            pass  # 配置文件损坏时使用默认值

    # 环境变量覆盖
    if relay_url := os.environ.get("EASYTRANSFER_RELAY_URL"):
        config.transfer.relay_server_url = relay_url

    if data_dir := os.environ.get("EASYTRANSFER_DATA_DIR"):
        config.data_dir = data_dir

    return config


def save_config(config: AppConfig, config_path: Path | None = None) -> None:
    """保存配置到文件。

    Args:
        config: 要保存的配置实例。
        config_path: 目标路径，默认 ~/.easytransfer/config.json。
    """
    path = config_path or CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    data = _config_to_dict(config)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _apply_dict_to_config(config: AppConfig, data: dict) -> None:
    """将字典数据应用到配置对象。"""
    if "scan" in data and isinstance(data["scan"], dict):
        for key, value in data["scan"].items():
            if hasattr(config.scan, key):
                setattr(config.scan, key, value)

    if "package" in data and isinstance(data["package"], dict):
        for key, value in data["package"].items():
            if hasattr(config.package, key):
                setattr(config.package, key, value)

    if "transfer" in data and isinstance(data["transfer"], dict):
        for key, value in data["transfer"].items():
            if hasattr(config.transfer, key):
                setattr(config.transfer, key, value)

    if "security" in data and isinstance(data["security"], dict):
        for key, value in data["security"].items():
            if hasattr(config.security, key):
                setattr(config.security, key, value)


def _config_to_dict(config: AppConfig) -> dict:
    """将配置对象转为字典（用于序列化）。"""
    from dataclasses import asdict

    return asdict(config)
