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
    import asyncio
    from pathlib import Path

    from easytransfer.core.models import ScanScope
    from easytransfer.scanner.orchestrator import run_full_scan, save_profile

    console.print(f"\n[bold blue]{APP_NAME}[/] — 正在扫描环境 (scope={scope})...\n")

    try:
        scan_scope = ScanScope(scope)
    except ValueError:
        console.print(f"[red]无效的扫描范围: {scope}[/]")
        raise typer.Exit(1)

    profile = asyncio.run(run_full_scan(scope=scan_scope))

    # 显示结果表格
    table = Table(title="扫描结果")
    table.add_column("类别", style="cyan")
    table.add_column("数量", justify="right", style="green")
    table.add_column("大小", justify="right")

    def _fmt_size(b: int) -> str:
        if b >= 1024**3:
            return f"{b / 1024**3:.1f} GB"
        if b >= 1024**2:
            return f"{b / 1024**2:.0f} MB"
        return f"{b / 1024:.0f} KB"

    apps_size = sum(a.size_bytes for a in profile.installed_apps)
    files_size = sum(fg.total_size_bytes for fg in profile.user_files)
    browser_size = sum(bp.data_size_bytes for bp in profile.browser_profiles)

    table.add_row("已安装应用", str(len(profile.installed_apps)), _fmt_size(apps_size))
    table.add_row("应用配置", str(len(profile.app_configs)), "-")
    table.add_row("用户文件组", str(len(profile.user_files)), _fmt_size(files_size))
    table.add_row("浏览器", str(len(profile.browser_profiles)), _fmt_size(browser_size))
    table.add_row("开发环境", str(len(profile.dev_environments)), "-")
    table.add_row("凭证/密钥", str(len(profile.credentials)), "-")
    table.add_row("[bold]总计[/]", "", f"[bold]{_fmt_size(profile.total_size_bytes)}[/]")

    console.print(table)

    # 显示部分应用列表
    if profile.installed_apps:
        console.print(f"\n[bold]已安装应用（前 15 个）:[/]")
        for app in profile.installed_apps[:15]:
            auto = "[green]✓ winget[/]" if app.can_auto_install else "[dim]手动[/]"
            console.print(f"  {app.name} {app.version} — {auto}")
        if len(profile.installed_apps) > 15:
            console.print(f"  [dim]...还有 {len(profile.installed_apps) - 15} 个[/]")

    # 保存到文件
    if output:
        save_profile(profile, Path(output))
        console.print(f"\n[green]环境画像已保存: {output}[/]")
    else:
        console.print(f"\n[dim]提示: 使用 --output profile.json 保存扫描结果[/]")


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
