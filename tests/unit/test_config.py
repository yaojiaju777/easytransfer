"""core/config.py 的单元测试。"""

import json
import os

from easytransfer.core.config import (
    APP_NAME,
    VERSION,
    AppConfig,
    load_config,
    save_config,
)


class TestAppConfig:
    """AppConfig 默认值测试。"""

    def test_default_version(self):
        config = AppConfig()
        assert config.version == VERSION

    def test_default_app_name(self):
        config = AppConfig()
        assert config.app_name == APP_NAME

    def test_default_scan_config(self):
        config = AppConfig()
        assert config.scan.skip_system_apps is True
        assert config.scan.include_file_sizes is True
        assert "node_modules" in config.scan.excluded_dirs

    def test_default_package_config(self):
        config = AppConfig()
        assert config.package.chunk_size_bytes == 10 * 1024 * 1024
        assert config.package.compression_level == 6

    def test_default_transfer_config(self):
        config = AppConfig()
        assert config.transfer.max_retries == 3
        assert config.transfer.migration_code_length == 6
        assert config.transfer.migration_code_expiry_hours == 24

    def test_default_security_config(self):
        config = AppConfig()
        assert config.security.pbkdf2_iterations == 600_000
        assert config.security.encryption_algorithm == "AES-256-GCM"


class TestLoadSaveConfig:
    """配置加载和保存测试。"""

    def test_load_nonexistent_returns_defaults(self, tmp_dir):
        config = load_config(tmp_dir / "nonexistent.json")
        assert config.version == VERSION

    def test_save_and_load_roundtrip(self, tmp_dir):
        config = AppConfig()
        config.scan.max_file_scan_depth = 10
        config.transfer.max_retries = 5

        path = tmp_dir / "config.json"
        save_config(config, path)

        loaded = load_config(path)
        assert loaded.scan.max_file_scan_depth == 10
        assert loaded.transfer.max_retries == 5

    def test_load_corrupted_file_returns_defaults(self, tmp_dir):
        path = tmp_dir / "config.json"
        path.write_text("this is not json", encoding="utf-8")

        config = load_config(path)
        assert config.version == VERSION  # 应回退到默认值

    def test_env_var_override(self, tmp_dir, monkeypatch):
        monkeypatch.setenv("EASYTRANSFER_RELAY_URL", "https://relay.example.com")
        config = load_config(tmp_dir / "nonexistent.json")
        assert config.transfer.relay_server_url == "https://relay.example.com"

    def test_save_creates_parent_dirs(self, tmp_dir):
        path = tmp_dir / "sub" / "dir" / "config.json"
        save_config(AppConfig(), path)
        assert path.exists()
