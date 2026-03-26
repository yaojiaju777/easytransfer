"""AES-256-GCM 加密/解密模块。

负责迁移包的加密和解密。

加密后的数据格式：
    [16 bytes salt][12 bytes nonce][16 bytes auth tag][encrypted data]
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from easytransfer.core.errors import DecryptionError, EncryptionError
from easytransfer.security.key_derivation import (
    SALT_LENGTH,
    derive_key,
    generate_salt,
)

# Nonce 长度（字节）
NONCE_LENGTH = 12

# Auth tag 长度（字节）— GCM 默认 16 字节
TAG_LENGTH = 16

# 头部总长度 = salt + nonce + tag
HEADER_LENGTH = SALT_LENGTH + NONCE_LENGTH + TAG_LENGTH


def encrypt_data(
    plaintext: bytes,
    migration_code: str,
    iterations: int | None = None,
) -> bytes:
    """使用 AES-256-GCM 加密数据。

    流程：
    1. 生成随机 salt
    2. 从迁移码 + salt 派生密钥
    3. 生成随机 nonce
    4. 用 AES-256-GCM 加密
    5. 返回 salt + nonce + tag + ciphertext

    Args:
        plaintext: 要加密的数据。
        migration_code: 6 位迁移码。
        iterations: PBKDF2 迭代次数（测试时可用较小值加速）。

    Returns:
        加密后的数据（含 salt、nonce、tag 头部）。

    Raises:
        EncryptionError: 加密失败。
    """
    try:
        salt = generate_salt()
        key = derive_key(migration_code, salt, iterations=iterations)
        nonce = os.urandom(NONCE_LENGTH)

        aesgcm = AESGCM(key)
        # AESGCM.encrypt 返回 ciphertext + tag（tag 附在末尾）
        ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)

        # 分离 ciphertext 和 tag
        # GCM tag 始终在末尾 16 字节
        ciphertext = ct_with_tag[:-TAG_LENGTH]
        tag = ct_with_tag[-TAG_LENGTH:]

        return salt + nonce + tag + ciphertext

    except Exception as e:
        if isinstance(e, EncryptionError):
            raise
        raise EncryptionError(f"加密失败: {e}") from e


def decrypt_data(
    encrypted: bytes,
    migration_code: str,
    iterations: int | None = None,
) -> bytes:
    """解密 AES-256-GCM 加密的数据。

    流程：
    1. 解析 salt、nonce、tag
    2. 从迁移码 + salt 派生密钥
    3. 用 AES-256-GCM 解密验证

    Args:
        encrypted: 加密后的数据（含头部）。
        migration_code: 6 位迁移码。
        iterations: PBKDF2 迭代次数。

    Returns:
        解密后的原始数据。

    Raises:
        DecryptionError: 解密失败（密码错误或数据损坏）。
    """
    if len(encrypted) < HEADER_LENGTH:
        raise DecryptionError("加密数据过短，格式无效")

    try:
        salt = encrypted[:SALT_LENGTH]
        nonce = encrypted[SALT_LENGTH : SALT_LENGTH + NONCE_LENGTH]
        tag = encrypted[SALT_LENGTH + NONCE_LENGTH : HEADER_LENGTH]
        ciphertext = encrypted[HEADER_LENGTH:]

        key = derive_key(migration_code, salt, iterations=iterations)

        aesgcm = AESGCM(key)
        # AESGCM.decrypt 需要 ciphertext + tag
        ct_with_tag = ciphertext + tag
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, None)

        return plaintext

    except DecryptionError:
        raise
    except Exception as e:
        raise DecryptionError(
            "解密失败，请检查迁移码是否正确", details=str(e)
        ) from e
