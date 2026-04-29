from typing import List, Dict, Any
from lilith_core.config import Config
from lilith_tools.registry import ToolRegistry
from lilith_memory.store import MemoryStore


class LilithEngine:
    def __init__(self, config: Config, memory_store: MemoryStore):
        self.config = config
        self.memory = memory_store
        self.tools = ToolRegistry

    def process(self, user_input: str) -> Dict[str, Any]:
        context = self.memory.search(user_input, limit=3)
        prompt = self._build_prompt(user_input, context)
        tool_call = self._detect_tool(user_input)

        return {
            "prompt": prompt,
            "context": context,
            "tool_call": tool_call,
            "response": None,
        }

    def _build_prompt(self, user_input: str, context: List[Dict]) -> str:
        ctx_str = "\n".join([c["content"] for c in context]) if context else ""
        return f"Contexto previo:\n{ctx_str}\n\nUsuario: {user_input}\n\nAsistente:"

    def _detect_tool(self, user_input: str) -> Dict:
        available = self.tools.list_tools()
        for name, desc in available.items():
            if name.replace("_", " ") in user_input.lower():
                return {"tool": name, "reason": f"Palabra clave detectada: {name}"}
        return {}

    def execute_tool(self, tool_name: str, params: Dict) -> Dict:
        tool_class = self.tools.get(tool_name)
        if not tool_class:
            return {"error": f"Tool no encontrada: {tool_name}"}
        tool = tool_class()
        if not tool.validate(params):
            return {"error": "Parametros invalidos"}
        result = tool.execute(**params)
        return {"success": result.success, "data": result.data, "error": result.error}
