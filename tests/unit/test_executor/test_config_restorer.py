"""配置恢复器测试。

使用临时目录测试配置文件的恢复和备份逻辑。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from easytransfer.core.errors import RestoreError
from easytransfer.executor.restorers.config_restorer import ConfigRestorer


@pytest.fixture
def extract_dir():
    """模拟解包目录。"""
    with tempfile.TemporaryDirectory() as d:
        extract = Path(d) / "extract"
        extract.mkdir()
        configs = extract / "configs"
        configs.mkdir()
        (configs / "settings.json").write_text('{"theme": "dark"}')
        (configs / "keybindings.json").write_text('[]')
        # 嵌套目录
        nested = configs / "app" / "sub"
        nested.mkdir(parents=True)
        (nested / "config.ini").write_text("[section]\nkey=value")
        yield extract


@pytest.fixture
def target_dir():
    """模拟目标目录。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestConfigRestorer:
    """ConfigRestorer 测试。"""

    @pytest.mark.asyncio
    async def test_restore_simple_file(self, extract_dir, target_dir):
        """恢复简单配置文件。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)
        target_path = str(target_dir / "settings.json")

        backup = await restorer.restore(
            source_path="configs/settings.json",
            target_path=target_path,
        )

        assert Path(target_path).exists()
        assert Path(target_path).read_text() == '{"theme": "dark"}'
        assert backup == ""  # 没有已存在的文件，无需备份

    @pytest.mark.asyncio
    async def test_restore_creates_parent_dirs(self, extract_dir, target_dir):
        """恢复时应创建不存在的父目录。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)
        target_path = str(target_dir / "a" / "b" / "c" / "settings.json")

        await restorer.restore(
            source_path="configs/settings.json",
            target_path=target_path,
        )

        assert Path(target_path).exists()

    @pytest.mark.asyncio
    async def test_restore_backs_up_existing_file(self, extract_dir, target_dir):
        """恢复时应备份已存在的文件。"""
        target_path = target_dir / "settings.json"
        target_path.write_text('{"theme": "light"}')  # 旧文件

        restorer = ConfigRestorer(extract_dir=extract_dir)
        backup = await restorer.restore(
            source_path="configs/settings.json",
            target_path=str(target_path),
        )

        # 新文件已覆盖
        assert target_path.read_text() == '{"theme": "dark"}'
        # 备份存在
        assert backup != ""
        assert Path(backup).exists()
        assert Path(backup).read_text() == '{"theme": "light"}'

    @pytest.mark.asyncio
    async def test_restore_nested_path(self, extract_dir, target_dir):
        """恢复嵌套路径的配置。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)
        target_path = str(target_dir / "config.ini")

        await restorer.restore(
            source_path="configs/app/sub/config.ini",
            target_path=target_path,
        )

        assert Path(target_path).exists()
        assert "[section]" in Path(target_path).read_text()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_write(self, extract_dir, target_dir):
        """dry-run 模式不应写入文件。"""
        restorer = ConfigRestorer(extract_dir=extract_dir, dry_run=True)
        target_path = str(target_dir / "settings.json")

        backup = await restorer.restore(
            source_path="configs/settings.json",
            target_path=target_path,
        )

        assert not Path(target_path).exists()
        assert backup == ""

    @pytest.mark.asyncio
    async def test_source_not_found_raises(self, extract_dir, target_dir):
        """源文件不存在应抛出 RestoreError。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)

        with pytest.raises(RestoreError):
            await restorer.restore(
                source_path="configs/nonexistent.json",
                target_path=str(target_dir / "out.json"),
            )

    @pytest.mark.asyncio
    async def test_empty_source_path_raises(self, extract_dir, target_dir):
        """空 source_path 应抛出 RestoreError。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)

        with pytest.raises(RestoreError):
            await restorer.restore(
                source_path="",
                target_path=str(target_dir / "out.json"),
            )

    @pytest.mark.asyncio
    async def test_restore_directory(self, extract_dir, target_dir):
        """恢复目录结构。"""
        restorer = ConfigRestorer(extract_dir=extract_dir)
        target_path = str(target_dir / "app_config")

        await restorer.restore(
            source_path="configs/app",
            target_path=target_path,
        )

        assert Path(target_path).is_dir()
        assert (Path(target_path) / "sub" / "config.ini").exists()
