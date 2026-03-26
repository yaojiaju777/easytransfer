"""迁移包打包器。

将环境画像和相关数据打包为加密的 .etpkg 文件。

打包流程：
1. 生成 manifest.json
2. 生成 install_plan.json
3. 收集配置文件
4. 打包为 tar.gz
5. 生成迁移码
6. 加密为 .etpkg
"""

from __future__ import annotations

import io
import json
import tarfile
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from easytransfer.core.config import AppConfig, load_config
from easytransfer.core.errors import PackageError
from easytransfer.core.logging import get_logger
from easytransfer.core.models import (
    EnvironmentProfile,
    MigrationAnalysis,
    MigrationPackageInfo,
    StorageMode,
)
from easytransfer.packager.manifest import generate_manifest, serialize_manifest
from easytransfer.security.crypto import encrypt_data
from easytransfer.security.key_derivation import generate_migration_code

logger = get_logger(__name__)


async def pack_migration(
    profile: EnvironmentProfile,
    analysis: MigrationAnalysis | None = None,
    include_files: bool = True,
    include_browser: bool = True,
    include_dev_env: bool = True,
    include_credentials: bool = False,
    output_path: str | None = None,
    output_mode: str = "local",
    config: AppConfig | None = None,
) -> MigrationPackageInfo:
    """打包迁移数据为加密的 .etpkg 文件。

    Args:
        profile: 环境画像。
        analysis: 迁移分析结果（可选，会自动生成）。
        include_files: 是否包含用户文件。
        include_browser: 是否包含浏览器数据。
        include_dev_env: 是否包含开发环境。
        include_credentials: 是否包含凭证。
        output_path: 输出文件路径。
        output_mode: 存储方式 (local/cloud)。
        config: 应用配置。

    Returns:
        迁移包信息（含迁移码）。

    Raises:
        PackageError: 打包失败。
    """
    if config is None:
        config = load_config()

    logger.info("开始打包迁移数据: profile=%s", profile.profile_id)

    try:
        # 1. 如果没有分析结果，运行分析
        if analysis is None:
            from easytransfer.planner.analyzer import analyze_profile

            analysis = await analyze_profile(profile)

        # 2. 生成 manifest
        manifest = generate_manifest(
            profile=profile,
            analysis=analysis,
            include_files=include_files,
            include_browser=include_browser,
            include_dev_env=include_dev_env,
            include_credentials=include_credentials,
        )

        # 3. 构建安装计划
        install_plan = _build_install_plan(profile, analysis)

        # 4. 创建 tar.gz 包
        tar_data = _create_tar_archive(
            profile=profile,
            manifest=manifest,
            install_plan=install_plan,
            include_files=include_files,
            include_browser=include_browser,
            include_dev_env=include_dev_env,
            include_credentials=include_credentials,
        )

        # 5. 生成迁移码
        migration_code = generate_migration_code(
            length=config.transfer.migration_code_length
        )

        # 6. 加密
        logger.info("正在加密迁移包...")
        encrypted_data = encrypt_data(tar_data, migration_code)

        # 7. 保存到文件
        if output_path is None:
            data_dir = Path(config.data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(
                data_dir / f"migration_{manifest['package_id']}.etpkg"
            )

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(encrypted_data)

        logger.info(
            "迁移包已保存: %s (%.1f MB)",
            output_path,
            len(encrypted_data) / (1024 * 1024),
        )

        # 8. 构建结果
        package_info = MigrationPackageInfo(
            package_id=manifest["package_id"],
            migration_code=migration_code,
            package_size_bytes=len(encrypted_data),
            item_count=_count_items(manifest),
            storage_mode=StorageMode(output_mode),
            storage_path=output_path,
            expires_at=datetime.now()
            + timedelta(hours=config.transfer.migration_code_expiry_hours),
            encryption_info="AES-256-GCM with PBKDF2 key derivation",
        )

        logger.info(
            "打包完成: code=%s, size=%.1f MB, items=%d",
            migration_code,
            package_info.package_size_bytes / (1024 * 1024),
            package_info.item_count,
        )

        return package_info

    except PackageError:
        raise
    except Exception as e:
        raise PackageError(f"打包失败: {e}") from e


def _build_install_plan(
    profile: EnvironmentProfile,
    analysis: MigrationAnalysis,
) -> dict:
    """构建安装计划（install_plan.json 的内容）。"""
    from easytransfer.planner.plan_builder import build_plan, plan_to_dict

    plan = build_plan(
        profile=profile,
        analysis=analysis,
        include_files=True,
        include_browser=True,
        include_dev_env=True,
        include_credentials=False,
    )
    return plan_to_dict(plan)


def _create_tar_archive(
    profile: EnvironmentProfile,
    manifest: dict,
    install_plan: dict,
    include_files: bool = True,
    include_browser: bool = True,
    include_dev_env: bool = True,
    include_credentials: bool = False,
) -> bytes:
    """创建 tar.gz 归档。

    将 manifest.json、install_plan.json 和配置数据打包。
    """
    buf = io.BytesIO()

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # 1. manifest.json
        manifest_data = serialize_manifest(manifest)
        _add_bytes_to_tar(tar, "manifest.json", manifest_data)

        # 2. install_plan.json
        plan_data = json.dumps(
            install_plan, ensure_ascii=False, indent=2, default=str
        ).encode("utf-8")
        _add_bytes_to_tar(tar, "install_plan.json", plan_data)

        # 3. 应用配置数据
        profile_data = json.dumps(
            asdict(profile), ensure_ascii=False, indent=2, default=str
        ).encode("utf-8")
        _add_bytes_to_tar(tar, "profile.json", profile_data)

        # 4. 收集实际配置文件（如果存在）
        _collect_config_files(tar, profile)

        # 5. 收集开发环境配置文件
        if include_dev_env:
            _collect_dev_config_files(tar, profile)

    return buf.getvalue()


def _add_bytes_to_tar(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    """向 tar 归档添加内存中的数据。"""
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def _collect_config_files(
    tar: tarfile.TarFile,
    profile: EnvironmentProfile,
) -> None:
    """收集应用配置文件到归档中。"""
    for config in profile.app_configs:
        path = Path(config.config_path)
        if path.exists() and path.is_file():
            try:
                arcname = f"apps/{config.app_name}/{path.name}"
                tar.add(str(path), arcname=arcname)
            except (PermissionError, OSError) as e:
                logger.warning("无法添加配置文件 %s: %s", path, e)


def _collect_dev_config_files(
    tar: tarfile.TarFile,
    profile: EnvironmentProfile,
) -> None:
    """收集开发环境配置文件到归档中。"""
    for dev in profile.dev_environments:
        for cfg_file in dev.config_files:
            path = Path(cfg_file)
            if path.exists() and path.is_file():
                try:
                    arcname = f"dev/{dev.name}/{path.name}"
                    tar.add(str(path), arcname=arcname)
                except (PermissionError, OSError) as e:
                    logger.warning("无法添加开发配置 %s: %s", path, e)


def _count_items(manifest: dict) -> int:
    """计算迁移包中的项目总数。"""
    contents = manifest.get("contents", {})
    return sum(contents.values())


def serialize_manifest(manifest: dict) -> bytes:
    """序列化 manifest 为 JSON 字节。"""
    return json.dumps(
        manifest, ensure_ascii=False, indent=2, default=str
    ).encode("utf-8")


from dataclasses import asdict  # noqa: E402
