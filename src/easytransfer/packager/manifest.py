"""迁移包清单文件处理。

manifest.json 包含迁移包的完整元数据，
用于在目标端恢复时了解包内容。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime

from easytransfer.core.config import VERSION
from easytransfer.core.errors import ManifestError
from easytransfer.core.models import EnvironmentProfile, MigrationAnalysis


def generate_manifest(
    profile: EnvironmentProfile,
    analysis: MigrationAnalysis | None = None,
    include_files: bool = True,
    include_browser: bool = True,
    include_dev_env: bool = True,
    include_credentials: bool = False,
) -> dict:
    """生成迁移包清单。

    Args:
        profile: 环境画像。
        analysis: 迁移分析结果（可选）。
        include_files: 是否包含用户文件。
        include_browser: 是否包含浏览器数据。
        include_dev_env: 是否包含开发环境。
        include_credentials: 是否包含凭证。

    Returns:
        清单数据字典。
    """
    manifest: dict = {
        "manifest_version": "1.0",
        "easytransfer_version": VERSION,
        "package_id": str(uuid.uuid4())[:8],
        "created_at": datetime.now().isoformat(),
        "source_system": {
            "hostname": profile.system_info.hostname,
            "os_name": profile.system_info.os_name,
            "os_version": profile.system_info.os_version,
            "username": profile.system_info.username,
        },
        "profile_id": profile.profile_id,
        "contents": {
            "installed_apps": len(profile.installed_apps),
            "app_configs": len(profile.app_configs),
            "user_files": len(profile.user_files) if include_files else 0,
            "browser_profiles": len(profile.browser_profiles) if include_browser else 0,
            "dev_environments": len(profile.dev_environments) if include_dev_env else 0,
            "credentials": len(profile.credentials) if include_credentials else 0,
        },
        "options": {
            "include_files": include_files,
            "include_browser": include_browser,
            "include_dev_env": include_dev_env,
            "include_credentials": include_credentials,
        },
        "apps": [
            {
                "name": app.name,
                "version": app.version,
                "winget_id": app.winget_id,
                "can_auto_install": app.can_auto_install,
                "install_source": app.install_source.value
                if hasattr(app.install_source, "value")
                else str(app.install_source),
            }
            for app in profile.installed_apps
        ],
        "total_size_bytes": profile.total_size_bytes,
    }

    if analysis:
        manifest["analysis_summary"] = {
            "auto_installable_apps": analysis.auto_installable_apps,
            "manual_install_apps": analysis.manual_install_apps,
            "estimated_time_minutes": analysis.estimated_time_minutes,
        }

    return manifest


def serialize_manifest(manifest: dict) -> bytes:
    """将清单序列化为 JSON 字节。"""
    return json.dumps(
        manifest, ensure_ascii=False, indent=2, default=str
    ).encode("utf-8")


def parse_manifest(data: bytes) -> dict:
    """解析清单 JSON 数据。

    Args:
        data: JSON 字节数据。

    Returns:
        清单字典。

    Raises:
        ManifestError: 解析失败。
    """
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ManifestError(f"清单解析失败: {e}") from e

    if not isinstance(manifest, dict):
        raise ManifestError("清单格式无效：顶层必须是对象")

    required_fields = ["manifest_version", "package_id", "contents"]
    for field in required_fields:
        if field not in manifest:
            raise ManifestError(f"清单缺少必需字段: {field}")

    return manifest
