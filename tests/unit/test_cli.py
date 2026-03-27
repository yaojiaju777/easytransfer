"""cli.py 的单元测试。"""

from typer.testing import CliRunner

from easytransfer.cli import app

runner = CliRunner()


class TestCLI:
    """CLI 命令测试。"""

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "EasyTransfer" in result.output

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "EasyTransfer" in result.output

    def test_scan_command(self):
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 0

    def test_scan_with_scope(self):
        result = runner.invoke(app, ["scan", "--scope", "apps_only"])
        assert result.exit_code == 0

    def test_scan_invalid_scope(self):
        result = runner.invoke(app, ["scan", "--scope", "invalid"])
        assert result.exit_code == 1

    def test_package_command(self):
        result = runner.invoke(app, ["package"])
        assert result.exit_code == 0
        assert "迁移码" in result.output or "123456" in result.output

    def test_restore_requires_code_or_path(self):
        result = runner.invoke(app, ["restore"])
        assert result.exit_code == 1

    def test_restore_with_code_no_package(self):
        """使用迁移码但不提供包路径应报错（目前仅支持本地包）。"""
        result = runner.invoke(app, ["restore", "--code", "123456"])
        assert result.exit_code == 1
        assert "恢复失败" in result.output or "package" in result.output.lower()

    def test_restore_with_nonexistent_package(self):
        """提供不存在的包路径应报错。"""
        result = runner.invoke(app, ["restore", "--package", "/tmp/nonexistent_test.etpkg", "--code", "123456"])
        assert result.exit_code == 1

    def test_restore_dry_run_flag(self):
        """dry-run flag 应可被接受。"""
        result = runner.invoke(app, ["restore", "--code", "123456", "--dry-run"])
        # 仍然会失败（无包路径），但说明 flag 被解析了
        assert result.exit_code == 1

    def test_verify_no_migration(self):
        """没有迁移记录时验证应报错。"""
        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 1
        assert "找不到" in result.output or "迁移记录" in result.output
