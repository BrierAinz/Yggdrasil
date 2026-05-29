"""
Agent Router - Lilith decide. El router ejecuta su voluntad.

Reglas de routing:
- Eva:     contexto largo, análisis, documentación (usa Grok)
- Adán:    código puro, tests, refactorización
- Odín:    investigación, creativo, privado — absorbió a Lucifer
- Kimi:    por defecto (Lilith, razonamiento, planificación)
- Shalltear: triage, clasificación, parsing NL
"""
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from .agents.panteon.adan import AdanAgent
from .agents.panteon.eva import EvaAgent
from .agents.panteon.odin import OdinAgent


class AgentRouter:
    """
    Router de agentes del Panteón.
    Decide qué agente es más apropiado para cada tarea.
    """

    def __init__(self, base_path: Optional[str] = None):
        self.eva = EvaAgent()
        self.adan = AdanAgent()
        self.odin = OdinAgent()

        # Mapeo de nombres a agentes
        # Nota: "kimi" es Lilith (orquestador), no un agente del panteón; "odin" usa Kimi para análisis masivo
        self.agent_map = {
            "eva": self.eva,
            "adan": self.adan,
            "lucifer": self.odin,  # Legacy alias → Odín absorbió a Lucifer
            "odin": self.odin,
            "kimi": None,  # Lilith/Kimi es el orquestador
            "grok": None,  # Legacy: Grok ahora es Eva
        }

    def select_agent(
        self,
        task: str,
        context_tokens: int = 0,
        user_role: str = "trusted",
        transport: str = "api",
    ) -> str:
        """
        Selecciona el agente más apropiado para una tarea.

        Args:
            task: La tarea a ejecutar
            context_tokens: Tamaño del contexto en tokens (aproximado)
            user_role: Rol del usuario (owner, trusted, public)
            transport: Transporte usado (discord, telegram, api, web)

        Returns:
            Nombre del agente seleccionado
        """
        task_lower = task.lower()

        # === EVA: Contexto largo o análisis ===
        if context_tokens > 50000:
            if self.eva.is_available():
                return "eva"

        eva_keywords = [
            "analiza",
            "documenta",
            "resume",
            "revisa todos",
            "lee el proyecto",
            "dame un resumen de",
            "audita",
            "examina",
            "estudia",
            "investiga",
            "compara",
            "genera documentación",
            "documentar",
            "análisis",
        ]
        if any(word in task_lower for word in eva_keywords):
            if self.eva.is_available():
                return "eva"

        # === ADÁN: Código puro ===
        # Nota: "implementa" es ambiguo (puede ser implementación de feature o de código)
        # Se usa solo con contexto de código
        adan_keywords = [
            "genera código",
            "escribe una función",
            "crea una clase",
            "refactoriza",
            "genera tests",
            "codifica",
            "escribe un script",
            "crea un módulo",
            "optimiza el código",
            "corrige el error",
            "fix",
            "debug",
            "test unitario",
            "función",
            "function",
            "script",
            "código",
            "code",
        ]
        if any(word in task_lower for word in adan_keywords):
            if self.adan.is_available():
                return "adan"

        # === ODÍN: Creativo, privado, investigación profunda ===
        odin_creative_keywords = [
            "creativo",
            "imagina",
            "inventa",
            "privado",
            "sin logs",
            "confidencial",
            "alternativa",
            "alternativo",
            "piensa fuera de la caja",
            "solución radical",
            "rompe las reglas",
            "enfoque diferente",
            "qué pasaría si",
            "supón que",
            "reimagina",
            "propón",
            "propuesta",
            "fuera de lo común",
        ]
        if any(word in task_lower for word in odin_creative_keywords):
            if self.odin.is_available():
                return "odin"

        # === Default: Kimi/Lilith (contexto 262k) ===
        return "kimi"

    async def execute(
        self,
        task: str,
        agent_name: str = None,
        context: str = "",
        context_tokens: int = 0,
        user_role: str = "trusted",
        transport: str = "api",
    ) -> Dict[str, Any]:
        """
        Ejecuta una tarea con el agente especificado o el seleccionado.

        Args:
            task: La tarea a ejecutar
            agent_name: Nombre del agente a usar (None para auto-selección)
            context: Contexto adicional
            context_tokens: Tamaño del contexto en tokens
            user_role: Rol del usuario (owner, trusted, public)
            transport: Transporte usado (discord, telegram, api, web)

        Returns:
            Dict con el resultado de la ejecución
        """
        if agent_name is None:
            agent_name = self.select_agent(task, context_tokens, user_role, transport)

        agent_name = agent_name.lower()

        if agent_name == "kimi" or agent_name not in self.agent_map:
            # Lilith/Kimi maneja directamente
            return {
                "agent": "kimi",
                "agent_display": "Lilith",
                "result": None,
                "delegated": False,
                "task": task,
            }

        agent = self.agent_map[agent_name]

        if agent is None:
            return {
                "agent": "kimi",
                "agent_display": "Lilith",
                "result": None,
                "delegated": False,
                "task": task,
            }

        # Verificar disponibilidad
        if not agent.is_available():
            return {
                "agent": agent_name,
                "agent_display": agent.name,
                "result": f"[{agent.name} offline] Agente no disponible. Fallback a Lilith.",
                "delegated": False,
                "task": task,
            }

        # Ejecutar la tarea (execute es síncrono en Eva/Adán/Odín)
        if asyncio.iscoroutinefunction(getattr(agent, "execute", None)):
            result = await agent.execute(task, context)
        else:
            result = agent.execute(task, context)

        return {
            "agent": agent_name,
            "agent_display": agent.name,
            "result": result,
            "delegated": True,
            "task": task,
        }

    def get_agent_info(self) -> Dict[str, Any]:
        """
        Retorna información sobre todos los agentes disponibles.

        Post-cambio de roles:
        - Lilith (kimi): Orquestadora principal, contexto 262k
        - Eva: Analista, usa Grok
        - Adán: Código puro (Qwen local)
        - Odín: Investigación, contexto masivo (Kimi)
        """
        return {
            "eva": {
                "name": self.eva.name,
                "description": self.eva.description,
                "available": self.eva.is_available(),
                "model": "grok-4-fast-reasoning",
            },
            "adan": {
                "name": self.adan.name,
                "description": self.adan.description,
                "available": self.adan.is_available(),
                "model": "qwen2.5-coder:7b",
            },
            "kimi": {
                "name": "Lilith",
                "description": "Orquestadora. Kimi (contexto 262k).",
                "available": True,
                "model": "kimi-for-coding",
            },
            "odin": {
                "name": self.odin.name,
                "description": self.odin.description,
                "available": self.odin.is_available(),
                "model": "kimi-for-coding",
            },
        }