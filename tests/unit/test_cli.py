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
        assert "扫描" in result.output or "Mock" in result.output

    def test_scan_with_scope(self):
        result = runner.invoke(app, ["scan", "--scope", "apps_only"])
        assert result.exit_code == 0

    def test_package_command(self):
        result = runner.invoke(app, ["package"])
        assert result.exit_code == 0
        assert "迁移码" in result.output or "123456" in result.output

    def test_restore_requires_code_or_path(self):
        result = runner.invoke(app, ["restore"])
        assert result.exit_code == 1

    def test_restore_with_code(self):
        result = runner.invoke(app, ["restore", "--code", "123456"])
        assert result.exit_code == 0

    def test_restore_with_package_path(self):
        result = runner.invoke(app, ["restore", "--package", "/tmp/test.etpkg"])
        assert result.exit_code == 0

    def test_verify_command(self):
        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 0
