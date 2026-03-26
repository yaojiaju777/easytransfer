"""Git/SSH 配置扫描器。

扫描 Git 全局配置和 SSH 密钥（仅元数据，不读取密钥内容）。
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from easytransfer.core.logging import get_logger
from easytransfer.core.models import CredentialInfo, DevEnvInfo, Priority, ScanResult
from easytransfer.scanner.base import BaseScanner

logger = get_logger(__name__)

_USER_HOME = Path.home()


class GitSshScanner(BaseScanner):
    """扫描 Git 配置和 SSH 密钥。

    Git 配置文件直接收集，SSH 密钥只收集元数据
    （文件名、类型），不读取密钥内容。
    """

    name = "git_ssh"
    description = "扫描 Git 配置和 SSH 密钥"
    priority = Priority.P0

    async def _scan(self) -> ScanResult:
        """扫描 Git 和 SSH 配置。"""
        git_configs = self._scan_git_config()
        ssh_keys = self._scan_ssh_keys()

        return ScanResult(
            success=True,
            items_found=len(git_configs) + len(ssh_keys),
            data={
                "git_configs": [asdict(g) for g in git_configs],
                "ssh_keys": [asdict(k) for k in ssh_keys],
            },
        )

    def _scan_git_config(self) -> list[DevEnvInfo]:
        """扫描 Git 全局配置。"""
        configs: list[DevEnvInfo] = []

        gitconfig = _USER_HOME / ".gitconfig"
        if gitconfig.exists():
            config_files = [str(gitconfig)]

            # 也检查 .gitignore_global
            gitignore = _USER_HOME / ".gitignore_global"
            if gitignore.exists():
                config_files.append(str(gitignore))

            configs.append(
                DevEnvInfo(
                    name="Git Config",
                    version="",
                    config_files=config_files,
                )
            )
            logger.info("发现 Git 配置: %s", config_files)

        return configs

    def _scan_ssh_keys(self) -> list[CredentialInfo]:
        """扫描 SSH 密钥（仅元数据）。"""
        ssh_dir = _USER_HOME / ".ssh"
        if not ssh_dir.exists():
            return []

        keys: list[CredentialInfo] = []

        # 常见的 SSH 密钥文件名
        key_patterns = [
            "id_rsa",
            "id_ed25519",
            "id_ecdsa",
            "id_dsa",
        ]

        for pattern in key_patterns:
            private_key = ssh_dir / pattern
            public_key = ssh_dir / f"{pattern}.pub"

            if private_key.exists():
                keys.append(
                    CredentialInfo(
                        credential_type="ssh_key",
                        name=pattern,
                        path=str(private_key),
                        description=f"SSH 私钥 ({pattern})" + (
                            " + 公钥" if public_key.exists() else ""
                        ),
                    )
                )

        # SSH config 文件
        ssh_config = ssh_dir / "config"
        if ssh_config.exists():
            keys.append(
                CredentialInfo(
                    credential_type="ssh_config",
                    name="config",
                    path=str(ssh_config),
                    description="SSH 配置文件",
                )
            )

        # known_hosts
        known_hosts = ssh_dir / "known_hosts"
        if known_hosts.exists():
            keys.append(
                CredentialInfo(
                    credential_type="ssh_known_hosts",
                    name="known_hosts",
                    path=str(known_hosts),
                    description="SSH 已知主机列表",
                )
            )

        if keys:
            logger.info("发现 %d 个 SSH 相关文件", len(keys))

        return keys
