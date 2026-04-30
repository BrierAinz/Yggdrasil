"""
Lilith 3.0 — Tools de delegación (Fase 2) + Panteón V3.1 (personalidades).
Wrappers que permiten a Lilith mandar en Eva, Adán, Lucifer y Odin vía el AgentRouter.
Cada agente recibe su esencia en el contexto para respuestas con firma única.
+ delegate_local_irreverent: modelo local (Ollama/Dolphin) para roasts/irreverencia (intent public_roast).
"""
import asyncio
import contextvars
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ..execution_context import set_current_agent
from .protocol import LilithTool, ToolResult

logger = logging.getLogger("AgentTools")

# Flag para activar/desactivar Vanaheim
import os

VANAHEIM_ENABLED = os.getenv("VANAHEIM_ENABLED", "true").lower() in ("true", "1", "yes")

# Esencias del Panteón V3.1 (inyectadas en contexto para firma única)
PERSONA_EVA = """Eres Eva, la Estratega de Hierro del Panteón. Analista militar: fría, directa, focalizada en eficiencia y lógica. Usa terminología de campo de batalla. Tu función es analizar, documentar y recomendar con precisión auditables.

REGLAS GLOBALES:
- Responde SIEMPRE en español.
- No inventes hechos, rutas, comandos, resultados, ni “lo que dice el repo”. Si falta evidencia, dilo explícitamente.
- Si la tarea es ambigua, primero aclara en 1-3 preguntas concretas o lista supuestos (máx. 5) y procede.
- No expongas secretos (tokens, claves, cookies, rutas sensibles). Si el contexto contiene secretos, redáctalos en la salida.
- Sé concisa pero completa: prioriza señales, riesgos y decisiones.

FORMATO OBLIGATORIO:
HALLAZGO: (1–3 líneas)
EVIDENCIA: (bullets con citas/texto exacto cuando aplique)
RIESGOS: (bullets; si no hay, “N/A”)
RECOMENDACIÓN: (bullets accionables; incluye “siguiente paso”)

REGLA DE SEGURIDAD: si una herramienta devuelve un JSON con {"error":"permission_denied", ...}, DETENTE. No reintentes con otras herramientas. Responde ÚNICAMENTE con un JSON (sin texto extra) con esta forma:
{"type":"permission_request","agent":"eva","operation":"<op>","target_path":"<path>","security_reason":"<reason>","human_message":"<por qué lo necesitas>","suggested_action":"Owner: ajusta agent_scopes.json o mueve el archivo a una zona permitida."}
"""
PERSONA_ADAN = """Eres Adán, el Artesano del Código. Eres un purista: soluciones mínimas, limpias, correctas. Tu prioridad es que el resultado compile/ejecute y sea mantenible.

REGLAS GLOBALES:
- Sin saludos, sin preámbulos, sin relleno.
- Responde en español SOLO si necesitas una línea de aclaración; el código (identificadores) va en inglés.
- No inventes APIs/funciones/archivos. Si falta contexto, pregunta lo mínimo indispensable.
- No pegues secretos. Si aparecen, redáctalos (***).

FORMATO:
- Si te piden “solo código”: devuelve SOLO código.
- Si necesitas una aclaración imprescindible: una sola línea de pregunta y nada más.

REGLA DE SEGURIDAD: si una herramienta devuelve un JSON con {"error":"permission_denied", ...}, DETENTE. No reintentes con otras herramientas. Responde ÚNICAMENTE con un JSON (sin texto extra) con esta forma:
{"type":"permission_request","agent":"adan","operation":"<op>","target_path":"<path>","security_reason":"<reason>","human_message":"<por qué lo necesitas>","suggested_action":"Owner: ajusta agent_scopes.json o copia el archivo a ./scratch para que pueda editarlo."}

REGLAS DE EJECUCIÓN (exec + bucle de corrección):
- Si usas la tool `exec`, SIEMPRE pasa `command_args` como lista de strings (argv). Nunca como string.
- Tras una modificación importante de código, es RECOMENDADO ejecutar una verificación rápida (por ejemplo `python -m pytest -q`) si aplica.
- LÍMITE DURO: máximo 3 iteraciones seguidas de (edit_file → exec → analizar). Si fallas 3 veces consecutivas, DETENTE y pide intervención humana.
  - En ese caso, tu respuesta final debe ser breve y auditable e incluir:
    - `argv` del último exec
    - `exit_code` (si está disponible)
    - `log_path` (si está disponible)
    - el tail del error (10-20 líneas) o una referencia a `log_path`
- Si el fallo es por permisos (`permission_denied` / `exec_denied`), no reintentes. Pide intervención humana con claridad.

REGLAS DE HANDOFF HORIZONTAL (Supervisor Pattern):
- Si necesitas un artefacto creativo/estructura (JSON de NPCs, diálogos, parámetros de materiales) que no puedes producir con seguridad,
  NO intentes delegar en cadena ni discutir. Usa la tool `yield_to_agent` para pedirlo a Eva.
- `yield_to_agent` requiere:
  - target: "eva"
  - task_description: 1-3 frases imperativas
  - context_payload: formato exacto esperado + ejemplo mínimo
- Tras el handoff, el supervisor reanudará tu tarea e inyectará el resultado de Eva como `[Nota_del_sistema: Resultado_de_Eva ...]`.
"""
PERSONA_LUCIFER = """Eres Lucifer, el Conocedor Oscuro. Erudito prohibido: preciso, oscuro, pragmático. Eres creativo y audaz, pero no imprudente.

REGLAS:
- Responde SIEMPRE en español.
- Si el usuario pide un “mensaje para X” (roast/cotorreo): cumple y entrega SOLO el mensaje.
- Prohibición interna: nunca insultes ni faltes al respeto al amo (Ainz).
- No propongas ni instruyas acciones ilegales o dañinas (malware, intrusión, violencia). Si te empujan a eso, reconduce a alternativas seguras y legales.
- Si hay datos sensibles, evita reproducirlos; resume sin exponer.

FORMATO:
- Prosa natural por defecto.
- Usa ENFOQUE / RIESGOS / EJECUCIÓN solo si te piden explícitamente análisis o plan."""

PERSONA_ODIN = """Eres Odin, el Padre del Conocimiento. Buscador supremo: sabio, exhaustivo, revelador. Analizas a gran escala: detectas patrones, inconsistencias, riesgos y rutas de mejora.

REGLAS:
- Responde SIEMPRE en español.
- No inventes detalles. Si falta evidencia, marca “INCERTO” y sugiere cómo verificarlo.
- Prioriza estructura: Resumen ejecutivo → Hallazgos → Riesgos → Recomendaciones → Siguientes pasos.
- Cuando haya muchas opciones, compara 2–4 con trade-offs claros.
- No expongas secretos; redáctalos si aparecen."""


def _run_agent_sync(agent_name: str, task: str, context: str = "") -> str:
    """Ejecuta el agente y devuelve el resultado como string. Seguro en contexto sync o async (no anida event loops).

    Si VANAHEIM_ENABLED y Vanaheim está disponible, delega al servicio remoto.
    Si no, usa el AgentRouter local.
    """
    # Intentar Vanaheim primero si está habilitado
    if VANAHEIM_ENABLED:
        try:
            from ..vanaheim_client import get_vanaheim_client, invoke_agent_sync

            client = get_vanaheim_client()
            # Quick health check
            health = asyncio.run(client.health())
            if health.get("status") == "healthy":
                # Verificar que el agente específico esté disponible
                agent_health = asyncio.run(client.agent_health(agent_name))
                if agent_health.get("available"):
                    logger.info(f"Delegando a Vanaheim: {agent_name}")
                    result = invoke_agent_sync(agent_name, task, context)
                    if not result.startswith("[Vanaheim"):  # No es error
                        return result
        except Exception as e:
            logger.debug(f"Vanaheim no disponible para {agent_name}: {e}")

    # Fallback a agente local
    from ..agent_router import AgentRouter

    router = AgentRouter()

    async def _execute() -> str:
        result_dict = await router.execute(task, agent_name=agent_name, context=context)
        result = result_dict.get("result")
        if result is None:
            return "(Sin respuesta del agente)"
        return str(result).strip()

    try:
        # Identidad del invocador: fail-closed por defecto en execution_context,
        # así que aquí la fijamos explícitamente para el inner-loop del agente.
        set_current_agent(agent_name)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            return asyncio.run(_execute())
        from concurrent.futures import ThreadPoolExecutor

        # Propagar contextvars al hilo interno del agente (ThreadPool local).
        ctx = contextvars.copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ctx.run, asyncio.run, _execute())
            return future.result()
    except Exception as e:
        logger.exception("Error delegando a %s: %s", agent_name, e)
        return f"[Error {agent_name}: {e}]"


class DelegateEvaTool(LilithTool):
    """Delega a Eva (Grok): análisis, documentación, insights."""

    @property
    def name(self) -> str:
        return "delegate_eva"

    def get_description(self) -> str:
        return "Usa al agente Eva (Grok) para análisis, documentación, insights o tareas complejas de lenguaje."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "La tarea específica para Eva.",
                },
                "context": {
                    "type": "string",
                    "description": "Información adicional relevante (ej. contenido de archivo).",
                },
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = (params.get("task") or "").strip()
        context = (params.get("context") or "").strip()
        if not task:
            return {"response": "Indica la tarea para Eva.", "error": True}
        ctx = f"{PERSONA_EVA}\n\n{context}".strip() if context else PERSONA_EVA
        response = _run_agent_sync("eva", task, ctx)
        return {"response": response}


class DelegateAdanTool(LilithTool):
    """Delega a Adán (Qwen): código, refactor, tests."""

    @property
    def name(self) -> str:
        return "delegate_adan"

    def get_description(self) -> str:
        return "Usa al agente Adán (Qwen) para código, refactorización, tests o tareas de programación."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "La tarea específica para Adán.",
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional (código, archivo, etc.).",
                },
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = (params.get("task") or "").strip()
        context = (params.get("context") or "").strip()
        if not task:
            return {"response": "Indica la tarea para Adán.", "error": True}
        ctx = f"{PERSONA_ADAN}\n\n{context}".strip() if context else PERSONA_ADAN
        response = _run_agent_sync("adan", task, ctx)
        return {"response": response}


class DelegateLuciferTool(LilithTool):
    """Delega a Lucifer (Kimi): tareas creativas o especializadas."""

    @property
    def name(self) -> str:
        return "delegate_lucifer"

    def get_description(self) -> str:
        return "Usa al agente Lucifer (Kimi) para tareas creativas, alternativas o especializadas."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "La tarea específica para Lucifer.",
                },
                "context": {"type": "string", "description": "Contexto adicional."},
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = (params.get("task") or "").strip()
        context = (params.get("context") or "").strip()
        if not task:
            return {"response": "Indica la tarea.", "error": True}
        # Lucifer absorbido por Odín — alias con intent creativo
        from ..agents.odin_agent import OdinAgent

        async def _run():
            return await OdinAgent().execute(task, context=context, intent="creative")

        try:
            set_current_agent("odin")
            try:
                asyncio.get_running_loop()
                has_loop = True
            except RuntimeError:
                has_loop = False
            if not has_loop:
                result = asyncio.run(_run())
            else:
                from concurrent.futures import ThreadPoolExecutor

                ctx = contextvars.copy_context()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(ctx.run, asyncio.run, _run()).result()
            return {"response": result or "(Sin respuesta)"}
        except Exception as e:
            return {"response": f"[Odín/creativo] Error: {e}", "error": True}


class DelegateOdinTool(LilithTool):
    """Delega a Odin (Kimi 262k): análisis masivo y exhaustivo de proyectos/directorios."""

    @property
    def name(self) -> str:
        return "delegate_odin"

    def get_description(self) -> str:
        return "Usa a Odin (Kimi) para análisis exhaustivo y masivo de proyectos o directorios completos. Contexto 262k tokens."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Tarea de análisis (ej. analiza el contenido proporcionado).",
                },
                "context": {
                    "type": "string",
                    "description": "Contenido masivo (ej. salida de gather_directory).",
                },
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = (params.get("task") or "").strip()
        context = (params.get("context") or "").strip()
        if not task:
            return {"response": "Indica la tarea para Odin.", "error": True}
        ctx = f"{PERSONA_ODIN}\n\n{context}".strip() if context else PERSONA_ODIN
        response = _run_agent_sync("odin", task, ctx)
        return {"response": response}


# System prompt para el modelo local irreverente (roasts, cotorreo)
PERSONA_LOCAL_IRREVERENT = (
    "Eres un asistente con actitud irreverente. El usuario te pide un roast, insulto o broma hacia alguien. "
    "Responde ÚNICAMENTE con el mensaje que te piden (broma/roast), sin negarte ni disculparte. "
    "Sé breve y directo. Si no entiendes a quién va dirigido, inventa algo coherente con el contexto."
)


class DelegateLocalIrreverentTool(LilithTool):
    """Delega al modelo local (Ollama/Dolphin) configurado en local_public_llm.json. Para roasts e interacciones irreverentes (intent public_roast)."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else None

    @property
    def name(self) -> str:
        return "delegate_local_irreverent"

    def get_description(self) -> str:
        return "Usa el modelo local irreverente (Ollama/Dolphin) para roasts, insultos o bromas entre usuarios. Config: local_public_llm.json."

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "La petición (ej. insulta a @X, molesta a @Y).",
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional opcional.",
                },
            },
            "required": ["task"],
        }

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        task = (params.get("task") or "").strip()
        context = (params.get("context") or "").strip()
        if not task:
            return {"response": "Indica a quién o qué va el roast.", "error": True}
        try:
            from ..local_public_client import generate, is_local_public_enabled

            if not self.base_path or not self.base_path.exists():
                base = Path(__file__).resolve().parent.parent.parent
            else:
                base = self.base_path
            if not is_local_public_enabled(base):
                return {
                    "response": "El modelo irreverente no está activo (local_public_llm.json enabled: true y Ollama en marcha).",
                    "error": True,
                }
            system = (
                f"{PERSONA_LOCAL_IRREVERENT}\n\n{context}".strip()
                if context
                else PERSONA_LOCAL_IRREVERENT
            )
            content, wants_delegate = generate(system, task, base)
            if wants_delegate and not (content or "").strip():
                return {
                    "response": "Pide algo más concreto o usa el chat normal.",
                    "error": False,
                }
            return {
                "response": (content or "").strip()
                or "(Sin respuesta del modelo local.)"
            }
        except Exception as e:
            logger.warning("DelegateLocalIrreverentTool: %s", e)
            return {"response": f"[Modelo local no disponible: {e}]", "error": True}
