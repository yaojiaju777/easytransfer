"""加密/解密模块的单元测试。"""

import pytest

from easytransfer.core.errors import DecryptionError
from easytransfer.security.crypto import (
    HEADER_LENGTH,
    decrypt_data,
    encrypt_data,
)

# 使用较少的迭代次数加速测试
_TEST_ITERATIONS = 1000


class TestEncryptDecryptRoundtrip:
    """加密解密往返测试。"""

    def test_basic_roundtrip(self):
        plaintext = b"Hello, EasyTransfer!"
        code = "123456"

        encrypted = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)
        decrypted = decrypt_data(encrypted, code, iterations=_TEST_ITERATIONS)

        assert decrypted == plaintext

    def test_empty_data(self):
        plaintext = b""
        code = "000000"

        encrypted = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)
        decrypted = decrypt_data(encrypted, code, iterations=_TEST_ITERATIONS)

        assert decrypted == plaintext

    def test_large_data(self):
        plaintext = b"x" * (1024 * 1024)  # 1 MB
        code = "999999"

        encrypted = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)
        decrypted = decrypt_data(encrypted, code, iterations=_TEST_ITERATIONS)

        assert decrypted == plaintext

    def test_binary_data(self):
        plaintext = bytes(range(256)) * 100
        code = "112233"

        encrypted = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)
        decrypted = decrypt_data(encrypted, code, iterations=_TEST_ITERATIONS)

        assert decrypted == plaintext

    def test_encrypted_size_larger(self):
        """加密数据应该比原始数据大（包含头部）。"""
        plaintext = b"test data"
        encrypted = encrypt_data(plaintext, "123456", iterations=_TEST_ITERATIONS)

        assert len(encrypted) > len(plaintext)
        assert len(encrypted) >= HEADER_LENGTH + len(plaintext)


class TestDecryptionErrors:
    """解密错误处理测试。"""

    def test_wrong_code(self):
        plaintext = b"secret data"
        encrypted = encrypt_data(plaintext, "123456", iterations=_TEST_ITERATIONS)

        with pytest.raises(DecryptionError):
            decrypt_data(encrypted, "654321", iterations=_TEST_ITERATIONS)

    def test_truncated_data(self):
        with pytest.raises(DecryptionError, match="过短"):
            decrypt_data(b"short", "123456", iterations=_TEST_ITERATIONS)

    def test_corrupted_data(self):
        plaintext = b"secret data"
        encrypted = encrypt_data(plaintext, "123456", iterations=_TEST_ITERATIONS)

        # 修改加密数据中的一个字节
        corrupted = bytearray(encrypted)
        corrupted[-1] ^= 0xFF
        corrupted = bytes(corrupted)

        with pytest.raises(DecryptionError):
            decrypt_data(corrupted, "123456", iterations=_TEST_ITERATIONS)

    def test_header_only(self):
        """仅有头部、无密文的数据。"""
        # 创建恰好 HEADER_LENGTH 长的数据
        fake_data = b"\x00" * HEADER_LENGTH
        with pytest.raises(DecryptionError):
            decrypt_data(fake_data, "123456", iterations=_TEST_ITERATIONS)


class TestEncryptionFormat:
    """加密数据格式测试。"""

    def test_header_structure(self):
        """验证加密后的数据包含 salt + nonce + tag 头部。"""
        encrypted = encrypt_data(b"test", "123456", iterations=_TEST_ITERATIONS)
        assert len(encrypted) >= HEADER_LENGTH

        # salt: 16 bytes, nonce: 12 bytes, tag: 16 bytes
        salt = encrypted[:16]
        nonce = encrypted[16:28]
        tag = encrypted[28:44]

        assert len(salt) == 16
        assert len(nonce) == 12
        assert len(tag) == 16

    def test_different_encryptions_different_output(self):
        """相同输入的两次加密应产生不同输出（因为随机 salt 和 nonce）。"""
        plaintext = b"same data"
        code = "123456"

        enc1 = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)
        enc2 = encrypt_data(plaintext, code, iterations=_TEST_ITERATIONS)

        assert enc1 != enc2
