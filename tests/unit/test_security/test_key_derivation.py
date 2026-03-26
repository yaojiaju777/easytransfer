"""密钥派生模块的单元测试。"""

import pytest

from easytransfer.core.errors import InvalidMigrationCodeError
from easytransfer.security.key_derivation import (
    KEY_LENGTH,
    SALT_LENGTH,
    derive_key,
    generate_migration_code,
    generate_salt,
    validate_migration_code,
)


class TestGenerateMigrationCode:
    """迁移码生成测试。"""

    def test_default_length(self):
        code = generate_migration_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_custom_length(self):
        code = generate_migration_code(length=8)
        assert len(code) == 8
        assert code.isdigit()

    def test_randomness(self):
        """生成多个码确保不完全相同。"""
        codes = {generate_migration_code() for _ in range(20)}
        # 20 次生成至少有 2 个不同的值
        assert len(codes) > 1


class TestValidateMigrationCode:
    """迁移码验证测试。"""

    def test_valid_code(self):
        validate_migration_code("123456")  # 不应抛出异常

    def test_empty_code(self):
        with pytest.raises(InvalidMigrationCodeError, match="不能为空"):
            validate_migration_code("")

    def test_non_digit(self):
        with pytest.raises(InvalidMigrationCodeError, match="纯数字"):
            validate_migration_code("abcdef")

    def test_wrong_length(self):
        with pytest.raises(InvalidMigrationCodeError, match="6 位"):
            validate_migration_code("12345")

    def test_too_long(self):
        with pytest.raises(InvalidMigrationCodeError, match="6 位"):
            validate_migration_code("1234567")


class TestGenerateSalt:
    """盐生成测试。"""

    def test_salt_length(self):
        salt = generate_salt()
        assert len(salt) == SALT_LENGTH

    def test_salt_randomness(self):
        salts = {generate_salt() for _ in range(10)}
        assert len(salts) > 1


class TestDeriveKey:
    """密钥派生测试。"""

    def test_key_length(self):
        salt = generate_salt()
        key = derive_key("123456", salt, iterations=1000)
        assert len(key) == KEY_LENGTH

    def test_deterministic(self):
        """同样的输入应产生同样的密钥。"""
        salt = b"\x00" * SALT_LENGTH
        key1 = derive_key("123456", salt, iterations=1000)
        key2 = derive_key("123456", salt, iterations=1000)
        assert key1 == key2

    def test_different_codes_different_keys(self):
        salt = b"\x00" * SALT_LENGTH
        key1 = derive_key("123456", salt, iterations=1000)
        key2 = derive_key("654321", salt, iterations=1000)
        assert key1 != key2

    def test_different_salts_different_keys(self):
        salt1 = b"\x00" * SALT_LENGTH
        salt2 = b"\x01" * SALT_LENGTH
        key1 = derive_key("123456", salt1, iterations=1000)
        key2 = derive_key("123456", salt2, iterations=1000)
        assert key1 != key2
