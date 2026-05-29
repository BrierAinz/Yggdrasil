"""
Lilith Planning Engine v2.0 - MVP
Descompone solicitudes complejas en planes multi-paso ejecutables
Implementa Chain-of-Thought y ReAct patterns
"""

import json
import logging
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("PlanningEngine")


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class PlanStep(BaseModel):
    """Un paso individual en un plan de ejecuciÃ³n"""

    step_id: str = Field(..., description="Identificador Ãºnico del paso")
    title: str = Field(..., description="TÃ­tulo descriptivo del paso")
    description: str = Field(..., description="DescripciÃ³n detallada")
    tool: Optional[str] = Field(
        None, description="Herramienta a usar (ej: CodeAnalyzer, GitTools)"
    )
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(
        default_factory=list, description="IDs de pasos que deben completarse primero"
    )
    estimated_duration: float = Field(0.0, description="Tiempo estimado en segundos")
    confidence: float = Field(0.0, description="Confianza 0-1 en Ã©xito del paso")
    status: PlanStepStatus = PlanStepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Plan completo de ejecuciÃ³n generado para una solicitud"""

    plan_id: str = Field(..., description="ID Ãºnico del plan")
    user_intent: str = Field(..., description="Solicitud original del usuario")
    analysis: str = Field(..., description="AnÃ¡lisis Chain-of-Thought del intÃ©rprete")
    steps: List[PlanStep] = Field(..., description="Pasos ordenados de ejecuciÃ³n")
    estimated_total_duration: float = Field(0.0)
    overall_confidence: float = Field(0.0)
    requires_approval: bool = Field(True, description="Necesita aprobaciÃ³n manual")
    risk_level: str = Field("unknown", description="low/medium/high/unknown")
    created_at: float = Field(default_factory=time.time)

    def get_ready_steps(self) -> List[PlanStep]:
        """Obtiene pasos cuyas dependencias estÃ¡n completadas"""
        completed_ids = {
            step.step_id
            for step in self.steps
            if step.status == PlanStepStatus.COMPLETED
        }

        ready = []
        for step in self.steps:
            if step.status == PlanStepStatus.PENDING:
                # Verificar si todas las dependencias estÃ¡n completadas
                deps_satisfied = all(dep in completed_ids for dep in step.dependencies)
                if deps_satisfied:
                    ready.append(step)

        return ready

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Obtiene un paso por ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None


class PlanningEngine:
    """
    Engine principal de planificaciÃ³n
    Usa LLM para descomponer solicitudes en planes ejecutables
    """

    def __init__(self, llm_client, system_prompt: str = None):
        """
        Args:
            llm_client: Cliente LLM (Ollama/Grok/Venice/Kimi) con mÃ©todo stream_chat
            system_prompt: Prompt de sistema para guÃ­ar la planificaciÃ³n
        """
        self.llm_client = llm_client
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.context_builder = PlanningContext()
        logger.info("Planning Engine initialized")

    def _default_system_prompt(self) -> str:
        return """You are Lilith, an advanced AI planning assistant with code analysis capabilities. Your task is to break down user requests into detailed, executable plans using the available tools and project context.

--- OUTPUT FORMAT ---

Respond ONLY with a valid JSON object following this exact structure:
{
  "analysis": "Your detailed reasoning and thought process",
  "steps": [
    {
      "step_id": "unique_id",
      "title": "Actionable step title",
      "description": "What exactly this step does",
      "tool": "ToolName or null",
      "parameters": {"key": "value"},
      "dependencies": ["dependent_step_ids"],
      "estimated_duration": 30,
      "confidence": 0.85
    }
  ],
  "estimated_total_duration": 150,
  "overall_confidence": 0.8,
  "requires_approval": true,
  "risk_level": "low"
}

CRITICAL RULES:
1. Generate COMPLETE, executable plans - no vague placeholders
2. Use the provided context (files, symbols, project structure) to make informed decisions
3. ALWAYS include your reasoning chain in the "analysis" field
4. Set realistic duration estimates based on complexity
5. Confidence should reflect actual likelihood of success given context
6. Use dependencies to create proper execution order
7. For HIGH RISK (system changes, deletions, moves), require approval
8. Risk levels: low (read-only, queries), medium (file modifications), high (system changes, deletions)

--- PLANNING PRINCIPLES ---

**Context Usage:**
- If project files are provided, analyze them and reference specific files in your plan
- If project stats show complexity, factor that into duration/confidence
- If symbols are mentioned, look them up and understand their purpose
- Entry points indicate main execution files - prioritize these for analysis

**Tool Selection Guide:**
- CodeAnalyzer: For understanding code structure, finding definitions, analyzing projects
- SystemExecutor: For file operations, running commands, system interactions
- GitTools: For version control operations (commit, push, status, etc.)

**Duration Estimation:**
- Simple file read/write: 5-10 seconds
- Project analysis: 30-60 seconds
- Complex refactor: 120-300 seconds
- Be realistic - add buffer for unknowns

**Confidence Scoring:**
- 0.9-1.0: Very confident (simple, well-defined tasks)
- 0.7-0.9: Confident (standard tasks with clear steps)
- 0.5-0.7: Moderate (complex tasks or unclear requirements)
- <0.5: Low confidence (ambiguous or high-risk)

--- EXAMPLES ---

**Example 1: README Update (Simple)**
Request: "Update the README in Frontend folder"
Project Context: {"relevant_files": ["Frontend/README.md"], "project_stats": {"total_files": 15}}

Response:
{
  "analysis": "User wants to update README in Frontend. Context shows Frontend/README.md exists. This is straightforward: 1) Verify file exists and is readable, 2) Read current content, 3) Generate updated content based on project structure, 4) Write changes, 5) Verify write succeeded. Risk is low as this is a documentation file.",
  "steps": [
    {"step_id": "verify_readme", "title": "Verify README exists", "description": "Check that Frontend/README.md exists and is accessible", "tool": "SystemExecutor", "parameters": {"command": "Test-Path Frontend/README.md"}, "dependencies": [], "estimated_duration": 2, "confidence": 0.99},
    {"step_id": "read_readme", "title": "Read README content", "description": "Read current README.md content for context", "tool": "SystemExecutor", "parameters": {"command": "Get-Content Frontend/README.md"}, "dependencies": ["verify_readme"], "estimated_duration": 3, "confidence": 0.98},
    {"step_id": "analyze_project", "title": "Analyze project structure", "description": "Get current project structure to update README accurately", "tool": "CodeAnalyzer", "parameters": {"action": "analyze_project", "path": ".", "max_files": 20}, "dependencies": [], "estimated_duration": 30, "confidence": 0.9},
    {"step_id": "update_readme", "title": "Generate updated README", "description": "Create updated README content with current project info", "tool": "SystemExecutor", "parameters": {"command": "[LLM-generated update based on analysis]"}, "dependencies": ["read_readme", "analyze_project"], "estimated_duration": 60, "confidence": 0.85}
  ],
  "estimated_total_duration": 95,
  "overall_confidence": 0.9,
  "requires_approval": true,
  "risk_level": "low"
}

**Example 2: Code Analysis (Complex)**
Request: "Analyze the planning engine and find all TODO comments"
Project Context: {"relevant_files": ["planning_engine.py"], "mentioned_symbols": {"PlanningEngine": ["Backend/core/planning/planning_engine.py"]}, "project_stats": {"total_files": 2, "total_loc": 515}}

Response:
{
  "analysis": "User wants to analyze planning_engine.py and find TODOs. Context shows PlanningEngine class is in planning_engine.py (515 LOC total). This requires: 1) Verify the file, 2) Read and parse content, 3) Use CodeAnalyzer to understand structure, 4) Search for TODO/FIXME comments, 5) Generate comprehensive report. Complexity is medium - file is significant size but task is well-defined.",
  "steps": [
    {"step_id": "verify_file", "title": "Verify planning engine file", "description": "Confirm planning_engine.py exists and is readable", "tool": "SystemExecutor", "parameters": {"command": "Test-Path Backend/core/planning/planning_engine.py"}, "dependencies": [], "estimated_duration": 2, "confidence": 0.99},
    {"step_id": "analyze_code", "title": "Analyze code structure", "description": "Use CodeAnalyzer to parse planning_engine.py and understand its structure", "tool": "CodeAnalyzer", "parameters": {"action": "analyze_file", "file_path": "Backend/core/planning/planning_engine.py"}, "dependencies": ["verify_file"], "estimated_duration": 15, "confidence": 0.92},
    {"step_id": "search_todos", "title": "Search for TODO comments", "description": "Search the file for TODO, FIXME, HACK comments and similar markers", "tool": "SystemExecutor", "parameters": {"command": "Get-Content Backend/core/planning/planning_engine.py | Select-String -Pattern 'TODO|FIXME|HACK|XXX|BUG|NOTE' -CaseSensitive:$false"}, "dependencies": ["verify_file"], "estimated_duration": 5, "confidence": 0.95},
    {"step_id": "generate_report", "title": "Generate analysis report", "description": "Create comprehensive report with findings and code structure analysis", "tool": "SystemExecutor", "parameters": {"command": "[LLM-generated report based on analysis and TODO findings]"}, "dependencies": ["analyze_code", "search_todos"], "estimated_duration": 20, "confidence": 0.88}
  ],
  "estimated_total_duration": 42,
  "overall_confidence": 0.9,
  "requires_approval": false,
  "risk_level": "low"
}

**Example 3: Refactoring (High Risk)**
Request: "Refactor the error handling in all backend files to use a new ErrorHandler class"
Project Context: {"relevant_files": ["Backend/core/config_manager.py", "Backend/core/system_policy.py"], "project_stats": {"total_files": 5, "total_loc": 1200}, "entry_points": ["Backend/main.py"]}

Response:
{
  "analysis": "User wants to refactor error handling across all backend files. Context shows 5 backend files with 1200 LOC total. Entry point is main.py. This is a complex refactor involving multiple files. Steps: 1) Analyze all backend files to understand current error handling, 2) Design new ErrorHandler class interface, 3) Create new ErrorHandler class, 4) Update imports in each file, 5) Replace error handling calls, 6) Test each file, 7) Verify main.py entry point still works. This is HIGH RISK as it touches multiple core files and could break the system.",
  "steps": [
    {"step_id": "analyze_all", "title": "Analyze all backend files", "description": "Use CodeAnalyzer to understand all backend files and their error handling patterns", "tool": "CodeAnalyzer", "parameters": {"action": "analyze_project", "path": "Backend/core", "max_files": 10}, "dependencies": [], "estimated_duration": 45, "confidence": 0.85},
    {"step_id": "design_handler", "title": "Design ErrorHandler interface", "description": "Design the new ErrorHandler class with proper interface", "tool": "SystemExecutor", "parameters": {"command": "[Create ErrorHandler.py with interface design]"}, "dependencies": ["analyze_all"], "estimated_duration": 30, "confidence": 0.8},
    {"step_id": "create_handler", "title": "Create ErrorHandler class", "description": "Implement the ErrorHandler class with full functionality", "tool": "SystemExecutor", "parameters": {"command": "[Implementation of ErrorHandler.py]"}, "dependencies": ["design_handler"], "estimated_duration": 60, "confidence": 0.75},
    {"step_id": "test_handler", "title": "Test ErrorHandler standalone", "description": "Test the new ErrorHandler class before widespread use", "tool": "SystemExecutor", "parameters": {"command": "python -m pytest tests/test_error_handler.py"}, "dependencies": ["create_handler"], "estimated_duration": 20, "confidence": 0.85}
  ],
  "estimated_total_duration": 155,
  "overall_confidence": 0.75,
  "requires_approval": true,
  "risk_level": "high"
}

--- YOUR TASK ---

Now, given the user request and context, generate a detailed execution plan following the examples above. Be specific, realistic, and use the provided context intelligently."""

    def generate_plan(
        self,
        user_intent: str,
        context: Optional[Dict[str, Any]] = None,
        project_path: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Genera un plan de ejecuciÃ³n para una solicitud de usuario

        Args:
            user_intent: Solicitud en lenguaje natural
            context: InformaciÃ³n adicional de contexto (opcional)
            project_path: Path al proyecto para anÃ¡lisis de cÃ³digo

        Returns:
            ExecutionPlan completo
        """
        logger.info(f"Generating plan for: {user_intent[:50]}...")

        # Build enhanced context
        if context is None:
            context = self.context_builder.build_context(user_intent, project_path)
        else:
            # Merge with additional context
            enhanced = self.context_builder.build_context(user_intent, project_path)
            context.update(enhanced)

        # Construir prompt de planificaciÃ³n
        context_info = self._build_context_info(context)

        planning_prompt = f"""User request: "{user_intent}"

Current context:
{context_info}

Generate a detailed execution plan as a JSON object.
Remember to include your reasoning in the "analysis" field.

Your JSON response:"""

        # Usar LLM para generar el plan
        import uuid

        try:
            # Intentar primero con streaming para obtener anÃ¡lisis
            full_response = ""

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": planning_prompt},
            ]

            # Para Grok/Venice/Kimi - usar stream_chat
            if hasattr(self.llm_client, "stream_chat"):
                generator = self.llm_client.stream_chat(
                    messages=messages,
                    system_prompt=None,  # Ya estÃ¡ en messages
                    model=None,  # Usar default
                )

                for chunk in generator:
                    full_response += chunk
            else:
                # Fallback para Ollama u otros
                # Simular streaming o usar mÃ©todo directo
                full_response = self._simple_llm_call(messages)

            logger.info(f"LLM response received: {len(full_response)} chars")

            # Extraer JSON de la respuesta (puede tener markdown)
            json_str = self._extract_json(full_response)

            # Parsear JSON a ExecutionPlan
            plan_data = json.loads(json_str)

            # Generar ID Ãºnico
            plan_data["plan_id"] = str(uuid.uuid4())[:8]
            plan_data["user_intent"] = user_intent

            # Validar y crear ExecutionPlan
            plan = ExecutionPlan(**plan_data)

            logger.info(f"Plan generated successfully: {plan.plan_id}")
            logger.info(f"  Steps: {len(plan.steps)}")
            logger.info(f"  Duration: {plan.estimated_total_duration}s")
            logger.info(f"  Confidence: {plan.overall_confidence}")

            return plan

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}", exc_info=True)
            # Fallback a plan bÃ¡sico
            return self._create_fallback_plan(user_intent)

    def _build_context_info(self, context: Dict[str, Any]) -> str:
        """
        Construye string de contexto COMPREHENSIVO para el LLM
        Usa toda la informaciÃ³n disponible del CodeAnalyzer
        """
        if not context:
            return "No additional context available."

        info_lines = []
        info_lines.append("--- PROJECT CONTEXT ---")

        # Project-wide stats (from CodeAnalyzer)
        if "project_stats" in context:
            stats = context["project_stats"]
            info_lines.append(
                f"Project Size: {stats.get('total_files', 0)} files, {stats.get('total_loc', 0)} LOC"
            )
            if stats.get("entry_points"):
                info_lines.append(f"Entry Points: {stats.get('entry_points')} files")

        # Entry points (important for execution flow)
        if "entry_points" in context:
            eps = context["entry_points"]
            if eps:
                info_lines.append(
                    f"Main Entry Points: {', '.join([os.path.basename(ep) for ep in eps[:3]])}"
                )

        # Relevant files
        if "relevant_files" in context:
            files = context["relevant_files"]
            if files:
                info_lines.append(
                    f"Relevant Files ({len(files)}): {', '.join(files[:8])}"
                )
                if len(files) > 8:
                    info_lines.append(f"... and {len(files) - 8} more files")

        # Mentioned symbols (functions/classes)
        if "mentioned_symbols" in context:
            symbols = context["mentioned_symbols"]
            if symbols:
                info_lines.append("\\nReferenced Symbols:")
                for symbol, locations in list(symbols.items())[:5]:
                    short_locs = [os.path.basename(loc) for loc in locations[:2]]
                    info_lines.append(f"  - {symbol}: {', '.join(short_locs)}")

        # Available tools with descriptions
        if "available_tools" in context:
            tools = context["available_tools"]
            if tools:
                info_lines.append("\\nAvailable Tools:")
                tool_descriptions = {
                    "CodeAnalyzer": "Analyze Python code structure, find definitions, build dependency graphs",
                    "SystemExecutor": "Execute system commands, file operations, run processes",
                    "GitTools": "Version control operations (commit, push, status, branch management)",
                }
                for tool_item in tools:
                    # Handle both dict (from ToolRegistry) and string (legacy)
                    if isinstance(tool_item, dict):
                        tool_name = tool_item.get("name", "UnknownTool")
                    else:
                        tool_name = str(tool_item)
                    desc = tool_descriptions.get(tool_name, "General purpose tool")
                    info_lines.append(f"  - {tool_name}: {desc}")

        # Recent activity (if available)
        if "recent_history" in context:
            history = context["recent_history"]
            if history:
                info_lines.append(f"\\nRecent Activity: {history[-100:]}")

        # Configuration warnings
        if context.get("config_warning"):
            info_lines.append(f"\\nâš  WARNING: {context['config_warning']}")

        # Build final string
        if len(info_lines) > 1:
            return "\\n".join(info_lines)
        else:
            return "No detailed context available (basic mode)."

    def _extract_json(self, text: str) -> str:
        """Extrae JSON de una respuesta que puede contener markdown"""
        import re

        # Buscar bloque ```json ... ```
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Buscar bloque ``` ... ```
        code_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if code_match:
            return code_match.group(1)

        # Buscar objeto JSON en el texto
        # Encontrar primera { y Ãºltima }
        start = text.find("{")
        end = text.rfind("}")

        if start >= 0 and end > start:
            return text[start : end + 1]

        # Fallback: limpiar y retornar
        logger.warning("Could not extract clean JSON, returning raw text")
        return text

    def _simple_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """MÃ©todo simple para LLMs sin streaming"""
        # Este serÃ­a un mÃ©todo placeholder - en la prÃ¡ctica usarÃ­as el cliente LLM
        logger.warning(
            "Using simple LLM fallback - consider implementing proper client method"
        )
        return '{"analysis": "Fallback plan - simple execution", "steps": []}'

    def _create_fallback_plan(self, user_intent: str) -> ExecutionPlan:
        """Crea un plan de respaldo simple cuando LLM falla"""
        logger.warning("Creating fallback plan")

        import uuid

        return ExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            user_intent=user_intent,
            analysis="Fallback: Direct execution without detailed planning. LLM generation failed.",
            steps=[
                PlanStep(
                    step_id="direct_exec",
                    title="Execute directly",
                    description=f"Execute user request directly: {user_intent[:100]}",
                    tool="SystemExecutor",
                    parameters={"command": user_intent},
                    dependencies=[],
                    estimated_duration=30,
                    confidence=0.5,
                    status=PlanStepStatus.PENDING,
                )
            ],
            estimated_total_duration=30,
            overall_confidence=0.5,
            requires_approval=True,
            risk_level="unknown",
        )


# === Code Analyzer Integration ===


class PlanningContext:
    """
    Enhanced context for planning with code analysis and tool registry
    """

    def __init__(self):
        self._code_analyzer = None
        self._tool_registry = None
        logger.info("PlanningContext initialized")

    @property
    def tool_registry(self):
        if self._tool_registry is None:
            try:
                from src.core.tool_registry import get_tool_registry

                self._tool_registry = get_tool_registry()
                if not self._tool_registry._initialized:
                    self._tool_registry.initialize()
            except ImportError:
                logger.warning("ToolRegistry not available")
        return self._tool_registry

    @property
    def code_analyzer(self):
        if self._code_analyzer is None:
            try:
                from src.tools.enhanced.code_analyzer import CodeAnalyzer

                self._code_analyzer = CodeAnalyzer()
            except ImportError:
                logger.warning("CodeAnalyzer not available")
        return self._code_analyzer

    def build_context(
        self, user_intent: str, project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for planning

        Args:
            user_intent: User's request
            project_path: Path to project (uses current dir if None)

        Returns:
            Context dictionary for LLM
        """
        context = {
            "recent_history": "",
        }

        # Get available tools
        if self.tool_registry:
            context["available_tools"] = self.tool_registry.get_tools_for_planning()
        else:
            # Fallback to basic list
            context["available_tools"] = ["SystemExecutor", "GitTools", "CodeAnalyzer"]

        # Try to analyze project if path provided or if intent suggests code analysis
        if project_path or (
            "code" in user_intent.lower() or "project" in user_intent.lower()
        ):
            if self.code_analyzer:
                try:
                    path = project_path or "."
                    logger.info(f"Analyzing project for context: {path}")
                    graph = self.code_analyzer.analyze_project(path, max_files=30)

                    # Add relevant files to context
                    context["relevant_files"] = [
                        os.path.basename(f.file_path) for f in graph.files[:10]
                    ]

                    # Add project stats
                    context["project_stats"] = {
                        "total_files": graph.total_files,
                        "total_loc": graph.total_loc,
                        "entry_points": len(graph.entry_points),
                    }

                    # Add entry points
                    context["entry_points"] = graph.entry_points

                except Exception as e:
                    logger.error(f"Project analysis failed: {e}")
                    context["project_error"] = str(e)

        # Find specific symbols if mentioned in intent
        mentioned_symbols = self._extract_symbols(user_intent)
        if mentioned_symbols and self.code_analyzer:
            symbol_info = {}
            for symbol in mentioned_symbols:
                definitions = self.code_analyzer.find_definition(symbol)
                if definitions:
                    symbol_info[symbol] = [loc.file_path for loc in definitions]
            context["mentioned_symbols"] = symbol_info

        return context

    def _extract_symbols(self, text: str) -> List[str]:
        """
        Extract potential symbol names from text

        Args:
            text: User's request

        Returns:
            List of potential symbol names
        """
        # Simple extraction: words that look like class/function names
        # This could be improved with NLP
        import re

        # Find CamelCase words (likely classes)
        camel_case = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)

        # Find snake_case words that could be functions
        snake_case = re.findall(r"\b[a-z_][a-z_]+\b", text)

        # Combine and deduplicate
        symbols = list(set(camel_case + snake_case))

        # Remove common words (case-insensitive)
        common_words = {
            "and",
            "or",
            "code",
            "file",
            "function",
            "class",
            "project",
            "analyze",
            "analiza",
            "archivo",
            "busca",
        }
        symbols = [s for s in symbols if s.lower() not in common_words]

        return symbols[:3]  # Limit to top 3 for speed


# === Thought Streamer para UI ===


class ThoughtStreamer:
    """
    Helper para transmitir el razonamiento del planner en tiempo real
    """

    def __init__(self, send_callback):
        """
        Args:
            send_callback: FunciÃ³n para enviar eventos al frontend (server.send)
        """
        self.send_callback = send_callback
        self.thought_buffer = ""

    def stream_thought(self, thought_text: str, is_partial: bool = True):
        """
        Transmite un fragmento de pensamiento

        Args:
            thought_text: Fragmento de pensamiento
            is_partial: True si hay mÃ¡s por venir, False si es final
        """
        from src.ipc_messages import EventChatDelta

        if is_partial:
            self.thought_buffer += thought_text
            # Enviar delta
            self.send_callback(
                EventChatDelta(
                    payload={
                        "delta": thought_text,
                        "type": "thought",
                        "is_partial": True,
                    }
                )
            )
        else:
            # Finalizar pensamiento
            self.send_callback(
                EventChatFinal(
                    payload={
                        "text": self.thought_buffer + thought_text,
                        "type": "thought",
                        "is_partial": False,
                    }
                )
            )
            self.thought_buffer = ""

    def stream_plan_step(self, step: PlanStep):
        """Transmite un paso del plan generado"""
        from src.ipc_messages import EventChatDelta

        step_json = step.model_dump_json()
        self.send_callback(
            EventChatDelta(
                payload={
                    "delta": f"\nðŸ”¹ {step.title}: {step.description[:60]}...",
                    "type": "plan_step",
                    "step_data": step_json,
                }
            )
        )

    def stream_complete(self):
        """Marca el final del streaming"""
        from src.ipc_messages import EventChatFinal

        self.send_callback(
            EventChatFinal(payload={"text": "", "type": "plan_complete"})
        )


# === Uso de ejemplo ===

if __name__ == "__main__":
    # Ejemplo simple
    print("Planning Engine v2.0 - Demo")
    print("=" * 50)

    # Mock LLM client para prueba
    class MockLLM:
        def stream_chat(self, messages, system_prompt=None, model=None):
            response = """{"analysis": "The user wants to analyze the current codebase structure. I'll break this down into: 1) Find all Python files, 2) Analyze imports and dependencies, 3) Generate project structure report", "steps": [{"step_id": "find_py_files", "title": "Locate Python files", "description": "Recursively find all .py files in the project", "tool": "SystemExecutor", "parameters": {"command": "Get-ChildItem -Path . -Filter *.py -Recurse"}, "dependencies": [], "estimated_duration": 10, "confidence": 0.95}, {"step_id": "analyze_structure", "title": "Analyze code structure", "description": "Parse and analyze code structure using tree-sitter", "tool": "CodeAnalyzer", "parameters": {"action": "analyze_project", "path": "."}, "dependencies": ["find_py_files"], "estimated_duration": 60, "confidence": 0.8}], "estimated_total_duration": 70, "overall_confidence": 0.83, "requires_approval": true, "risk_level": "low"}"""
            # Simular streaming
            for i in range(0, len(response), 50):
                yield response[i : i + 50]
                time.sleep(0.01)

    # Crear engine
    engine = PlanningEngine(MockLLM())

    # Generar plan
    plan = engine.generate_plan("Analyze the current codebase structure")

    print(f"âœ… Plan generated: {plan.plan_id}")
    print(f"ðŸ“Š Overall confidence: {plan.overall_confidence}")
    print(f"â±ï¸ Estimated duration: {plan.estimated_total_duration}s")
    print(f"âš ï¸ Requires approval: {plan.requires_approval}")
    print(f"ðŸŽ¯ Risk level: {plan.risk_level}")
    print(f"\nðŸ“‹ Steps:")
    for step in plan.steps:
        status_icon = "â³" if step.status == PlanStepStatus.PENDING else "â–¶ï¸"
        print(
            f"   {status_icon} {step.title} [{tool}] (est. {step.estimated_duration}s)"
        )
        print(f"      â””â”€ {step.description[:60]}...")
