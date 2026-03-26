"""mcp/tools.py 的单元测试。

验证 6 个 MCP 工具的定义完整性和 mock 处理逻辑。
"""

import json

import pytest

from easytransfer.core.errors import ToolExecutionError
from easytransfer.mcp.tools import TOOL_DEFINITIONS, handle_tool_call


class TestToolDefinitions:
    """工具定义完整性测试。"""

    def test_exactly_six_tools(self):
        assert len(TOOL_DEFINITIONS) == 6

    def test_all_tools_have_required_fields(self):
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool, f"工具缺少 name 字段"
            assert "description" in tool, f"工具 {tool.get('name')} 缺少 description"
            assert "input_schema" in tool, f"工具 {tool.get('name')} 缺少 input_schema"

    def test_tool_names(self):
        names = {t["name"] for t in TOOL_DEFINITIONS}
        expected = {
            "scan_environment",
            "analyze_migration",
            "create_migration_package",
            "restore_from_package",
            "verify_migration",
            "rollback_migration",
        }
        assert names == expected

    def test_all_descriptions_nonempty(self):
        for tool in TOOL_DEFINITIONS:
            assert len(tool["description"]) > 10, f"工具 {tool['name']} 描述太短"

    def test_input_schemas_are_valid_objects(self):
        for tool in TOOL_DEFINITIONS:
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema


class TestHandleToolCall:
    """工具调用路由测试。"""

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_error(self):
        with pytest.raises(ToolExecutionError, match="未知工具"):
            await handle_tool_call("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_scan_environment_returns_json(self):
        result = await handle_tool_call("scan_environment", {"scope": "full"})
        data = json.loads(result)
        assert data["status"] == "success"
        assert "summary" in data
        assert "apps" in data

    @pytest.mark.asyncio
    async def test_analyze_migration_returns_json(self, sample_profile_path):
        result = await handle_tool_call(
            "analyze_migration", {"profile_path": str(sample_profile_path)}
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "analysis" in data
        assert "recommendations" in data
        assert "app_details" in data

    @pytest.mark.asyncio
    async def test_create_package_returns_migration_code(self, sample_profile_path, tmp_dir):
        output_path = str(tmp_dir / "test_pkg.etpkg")
        result = await handle_tool_call(
            "create_migration_package",
            {
                "profile_path": str(sample_profile_path),
                "output_mode": "local",
                "output_path": output_path,
            },
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert "migration_code" in data["package_info"]
        assert len(data["package_info"]["migration_code"]) == 6

    @pytest.mark.asyncio
    async def test_restore_returns_result(self):
        result = await handle_tool_call(
            "restore_from_package", {"migration_code": "123456"}
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["result"]["total_items"] > 0

    @pytest.mark.asyncio
    async def test_verify_returns_report(self):
        result = await handle_tool_call(
            "verify_migration", {"migration_id": "mig-001"}
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["verification"]["total_checked"] > 0

    @pytest.mark.asyncio
    async def test_rollback_returns_result(self):
        result = await handle_tool_call(
            "rollback_migration", {"migration_id": "mig-001"}
        )
        data = json.loads(result)
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_rollback_with_specific_items(self):
        result = await handle_tool_call(
            "rollback_migration",
            {"migration_id": "mig-001", "item_ids": ["item-1", "item-2"]},
        )
        data = json.loads(result)
        assert data["rollback"]["rolled_back_items"] == 2
