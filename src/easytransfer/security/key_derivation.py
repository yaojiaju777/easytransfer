"""密钥派生模块。

使用 PBKDF2-HMAC-SHA256 从 6 位迁移码派生 AES-256 加密密钥。
"""

from __future__ import annotations

import os
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from easytransfer.core.config import SecurityConfig
from easytransfer.core.errors import InvalidMigrationCodeError

# 默认配置
_DEFAULT_CONFIG = SecurityConfig()

# 盐长度（字节）
SALT_LENGTH = 16

# 密钥长度（字节），256 位
KEY_LENGTH = 32


def generate_migration_code(length: int = 6) -> str:
    """生成随机迁移码。

    使用 secrets.randbelow 生成密码学安全的随机数字。

    Args:
        length: 迁移码长度，默认 6 位。

    Returns:
        指定长度的数字字符串。
    """
    digits = "".join(str(secrets.randbelow(10)) for _ in range(length))
    return digits


def validate_migration_code(code: str, length: int = 6) -> None:
    """验证迁移码格式。

    Args:
        code: 待验证的迁移码。
        length: 预期长度。

    Raises:
        InvalidMigrationCodeError: 迁移码格式无效。
    """
    if not code:
        raise InvalidMigrationCodeError("迁移码不能为空")
    if not code.isdigit():
        raise InvalidMigrationCodeError("迁移码必须为纯数字")
    if len(code) != length:
        raise InvalidMigrationCodeError(
            f"迁移码必须为 {length} 位，当前为 {len(code)} 位"
        )


def generate_salt() -> bytes:
    """生成随机盐。

    Returns:
        16 字节的随机盐。
    """
    return os.urandom(SALT_LENGTH)


def derive_key(
    migration_code: str,
    salt: bytes,
    iterations: int | None = None,
) -> bytes:
    """从迁移码派生加密密钥。

    使用 PBKDF2-HMAC-SHA256 算法。

    Args:
        migration_code: 6 位迁移码。
        salt: 随机盐。
        iterations: PBKDF2 迭代次数，默认使用配置值。

    Returns:
        32 字节（256 位）的加密密钥。
    """
    if iterations is None:
        iterations = _DEFAULT_CONFIG.pbkdf2_iterations

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
    )

    return kdf.derive(migration_code.encode("utf-8"))
