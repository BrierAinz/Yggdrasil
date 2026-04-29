from lilith_tools.registry import ToolRegistry
from lilith_tools.system import SystemInfoTool


def test_tool_registration():
    assert "system_info" in ToolRegistry.list_tools()
    assert "system_time" in ToolRegistry.list_tools()
    assert "file_read" in ToolRegistry.list_tools()


def test_system_info_tool():
    tool = SystemInfoTool()
    result = tool.execute()
    assert result.success
    assert "os" in result.data
