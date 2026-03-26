"""MCP 工具定义。

定义 6 个暴露给 Agent 的工具。
已实现: scan_environment (M2), analyze_migration (M3)。
其余工具返回 mock 数据，后续里程碑逐步替换。

工具列表：
1. scan_environment — 扫描当前电脑环境
2. analyze_migration — 分析迁移可行性
3. create_migration_package — 打包迁移数据
4. restore_from_package — 从迁移包恢复
5. verify_migration — 验证迁移结果
6. rollback_migration — 回滚迁移操作
"""

from __future__ import annotations

import json
from datetime import datetime

from easytransfer.core.errors import ToolExecutionError
from easytransfer.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================
# 工具定义（JSON Schema）
# ============================================================

TOOL_DEFINITIONS = [
    {
        "name": "scan_environment",
        "description": (
            "扫描当前 Windows 电脑的完整软件环境，包括已安装应用、"
            "用户文件、浏览器数据、开发环境、系统配置等。"
            "返回结构化的环境画像。通常需要 1-5 分钟。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["full", "apps_only", "files_only", "dev_only"],
                    "default": "full",
                    "description": "扫描范围：full=全部, apps_only=仅应用, files_only=仅文件, dev_only=仅开发环境",
                },
                "include_file_sizes": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否统计文件大小（关闭可加快扫描速度）",
                },
                "skip_system_apps": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否跳过系统自带应用",
                },
            },
        },
    },
    {
        "name": "analyze_migration",
        "description": (
            "分析环境画像，返回人类可读的迁移报告。"
            "告诉用户有多少应用可以自动迁移、多少需要手动处理、"
            "总数据量是多少等。几秒钟即可完成。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profile_path": {
                    "type": "string",
                    "description": "环境画像 JSON 文件路径",
                },
            },
            "required": ["profile_path"],
        },
    },
    {
        "name": "create_migration_package",
        "description": (
            "将需要迁移的数据打包为加密的迁移包。"
            "生成一个 6 位迁移码，用于在新电脑上恢复。"
            "耗时取决于数据量。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "profile_path": {
                    "type": "string",
                    "description": "环境画像 JSON 文件路径",
                },
                "include_apps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要迁移的应用列表（不传则迁移全部）",
                },
                "include_files": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含用户文件",
                },
                "include_browser": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含浏览器数据",
                },
                "include_dev_env": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含开发环境",
                },
                "include_credentials": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否包含凭证（SSH密钥等），需用户明确同意",
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["cloud", "local"],
                    "default": "local",
                    "description": "存储方式：cloud=上传到中转服务器, local=保存到本地",
                },
                "output_path": {
                    "type": "string",
                    "description": "本地模式时的保存路径",
                },
            },
            "required": ["profile_path"],
        },
    },
    {
        "name": "restore_from_package",
        "description": (
            "从迁移包恢复环境到当前电脑。可以通过迁移码从云端下载，"
            "或从本地文件恢复。会自动安装应用、恢复配置、传输文件。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "migration_code": {
                    "type": "string",
                    "description": "6 位迁移码（云端模式）",
                },
                "package_path": {
                    "type": "string",
                    "description": "本地迁移包路径",
                },
                "auto_install_apps": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否自动安装应用",
                },
                "restore_files": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否恢复用户文件",
                },
                "restore_configs": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否恢复应用配置",
                },
            },
        },
    },
    {
        "name": "verify_migration",
        "description": (
            "验证迁移结果。检查应用是否安装成功、配置是否生效、"
            "文件是否完整。返回详细的验证报告。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "migration_id": {
                    "type": "string",
                    "description": "迁移记录 ID",
                },
            },
            "required": ["migration_id"],
        },
    },
    {
        "name": "rollback_migration",
        "description": "回滚指定的迁移操作。可以回滚单个应用安装或全部迁移。",
        "input_schema": {
            "type": "object",
            "properties": {
                "migration_id": {
                    "type": "string",
                    "description": "迁移记录 ID",
                },
                "item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要回滚的项目 ID 列表（不传则回滚全部）",
                },
            },
            "required": ["migration_id"],
        },
    },
]

# ============================================================
# 工具调用路由
# ============================================================

# 工具名称 → 处理函数 的映射
_TOOL_HANDLERS = {}


def _register_handler(name: str):
    """注册工具处理函数的装饰器。"""

    def decorator(func):
        _TOOL_HANDLERS[name] = func
        return func

    return decorator


async def handle_tool_call(name: str, arguments: dict) -> str:
    """路由工具调用到对应的处理函数。

    Args:
        name: 工具名称。
        arguments: 工具参数。

    Returns:
        JSON 格式的工具输出。

    Raises:
        ToolExecutionError: 工具不存在或执行失败。
    """
    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        raise ToolExecutionError(f"未知工具: {name}")

    try:
        result = await handler(arguments)
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error("工具 %s 执行失败: %s", name, e)
        raise ToolExecutionError(f"工具 {name} 执行失败: {e}") from e


# ============================================================
# 工具实现
# ============================================================


@_register_handler("scan_environment")
async def _handle_scan_environment(arguments: dict) -> dict:
    """扫描环境 — 调用真实扫描逻辑。"""
    from dataclasses import asdict

    from easytransfer.core.models import ScanScope
    from easytransfer.scanner.orchestrator import run_full_scan

    scope_str = arguments.get("scope", "full")
    scope = ScanScope(scope_str)

    profile = await run_full_scan(
        scope=scope,
        skip_system_apps=arguments.get("skip_system_apps", True),
        include_file_sizes=arguments.get("include_file_sizes", True),
    )

    return {
        "status": "success",
        "message": f"环境扫描完成 (scope={scope_str})",
        "profile_id": profile.profile_id,
        "scan_time": profile.scan_time.isoformat(),
        "system": {
            "hostname": profile.system_info.hostname,
            "os": profile.system_info.os_name,
            "cpu": profile.system_info.cpu,
            "memory_gb": profile.system_info.total_memory_gb,
            "disk_free_gb": profile.system_info.disk_free_gb,
        },
        "summary": {
            "installed_apps": len(profile.installed_apps),
            "app_configs": len(profile.app_configs),
            "user_file_groups": len(profile.user_files),
            "browser_profiles": len(profile.browser_profiles),
            "dev_environments": len(profile.dev_environments),
            "credentials": len(profile.credentials),
            "total_size_gb": round(profile.total_size_bytes / (1024**3), 1),
        },
        "apps": [
            {"name": a.name, "version": a.version, "auto_install": a.can_auto_install}
            for a in profile.installed_apps[:50]  # 最多返回 50 个
        ],
    }


@_register_handler("analyze_migration")
async def _handle_analyze_migration(arguments: dict) -> dict:
    """分析迁移 — 调用真实分析逻辑。"""
    from easytransfer.planner.analyzer import analyze_from_file

    profile_path = arguments.get("profile_path", "")
    logger.info("分析迁移画像: %s", profile_path)

    analysis = await analyze_from_file(profile_path)

    return {
        "status": "success",
        "message": "迁移分析完成",
        "analysis": {
            "profile_id": analysis.profile_id,
            "total_apps": analysis.total_apps,
            "auto_installable": analysis.auto_installable_apps,
            "manual_install": analysis.manual_install_apps,
            "not_available": analysis.total_apps - analysis.auto_installable_apps - analysis.manual_install_apps,
            "total_data_size_gb": round(analysis.total_data_size_bytes / (1024**3), 1),
            "estimated_time_minutes": analysis.estimated_time_minutes,
        },
        "recommendations": analysis.recommendations,
        "warnings": analysis.warnings,
        "app_details": analysis.app_details[:50],  # 最多返回 50 个
    }


@_register_handler("create_migration_package")
async def _handle_create_package(arguments: dict) -> dict:
    """创建迁移包 — 调用真实打包逻辑。"""
    from pathlib import Path

    from easytransfer.packager.packer import pack_migration
    from easytransfer.planner.analyzer import analyze_from_file

    profile_path = arguments.get("profile_path", "")
    logger.info("创建迁移包: profile=%s", profile_path)

    # 加载环境画像
    from easytransfer.planner.analyzer import _dict_to_profile

    path = Path(profile_path)
    if not path.exists():
        return {"status": "error", "message": f"环境画像文件不存在: {profile_path}"}

    import json as _json

    data = _json.loads(path.read_text(encoding="utf-8"))
    profile = _dict_to_profile(data)

    # 运行分析
    from easytransfer.planner.analyzer import analyze_profile

    analysis = await analyze_profile(profile)

    # 打包
    pkg_info = await pack_migration(
        profile=profile,
        analysis=analysis,
        include_files=arguments.get("include_files", True),
        include_browser=arguments.get("include_browser", True),
        include_dev_env=arguments.get("include_dev_env", True),
        include_credentials=arguments.get("include_credentials", False),
        output_path=arguments.get("output_path"),
        output_mode=arguments.get("output_mode", "local"),
    )

    return {
        "status": "success",
        "message": "迁移包创建完成",
        "package_info": {
            "package_id": pkg_info.package_id,
            "migration_code": pkg_info.migration_code,
            "package_size_mb": round(pkg_info.package_size_bytes / (1024 * 1024), 1),
            "item_count": pkg_info.item_count,
            "storage_mode": pkg_info.storage_mode.value,
            "storage_path": pkg_info.storage_path,
            "encryption": pkg_info.encryption_info,
            "expires_at": pkg_info.expires_at.isoformat() if pkg_info.expires_at else None,
        },
    }


@_register_handler("restore_from_package")
async def _mock_restore(arguments: dict) -> dict:
    """[Mock] 从迁移包恢复 — 返回示例恢复结果。"""
    code = arguments.get("migration_code", "")
    path = arguments.get("package_path", "")
    logger.info("[Mock] 恢复迁移包, code=%s, path=%s", code, path)

    return {
        "status": "success",
        "message": "[Mock] 迁移恢复完成",
        "result": {
            "migration_id": "mig-mock-001",
            "total_items": 45,
            "success": 42,
            "failed": 2,
            "skipped": 1,
            "manual_actions": [
                "请手动登录 Adobe Creative Cloud 以激活 Photoshop",
                "请重新登录微信",
            ],
        },
        "note": "这是 Mock 数据，真实恢复功能将在 M5 阶段实现。",
    }


@_register_handler("verify_migration")
async def _mock_verify(arguments: dict) -> dict:
    """[Mock] 验证迁移 — 返回示例验证结果。"""
    migration_id = arguments.get("migration_id", "")
    logger.info("[Mock] 验证迁移: %s", migration_id)

    return {
        "status": "success",
        "message": "[Mock] 验证完成",
        "verification": {
            "migration_id": migration_id,
            "total_checked": 45,
            "passed": 43,
            "failed": 2,
            "details": [
                {"item": "VS Code", "status": "passed", "note": "应用和配置均正常"},
                {"item": "Chrome", "status": "passed", "note": "书签和扩展已恢复"},
                {"item": "Photoshop", "status": "failed", "note": "需要重新激活许可证"},
            ],
        },
        "note": "这是 Mock 数据，真实验证功能将在 M5 阶段实现。",
    }


@_register_handler("rollback_migration")
async def _mock_rollback(arguments: dict) -> dict:
    """[Mock] 回滚迁移 — 返回示例回滚结果。"""
    migration_id = arguments.get("migration_id", "")
    item_ids = arguments.get("item_ids")
    logger.info("[Mock] 回滚迁移: %s, items=%s", migration_id, item_ids)

    return {
        "status": "success",
        "message": "[Mock] 回滚完成",
        "rollback": {
            "migration_id": migration_id,
            "rolled_back_items": len(item_ids) if item_ids else 45,
            "failed_rollbacks": 0,
        },
        "note": "这是 Mock 数据，真实回滚功能将在 M6 阶段实现。",
    }
