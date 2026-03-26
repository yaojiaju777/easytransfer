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
def analyze(
    profile_path: str = typer.Option(..., "--profile", "-p", help="环境画像 JSON 文件路径"),
    show_details: bool = typer.Option(False, "--details", "-d", help="显示每个应用的详细分析"),
) -> None:
    """分析迁移可行性。

    读取环境画像文件，分析哪些应用可以自动迁移、
    哪些需要手动处理，并给出迁移建议。
    """
    import asyncio

    from easytransfer.planner.analyzer import analyze_from_file

    console.print(f"\n[bold blue]{APP_NAME}[/] — 正在分析迁移可行性...\n")

    try:
        analysis = asyncio.run(analyze_from_file(profile_path))
    except Exception as e:
        console.print(f"[red]分析失败: {e}[/]")
        raise typer.Exit(1)

    # 总览表格
    table = Table(title="迁移分析总览")
    table.add_column("项目", style="cyan")
    table.add_column("数值", justify="right", style="green")

    table.add_row("应用总数", str(analysis.total_apps))
    table.add_row("可自动安装", f"[green]{analysis.auto_installable_apps}[/]")
    table.add_row("需手动安装", f"[yellow]{analysis.manual_install_apps}[/]")
    not_available = analysis.total_apps - analysis.auto_installable_apps - analysis.manual_install_apps
    table.add_row("未识别", f"[red]{not_available}[/]")

    data_gb = analysis.total_data_size_bytes / (1024**3)
    table.add_row("总数据量", f"{data_gb:.1f} GB")
    table.add_row("预计迁移时间", f"{analysis.estimated_time_minutes} 分钟")

    console.print(table)

    # 详细信息
    if show_details and analysis.app_details:
        detail_table = Table(title="\n应用详情")
        detail_table.add_column("应用", style="cyan")
        detail_table.add_column("版本", style="dim")
        detail_table.add_column("分类", justify="center")
        detail_table.add_column("方式", style="dim")
        detail_table.add_column("备注")

        for d in analysis.app_details:
            cat = d.get("category", "")
            if cat == "auto_installable":
                cat_display = "[green]自动[/]"
            elif cat == "manual_install":
                cat_display = "[yellow]手动[/]"
            else:
                cat_display = "[red]未识别[/]"

            detail_table.add_row(
                d.get("name", ""),
                d.get("version", ""),
                cat_display,
                d.get("strategy", ""),
                d.get("notes", "")[:50],
            )

        console.print(detail_table)

    # 建议
    if analysis.recommendations:
        console.print("\n[bold]建议:[/]")
        for rec in analysis.recommendations:
            console.print(f"  [green]>[/] {rec}")

    # 警告
    if analysis.warnings:
        console.print("\n[bold yellow]警告:[/]")
        for warn in analysis.warnings:
            console.print(f"  [yellow]![/] {warn}")

    console.print()


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
    import asyncio
    import json
    from pathlib import Path

    from easytransfer.packager.packer import pack_migration
    from easytransfer.planner.analyzer import _dict_to_profile, analyze_profile

    console.print(f"\n[bold blue]{APP_NAME}[/] — 正在打包迁移数据...\n")

    if not profile:
        console.print("[yellow]未指定环境画像文件，将先执行扫描...[/]\n")
        from easytransfer.core.models import ScanScope
        from easytransfer.scanner.orchestrator import run_full_scan, save_profile

        env_profile = asyncio.run(run_full_scan(scope=ScanScope.FULL))

        # 保存到临时位置
        from easytransfer.core.config import APP_DIR

        profile_path = APP_DIR / "latest_profile.json"
        save_profile(env_profile, profile_path)
        profile = str(profile_path)
        console.print(f"[green]扫描完成，画像已保存: {profile}[/]\n")
    else:
        # 从文件加载
        path = Path(profile)
        if not path.exists():
            console.print(f"[red]环境画像文件不存在: {profile}[/]")
            raise typer.Exit(1)

    # 加载画像
    try:
        data = json.loads(Path(profile).read_text(encoding="utf-8"))
        env_profile = _dict_to_profile(data)
    except Exception as e:
        console.print(f"[red]无法加载环境画像: {e}[/]")
        raise typer.Exit(1)

    # 分析
    analysis = asyncio.run(analyze_profile(env_profile))

    # 打包
    try:
        pkg_info = asyncio.run(
            pack_migration(
                profile=env_profile,
                analysis=analysis,
                output_path=output,
                output_mode=mode,
            )
        )
    except Exception as e:
        console.print(f"[red]打包失败: {e}[/]")
        raise typer.Exit(1)

    # 显示结果
    size_mb = pkg_info.package_size_bytes / (1024 * 1024)
    console.print(
        Panel(
            f"[bold green]打包完成![/]\n\n"
            f"迁移码:  [bold cyan]{pkg_info.migration_code}[/]\n"
            f"包大小:  {size_mb:.1f} MB\n"
            f"项目数:  {pkg_info.item_count}\n"
            f"保存位置: {pkg_info.storage_path}\n"
            f"加密方式: {pkg_info.encryption_info}\n"
            f"过期时间: {pkg_info.expires_at}",
            title=f"{APP_NAME} — 打包结果",
            border_style="green",
        )
    )

    console.print(f"\n[bold]请记住迁移码: [cyan]{pkg_info.migration_code}[/][/]")
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
