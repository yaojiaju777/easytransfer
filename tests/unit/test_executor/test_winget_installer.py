"""Winget 安装器测试。

使用 mock subprocess 测试，不实际运行 winget。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import subprocess

import pytest

from easytransfer.core.errors import InstallError
from easytransfer.executor.installers.winget_installer import WingetInstaller


class TestWingetInstaller:
    """WingetInstaller 测试。"""

    def test_build_install_command(self):
        """构建安装命令。"""
        cmd = WingetInstaller.build_install_command("Google.Chrome")
        assert "winget install" in cmd
        assert "--id Google.Chrome" in cmd
        assert "--accept-source-agreements" in cmd
        assert "--accept-package-agreements" in cmd

    @pytest.mark.asyncio
    async def test_install_dry_run(self):
        """dry-run 模式不执行。"""
        installer = WingetInstaller(dry_run=True)
        await installer.install("Google.Chrome")
        # 不应抛出异常

    @pytest.mark.asyncio
    async def test_install_empty_id_raises(self):
        """空 winget_id 应抛出 InstallError。"""
        installer = WingetInstaller()

        with pytest.raises(InstallError):
            await installer.install("")

    @pytest.mark.asyncio
    async def test_install_success(self):
        """模拟 winget 安装成功。"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully installed"
        mock_result.stderr = ""

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            await installer.install("Google.Chrome")

    @pytest.mark.asyncio
    async def test_install_failure(self):
        """模拟 winget 安装失败。"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Package not found"

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            with pytest.raises(InstallError, match="winget 安装失败"):
                await installer.install("Invalid.Package")

    @pytest.mark.asyncio
    async def test_install_timeout(self):
        """模拟安装超时。"""
        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=subprocess.TimeoutExpired(cmd="winget", timeout=600),
        ):
            installer = WingetInstaller()
            with pytest.raises(InstallError, match="安装超时"):
                await installer.install("Slow.Package")

    @pytest.mark.asyncio
    async def test_install_os_error(self):
        """模拟 winget 不存在。"""
        with patch(
            "asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=OSError("winget not found"),
        ):
            installer = WingetInstaller()
            with pytest.raises(InstallError, match="无法执行 winget"):
                await installer.install("Google.Chrome")

    @pytest.mark.asyncio
    async def test_uninstall_dry_run(self):
        """dry-run 模式卸载不执行。"""
        installer = WingetInstaller(dry_run=True)
        await installer.uninstall("Google.Chrome")

    @pytest.mark.asyncio
    async def test_uninstall_empty_id_raises(self):
        """空 winget_id 应抛出 InstallError。"""
        installer = WingetInstaller()

        with pytest.raises(InstallError):
            await installer.uninstall("")

    @pytest.mark.asyncio
    async def test_uninstall_success(self):
        """模拟 winget 卸载成功。"""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            await installer.uninstall("Google.Chrome")

    @pytest.mark.asyncio
    async def test_is_installed_dry_run(self):
        """dry-run 模式下检查安装状态应返回 False。"""
        installer = WingetInstaller(dry_run=True)
        result = await installer.is_installed("Google.Chrome")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_installed_true(self):
        """模拟应用已安装。"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Google.Chrome  122.0  winget"

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            result = await installer.is_installed("Google.Chrome")
            assert result is True

    @pytest.mark.asyncio
    async def test_is_installed_false(self):
        """模拟应用未安装。"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            result = await installer.is_installed("Missing.App")
            assert result is False

    @pytest.mark.asyncio
    async def test_install_with_custom_command(self):
        """使用自定义命令安装。"""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=mock_result):
            installer = WingetInstaller()
            await installer.install(
                "Custom.App",
                command="winget install --id Custom.App --silent",
            )
