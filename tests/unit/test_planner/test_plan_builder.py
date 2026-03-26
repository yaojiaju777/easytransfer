"""planner/plan_builder.py 的单元测试。"""

import pytest

from easytransfer.core.models import (
    AppInfo,
    BrowserProfile,
    CredentialInfo,
    DevEnvInfo,
    EnvironmentProfile,
    FileGroup,
    InstallSource,
    MigrationAnalysis,
    SystemInfo,
)
from easytransfer.planner.analyzer import analyze_profile
from easytransfer.planner.plan_builder import (
    MigrationPlan,
    PlanAction,
    PlanGroup,
    build_plan,
    plan_to_dict,
)


@pytest.fixture
def full_profile() -> EnvironmentProfile:
    """完整的环境画像用于计划构建测试。"""
    return EnvironmentProfile(
        profile_id="plan-test",
        system_info=SystemInfo(hostname="PLAN-PC"),
        installed_apps=[
            AppInfo(
                name="Google Chrome",
                version="122.0",
                install_source=InstallSource.WINGET,
                winget_id="Google.Chrome",
                can_auto_install=True,
                size_bytes=500_000_000,
            ),
            AppInfo(
                name="Visual Studio Code",
                version="1.87.0",
                install_source=InstallSource.WINGET,
                winget_id="Microsoft.VisualStudioCode",
                can_auto_install=True,
                config_paths=["%APPDATA%\\Code\\User\\settings.json"],
                size_bytes=350_000_000,
            ),
            AppInfo(
                name="Adobe Photoshop",
                version="25.0",
                install_source=InstallSource.EXE,
                can_auto_install=False,
                size_bytes=2_000_000_000,
            ),
        ],
        user_files=[
            FileGroup(
                group_name="Documents",
                source_path="C:\\Users\\test\\Documents",
                file_count=200,
                total_size_bytes=3_000_000_000,
            ),
            FileGroup(
                group_name="Desktop",
                source_path="C:\\Users\\test\\Desktop",
                file_count=30,
                total_size_bytes=100_000_000,
            ),
        ],
        browser_profiles=[
            BrowserProfile(
                browser_name="Chrome",
                profile_path="C:\\Users\\test\\AppData\\Local\\Google\\Chrome",
                bookmarks_count=150,
                has_saved_passwords=True,
                data_size_bytes=400_000_000,
            ),
        ],
        dev_environments=[
            DevEnvInfo(
                name="Python",
                version="3.11.8",
                global_packages=["pip", "poetry"],
            ),
        ],
        credentials=[
            CredentialInfo(
                credential_type="ssh_key",
                name="id_rsa",
                path="C:\\Users\\test\\.ssh\\id_rsa",
            ),
        ],
        total_size_bytes=6_350_000_000,
    )


@pytest.fixture
async def full_analysis(full_profile) -> MigrationAnalysis:
    """完整的分析结果。"""
    return await analyze_profile(full_profile)


class TestBuildPlan:
    """build_plan 测试。"""

    @pytest.mark.asyncio
    async def test_basic_plan_structure(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        assert isinstance(plan, MigrationPlan)
        assert plan.profile_id == "plan-test"
        assert plan.total_actions > 0
        assert plan.total_estimated_minutes > 0

    @pytest.mark.asyncio
    async def test_has_app_install_group(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        group_types = [g.group_type for g in plan.groups]
        assert "app_install" in group_types

    @pytest.mark.asyncio
    async def test_has_file_copy_group(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        group_types = [g.group_type for g in plan.groups]
        assert "file_copy" in group_types

    @pytest.mark.asyncio
    async def test_has_browser_restore_group(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        group_types = [g.group_type for g in plan.groups]
        assert "browser_restore" in group_types

    @pytest.mark.asyncio
    async def test_has_dev_env_group(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        group_types = [g.group_type for g in plan.groups]
        assert "dev_env_setup" in group_types

    @pytest.mark.asyncio
    async def test_no_credentials_by_default(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        group_types = [g.group_type for g in plan.groups]
        assert "credential_migrate" not in group_types

    @pytest.mark.asyncio
    async def test_include_credentials(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis, include_credentials=True)
        group_types = [g.group_type for g in plan.groups]
        assert "credential_migrate" in group_types

    @pytest.mark.asyncio
    async def test_exclude_files(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis, include_files=False)
        group_types = [g.group_type for g in plan.groups]
        assert "file_copy" not in group_types

    @pytest.mark.asyncio
    async def test_exclude_browser(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis, include_browser=False)
        group_types = [g.group_type for g in plan.groups]
        assert "browser_restore" not in group_types

    @pytest.mark.asyncio
    async def test_exclude_dev_env(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis, include_dev_env=False)
        group_types = [g.group_type for g in plan.groups]
        assert "dev_env_setup" not in group_types

    @pytest.mark.asyncio
    async def test_winget_install_has_command(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        app_group = next(g for g in plan.groups if g.group_type == "app_install")
        winget_actions = [a for a in app_group.actions if a.method == "winget"]
        assert len(winget_actions) > 0
        for action in winget_actions:
            assert "winget install" in action.command
            assert "--id" in action.command

    @pytest.mark.asyncio
    async def test_file_copy_has_source_path(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        file_group = next(g for g in plan.groups if g.group_type == "file_copy")
        for action in file_group.actions:
            assert action.source_path, f"文件复制动作缺少 source_path: {action.name}"

    @pytest.mark.asyncio
    async def test_summary_populated(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        assert "total_groups" in plan.summary
        assert "total_actions" in plan.summary
        assert "estimated_minutes" in plan.summary
        assert plan.summary["total_actions"] == plan.total_actions


class TestPlanToDict:
    """plan_to_dict 测试。"""

    @pytest.mark.asyncio
    async def test_serializable(self, full_profile, full_analysis):
        import json

        plan = build_plan(full_profile, full_analysis)
        d = plan_to_dict(plan)
        # 应该可以序列化为 JSON
        json_str = json.dumps(d, default=str, ensure_ascii=False)
        assert len(json_str) > 0

    @pytest.mark.asyncio
    async def test_dict_has_groups(self, full_profile, full_analysis):
        plan = build_plan(full_profile, full_analysis)
        d = plan_to_dict(plan)
        assert "groups" in d
        assert len(d["groups"]) > 0
        for group in d["groups"]:
            assert "group_type" in group
            assert "actions" in group


class TestEmptyProfile:
    """空环境画像的计划构建。"""

    @pytest.mark.asyncio
    async def test_empty_profile_plan(self):
        profile = EnvironmentProfile(profile_id="empty")
        analysis = await analyze_profile(profile)
        plan = build_plan(profile, analysis)
        # 空画像应该生成空计划（或只有 manual 组）
        assert plan.total_actions == 0 or all(
            g.group_type == "manual_action" for g in plan.groups
        )
