"""文件恢复器测试。

使用临时目录测试用户文件恢复逻辑。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from easytransfer.core.errors import RestoreError
from easytransfer.executor.restorers.file_restorer import FileRestorer


@pytest.fixture
def extract_dir():
    """模拟解包目录。"""
    with tempfile.TemporaryDirectory() as d:
        extract = Path(d) / "extract"
        extract.mkdir()
        files = extract / "files"
        files.mkdir()
        (files / "readme.txt").write_text("Hello from migration")
        # 子目录
        docs = files / "Documents"
        docs.mkdir()
        (docs / "report.docx").write_bytes(b"fake-docx-content")
        (docs / "notes.txt").write_text("important notes")
        yield extract


@pytest.fixture
def target_dir():
    """模拟目标目录。"""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestFileRestorer:
    """FileRestorer 测试。"""

    @pytest.mark.asyncio
    async def test_restore_single_file(self, extract_dir, target_dir):
        """恢复单个文件。"""
        restorer = FileRestorer(extract_dir=extract_dir)
        target = str(target_dir / "readme.txt")

        backup = await restorer.restore(
            source_path="files/readme.txt",
            target_path=target,
        )

        assert Path(target).exists()
        assert Path(target).read_text() == "Hello from migration"
        assert backup == ""

    @pytest.mark.asyncio
    async def test_restore_directory(self, extract_dir, target_dir):
        """恢复整个目录。"""
        restorer = FileRestorer(extract_dir=extract_dir)
        target = str(target_dir / "MyDocs")

        await restorer.restore(
            source_path="files/Documents",
            target_path=target,
        )

        assert Path(target).is_dir()
        assert (Path(target) / "report.docx").exists()
        assert (Path(target) / "notes.txt").read_text() == "important notes"

    @pytest.mark.asyncio
    async def test_restore_backs_up_existing(self, extract_dir, target_dir):
        """恢复时备份已存在的文件。"""
        target = target_dir / "readme.txt"
        target.write_text("old content")

        restorer = FileRestorer(extract_dir=extract_dir)
        backup = await restorer.restore(
            source_path="files/readme.txt",
            target_path=str(target),
        )

        assert target.read_text() == "Hello from migration"
        assert backup != ""
        assert Path(backup).exists()
        assert Path(backup).read_text() == "old content"

    @pytest.mark.asyncio
    async def test_restore_creates_parent_dirs(self, extract_dir, target_dir):
        """恢复时创建不存在的父目录。"""
        restorer = FileRestorer(extract_dir=extract_dir)
        target = str(target_dir / "deep" / "path" / "readme.txt")

        await restorer.restore(
            source_path="files/readme.txt",
            target_path=target,
        )

        assert Path(target).exists()

    @pytest.mark.asyncio
    async def test_dry_run(self, extract_dir, target_dir):
        """dry-run 模式不写入。"""
        restorer = FileRestorer(extract_dir=extract_dir, dry_run=True)
        target = str(target_dir / "readme.txt")

        await restorer.restore(
            source_path="files/readme.txt",
            target_path=target,
        )

        assert not Path(target).exists()

    @pytest.mark.asyncio
    async def test_source_not_found(self, extract_dir, target_dir):
        """源文件不存在应抛出错误。"""
        restorer = FileRestorer(extract_dir=extract_dir)

        with pytest.raises(RestoreError):
            await restorer.restore(
                source_path="files/nonexistent.txt",
                target_path=str(target_dir / "out.txt"),
            )

    @pytest.mark.asyncio
    async def test_empty_source_path(self, extract_dir, target_dir):
        """空 source_path 应抛出错误。"""
        restorer = FileRestorer(extract_dir=extract_dir)

        with pytest.raises(RestoreError):
            await restorer.restore(
                source_path="",
                target_path=str(target_dir / "out.txt"),
            )
