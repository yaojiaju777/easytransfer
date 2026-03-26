"""开发环境扫描器。

检测已安装的开发运行时和工具：
Python, Node.js, Java, Go, Rust 等。
"""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import asdict

from easytransfer.core.logging import get_logger
from easytransfer.core.models import DevEnvInfo, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

# 要检测的运行时命令
# (name, version_cmd, version_args, package_list_cmd)
_RUNTIMES = [
    {
        "name": "Python",
        "cmd": "python",
        "version_args": ["--version"],
        "packages_cmd": ["pip", "list", "--format=freeze"],
    },
    {
        "name": "Node.js",
        "cmd": "node",
        "version_args": ["--version"],
        "packages_cmd": ["npm", "list", "-g", "--depth=0"],
    },
    {
        "name": "Git",
        "cmd": "git",
        "version_args": ["--version"],
        "packages_cmd": None,
    },
    {
        "name": "Java",
        "cmd": "java",
        "version_args": ["--version"],
        "packages_cmd": None,
    },
    {
        "name": "Go",
        "cmd": "go",
        "version_args": ["version"],
        "packages_cmd": None,
    },
    {
        "name": "Rust",
        "cmd": "rustc",
        "version_args": ["--version"],
        "packages_cmd": ["cargo", "install", "--list"],
    },
    {
        "name": "Docker",
        "cmd": "docker",
        "version_args": ["--version"],
        "packages_cmd": None,
    },
]


class DevEnvScanner(BaseScanner):
    """扫描开发环境。

    检测 PATH 中的开发运行时，获取版本号和已安装的全局包。
    """

    name = "dev_environment"
    description = "扫描开发环境和运行时"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        """扫描所有运行时。"""
        envs: list[DevEnvInfo] = []

        for runtime in _RUNTIMES:
            env = await self._detect_runtime(runtime)
            if env:
                envs.append(env)

        return ScanResult(
            success=True,
            items_found=len(envs),
            data={"dev_environments": [asdict(e) for e in envs]},
        )

    async def _detect_runtime(self, runtime: dict) -> DevEnvInfo | None:
        """检测单个运行时。"""
        cmd = runtime["cmd"]
        version_args = runtime["version_args"]

        # 检测版本
        version = await self._run_cmd([cmd] + version_args)
        if version is None:
            return None

        # 获取安装路径
        install_path = await self._get_install_path(cmd)

        # 获取全局包
        packages: list[str] = []
        if runtime.get("packages_cmd"):
            pkg_output = await self._run_cmd(runtime["packages_cmd"])
            if pkg_output:
                packages = self._parse_packages(runtime["name"], pkg_output)

        env = DevEnvInfo(
            name=runtime["name"],
            version=version.strip(),
            install_path=install_path or "",
            global_packages=packages,
        )

        logger.info("检测到 %s: %s (%d 个全局包)", env.name, env.version, len(packages))
        return env

    async def _run_cmd(self, cmd: list[str]) -> str | None:
        """安全执行命令并返回输出。"""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
            # 有些命令（如 java --version）输出到 stderr
            output = result.stdout or result.stderr
            return output.strip() if output else None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None

    async def _get_install_path(self, cmd: str) -> str | None:
        """获取命令的安装路径。"""
        result = await self._run_cmd(["where", cmd])
        if result:
            return result.split("\n")[0].strip()
        return None

    @staticmethod
    def _parse_packages(runtime_name: str, output: str) -> list[str]:
        """解析包列表输出。"""
        packages = []

        if runtime_name == "Python":
            # pip freeze 格式: package==version
            for line in output.split("\n"):
                line = line.strip()
                if "==" in line:
                    pkg_name = line.split("==")[0]
                    packages.append(pkg_name)

        elif runtime_name == "Node.js":
            # npm list -g 格式: +-- package@version
            for line in output.split("\n"):
                line = line.strip()
                if "@" in line and ("──" in line or "+--" in line):
                    # 取 "── package@version" 中的包名
                    pkg_part = line.split("── ")[-1] if "── " in line else line.split("+-- ")[-1]
                    pkg_name = pkg_part.split("@")[0]
                    if pkg_name:
                        packages.append(pkg_name)

        elif runtime_name == "Rust":
            # cargo install --list 格式: package v0.1.0:
            for line in output.split("\n"):
                line = line.strip()
                if line and not line.startswith(" ") and " v" in line:
                    pkg_name = line.split(" v")[0]
                    packages.append(pkg_name)

        return packages
