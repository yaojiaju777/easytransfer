"""迁移包解包器。

解密并解包 .etpkg 文件。

解包流程：
1. 读取加密的 .etpkg 文件
2. 使用迁移码解密
3. 解压 tar.gz
4. 解析 manifest.json
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

from easytransfer.core.errors import DecryptionError, PackageError
from easytransfer.core.logging import get_logger
from easytransfer.packager.manifest import parse_manifest
from easytransfer.security.crypto import decrypt_data

logger = get_logger(__name__)


class UnpackResult:
    """解包结果。"""

    def __init__(
        self,
        manifest: dict,
        install_plan: dict | None,
        extract_dir: Path,
    ):
        self.manifest = manifest
        self.install_plan = install_plan
        self.extract_dir = extract_dir


async def unpack_migration(
    package_path: str,
    migration_code: str,
    extract_dir: str | None = None,
    iterations: int | None = None,
) -> UnpackResult:
    """解密并解包迁移包。

    Args:
        package_path: .etpkg 文件路径。
        migration_code: 6 位迁移码。
        extract_dir: 解压目标目录，默认为包文件同目录下的子目录。
        iterations: PBKDF2 迭代次数（测试时可用较小值）。

    Returns:
        解包结果，包含清单和解压目录。

    Raises:
        PackageError: 包文件不存在或格式错误。
        DecryptionError: 迁移码错误或数据损坏。
    """
    pkg_path = Path(package_path)
    if not pkg_path.exists():
        raise PackageError(f"迁移包文件不存在: {package_path}")

    logger.info("开始解包: %s", package_path)

    # 1. 读取加密数据
    encrypted_data = pkg_path.read_bytes()

    # 2. 解密
    logger.info("正在解密...")
    tar_data = decrypt_data(encrypted_data, migration_code, iterations=iterations)

    # 3. 确定解压目录
    if extract_dir is None:
        extract_path = pkg_path.parent / f"migration_{pkg_path.stem}"
    else:
        extract_path = Path(extract_dir)

    extract_path.mkdir(parents=True, exist_ok=True)

    # 4. 解压 tar.gz
    logger.info("正在解压到 %s...", extract_path)
    manifest = None
    install_plan = None

    try:
        with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:gz") as tar:
            # 安全检查：防止路径遍历攻击
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    raise PackageError(
                        f"迁移包包含不安全的路径: {member.name}"
                    )

            tar.extractall(path=str(extract_path))

            # 读取 manifest
            manifest_path = extract_path / "manifest.json"
            if manifest_path.exists():
                manifest = parse_manifest(manifest_path.read_bytes())
            else:
                raise PackageError("迁移包缺少 manifest.json")

            # 读取 install_plan（可选）
            plan_path = extract_path / "install_plan.json"
            if plan_path.exists():
                import json

                install_plan = json.loads(
                    plan_path.read_text(encoding="utf-8")
                )

    except (tarfile.TarError, OSError) as e:
        raise PackageError(f"解压失败: {e}") from e

    logger.info(
        "解包完成: package_id=%s, items=%s",
        manifest.get("package_id", "unknown"),
        manifest.get("contents", {}),
    )

    return UnpackResult(
        manifest=manifest,
        install_plan=install_plan,
        extract_dir=extract_path,
    )


async def unpack_migration_to_memory(
    encrypted_data: bytes,
    migration_code: str,
    iterations: int | None = None,
) -> tuple[dict, bytes]:
    """解密迁移包到内存（不写入磁盘）。

    用于快速验证迁移码是否正确，或在内存中处理数据。

    Args:
        encrypted_data: 加密的 .etpkg 数据。
        migration_code: 6 位迁移码。
        iterations: PBKDF2 迭代次数。

    Returns:
        (manifest字典, tar.gz数据) 的元组。

    Raises:
        DecryptionError: 迁移码错误或数据损坏。
    """
    tar_data = decrypt_data(encrypted_data, migration_code, iterations=iterations)

    # 从 tar 中提取 manifest
    manifest = None
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "manifest.json":
                    f = tar.extractfile(member)
                    if f:
                        manifest = parse_manifest(f.read())
                    break
    except tarfile.TarError as e:
        raise PackageError(f"tar 解析失败: {e}") from e

    if manifest is None:
        raise PackageError("迁移包缺少 manifest.json")

    return manifest, tar_data
