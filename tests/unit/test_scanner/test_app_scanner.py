"""scanner/app_scanner.py 的单元测试。"""

import pytest

from easytransfer.scanner.app_scanner import InstalledAppScanner


class TestWingetParsing:
    """winget 输出解析测试。"""

    def test_parse_standard_output(self):
        output = """Name                             Id                                   Version
------------------------------------------------------------------------------------------
Google Chrome                    Google.Chrome                        122.0.6261.112
Visual Studio Code               Microsoft.VisualStudioCode           1.87.0
Git                              Git.Git                              2.44.0
7-Zip                            7zip.7zip                            24.01
"""
        mapping = InstalledAppScanner._parse_winget_output(output)
        assert mapping.get("Google Chrome") == "Google.Chrome"
        assert mapping.get("Visual Studio Code") == "Microsoft.VisualStudioCode"
        assert mapping.get("Git") == "Git.Git"
        assert mapping.get("7-Zip") == "7zip.7zip"

    def test_parse_empty_output(self):
        mapping = InstalledAppScanner._parse_winget_output("")
        assert mapping == {}

    def test_parse_no_separator(self):
        output = "Name Id Version\nSomeApp Some.App 1.0"
        mapping = InstalledAppScanner._parse_winget_output(output)
        assert mapping == {}


class TestSystemAppFilter:
    """系统应用过滤测试。"""

    def test_skip_windows_updates(self):
        assert InstalledAppScanner._is_system_app("Security Update for Windows", "KB12345")

    def test_skip_kb_patches(self):
        assert InstalledAppScanner._is_system_app("Something", "KB5034441")

    def test_skip_vc_runtime(self):
        assert InstalledAppScanner._is_system_app(
            "Microsoft Visual C++ 2019 Redistributable", "vc_redist"
        )

    def test_keep_normal_apps(self):
        assert not InstalledAppScanner._is_system_app("Google Chrome", "Google Chrome")

    def test_keep_vscode(self):
        assert not InstalledAppScanner._is_system_app(
            "Microsoft Visual Studio Code", "{some-guid}"
        )


class TestInstalledAppScannerIntegration:
    """集成测试 — 在真实环境上运行。"""

    @pytest.mark.asyncio
    async def test_scan_finds_some_apps(self):
        """在真实 Windows 上应该至少发现一些应用。"""
        scanner = InstalledAppScanner(skip_system_apps=True)
        result = await scanner.scan()
        assert result.success is True
        assert result.items_found > 0
        assert "apps" in result.data
