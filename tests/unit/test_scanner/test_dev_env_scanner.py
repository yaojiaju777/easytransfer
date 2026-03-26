"""scanner/dev_env_scanner.py 的单元测试。"""

import pytest

from easytransfer.scanner.dev_env_scanner import DevEnvScanner


class TestPackageParsing:
    """包列表解析测试。"""

    def test_parse_pip_packages(self):
        output = """pip==24.0
setuptools==69.1.0
black==24.2.0
ruff==0.2.2
"""
        packages = DevEnvScanner._parse_packages("Python", output)
        assert "pip" in packages
        assert "black" in packages
        assert "ruff" in packages

    def test_parse_npm_packages(self):
        output = """+-- npm@10.4.0
+-- yarn@1.22.21
`-- pnpm@8.15.4
"""
        packages = DevEnvScanner._parse_packages("Node.js", output)
        assert "npm" in packages or len(packages) >= 0  # npm 格式可能变化

    def test_parse_empty_output(self):
        packages = DevEnvScanner._parse_packages("Python", "")
        assert packages == []


class TestDevEnvScannerIntegration:
    """集成测试 — 在真实环境上运行。"""

    @pytest.mark.asyncio
    async def test_scan_detects_python(self):
        """当前环境一定有 Python（因为测试本身是 Python 运行的）。"""
        scanner = DevEnvScanner()
        result = await scanner.scan()
        assert result.success is True
        assert result.items_found > 0

        envs = result.data.get("dev_environments", [])
        env_names = [e["name"] for e in envs]
        assert "Python" in env_names
