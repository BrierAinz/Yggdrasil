from .base import BaseTool, ToolResult
from .registry import ToolRegistry


@ToolRegistry.register
class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Obtiene informacion del sistema"
    parameters = {}

    def execute(self, **kwargs) -> ToolResult:
        import platform

        data = {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
        }
        return ToolResult(success=True, data=data)


@ToolRegistry.register
class SystemTimeTool(BaseTool):
    name = "system_time"
    description = "Obtiene la fecha y hora actual"
    parameters = {}

    def execute(self, **kwargs) -> ToolResult:
        from datetime import datetime

        return ToolResult(success=True, data={"now": datetime.now().isoformat()})
