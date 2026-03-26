"""EasyTransfer CLI 界面。

使用 typer + rich 构建的命令行工具。
支持独立使用（不依赖 Agent）。

使用方式：
    python -m easytransfer --help
    python -m easytransfer scan
    python -m easytransfer package
    python -m easytransfer restore --code 123456
    python -m easytransfer verify
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from easytransfer.core.config import APP_NAME, VERSION

# CLI 应用实例
app = typer.Typer(
    name="easytransfer",
    help=f"{APP_NAME} — AI Agent 电脑换机技能包",
    add_completion=False,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold blue]{APP_NAME}[/] v{VERSION}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="显示版本号",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """EasyTransfer — Windows 电脑一键换机工具。

    既可以作为 AI Agent 的技能包使用，也可以独立运行。
    """


@app.command()
def scan(
    scope: str = typer.Option("full", help="扫描范围: full/apps_only/files_only/dev_only"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径 (JSON)"),
) -> None:
    """扫描当前电脑环境。

    扫描已安装应用、用户文件、浏览器数据、开发环境等，
    生成完整的环境画像。
    """
    console.print(
        Panel(
            f"[bold]环境扫描[/]\n\n"
            f"扫描范围: {scope}\n"
            f"输出文件: {output or '（仅显示，不保存）'}\n\n"
            f"[dim]此功能将在 M2 阶段实现。当前显示 Mock 信息。[/]",
            title=f"{APP_NAME} — 扫描",
            border_style="blue",
        )
    )

    # Mock 扫描结果展示
    table = Table(title="扫描结果预览 (Mock)")
    table.add_column("类别", style="cyan")
    table.add_column("数量", justify="right", style="green")
    table.add_column("大小", justify="right")

    table.add_row("已安装应用", "25", "8.5 GB")
    table.add_row("用户文件", "1,234 个", "5.2 GB")
    table.add_row("浏览器数据", "2 个浏览器", "350 MB")
    table.add_row("开发环境", "3 个运行时", "1.2 GB")
    table.add_row("系统配置", "15 项", "< 1 MB")

    console.print(table)
    console.print("\n[dim]提示: 真实扫描功能即将在下一个版本实现[/]")


@app.command()
def package(
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="环境画像文件路径"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="迁移包保存路径"),
    mode: str = typer.Option("local", help="存储方式: local/cloud"),
) -> None:
    """打包迁移数据。

    将扫描到的环境数据打包为加密的迁移包，
    并生成 6 位迁移码。
    """
    console.print(
        Panel(
            f"[bold]迁移打包[/]\n\n"
            f"环境画像: {profile or '（将先执行扫描）'}\n"
            f"存储方式: {mode}\n"
            f"输出路径: {output or '（默认路径）'}\n\n"
            f"[dim]此功能将在 M4 阶段实现。[/]",
            title=f"{APP_NAME} — 打包",
            border_style="yellow",
        )
    )

    console.print("\n[bold green]迁移码: 123456[/] (Mock)")
    console.print("[dim]请将此迁移码告诉新电脑上的助手[/]")


@app.command()
def restore(
    code: Optional[str] = typer.Option(None, "--code", "-c", help="6 位迁移码"),
    package_path: Optional[str] = typer.Option(None, "--package", "-p", help="本地迁移包路径"),
) -> None:
    """从迁移包恢复环境。

    在新电脑上运行，输入迁移码即可自动恢复
    旧电脑上的应用、配置和文件。
    """
    if not code and not package_path:
        console.print("[red]错误: 请提供迁移码 (--code) 或迁移包路径 (--package)[/]")
        raise typer.Exit(1)

    source = f"迁移码: {code}" if code else f"本地文件: {package_path}"
    console.print(
        Panel(
            f"[bold]迁移恢复[/]\n\n"
            f"数据来源: {source}\n\n"
            f"[dim]此功能将在 M5 阶段实现。[/]",
            title=f"{APP_NAME} — 恢复",
            border_style="green",
        )
    )


@app.command()
def verify(
    migration_id: Optional[str] = typer.Option(None, "--id", help="迁移记录 ID"),
) -> None:
    """验证迁移结果。

    检查应用安装状态、配置恢复情况和文件完整性。
    """
    console.print(
        Panel(
            f"[bold]迁移验证[/]\n\n"
            f"迁移 ID: {migration_id or '（最近一次迁移）'}\n\n"
            f"[dim]此功能将在 M5 阶段实现。[/]",
            title=f"{APP_NAME} — 验证",
            border_style="magenta",
        )
    )


@app.command()
def server() -> None:
    """启动 MCP Server 模式。

    以 MCP Server 运行，等待 AI Agent 连接和调用。
    """
    console.print(f"[bold]{APP_NAME} MCP Server[/] v{VERSION}")
    console.print("正在启动 MCP Server...")
    console.print("[dim]Agent 将通过 stdio 连接[/]\n")

    from easytransfer.mcp_server import main as run_mcp

    run_mcp()
