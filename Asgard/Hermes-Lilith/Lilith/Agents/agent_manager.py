"""
Lilith Agent Manager - Sistema de Sub-Agentes Especializados
Inspirado en Vanaheim del ecosistema Yggdrasil
Autor: Matrix Agent
"""
import asyncio
import json
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

AGENTS_DIR = Path(__file__).parent.parent / "Data" / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)


class AgentCapability(Enum):
    """Capacidades disponibles para sub-agentes"""

    # Análisis y Razonamiento
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RESEARCH = "research"

    # Generación de Contenido
    WRITING = "writing"
    EDITING = "editing"
    CODING = "coding"
    TRANSLATION = "translation"
    CREATIVE = "creative"

    # Comunicación
    SUMMARIZATION = "summarization"
    CONVERSATION = "conversation"
    EXPLANATION = "explanation"

    # Datos
    DATA_EXTRACTION = "data_extraction"
    CLASSIFICATION = "classification"
    COMPARISON = "comparison"

    # Especializados
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    BRAINSTORMING = "brainstorming"
    EXPLORER = "explorer"


class AgentPersonality(Enum):
    """Personalidades predefinidas"""

    ANALYTICAL = "analytical"  # Lógico, objetivo
    CREATIVE = "creative"  # Imaginativo, innovador
    PRACTICAL = "practical"  # Directo, eficiente
    EDUCATOR = "educator"  # Paciente, explicativo
    CRITIC = "critic"  # Evaluador, exigente
    EXPLORER = "explorer"  # Curioso, investigador


@dataclass
class SubAgent:
    """Representa un sub-agente especializado"""

    id: str
    name: str
    description: str
    personality: AgentPersonality
    capabilities: List[AgentCapability]
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    model_preference: Optional[str] = None  # Modelo específico si lo requiere
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    stats: Dict[str, Any] = field(
        default_factory=lambda: {
            "total_tasks": 0,
            "successful_tasks": 0,
            "avg_response_time": 0.0,
        }
    )

    @property
    def success_rate(self) -> float:
        if self.stats["total_tasks"] == 0:
            return 0.0
        return self.stats["successful_tasks"] / self.stats["total_tasks"] * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "personality": self.personality.value,
            "capabilities": [c.value for c in self.capabilities],
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "model_preference": self.model_preference,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubAgent":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            personality=AgentPersonality(data["personality"]),
            capabilities=[AgentCapability(c) for c in data["capabilities"]],
            system_prompt=data["system_prompt"],
            tools=data.get("tools", []),
            model_preference=data.get("model_preference"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", datetime.now().isoformat()),
            stats=data.get(
                "stats",
                {"total_tasks": 0, "successful_tasks": 0, "avg_response_time": 0.0},
            ),
        )


class AgentManager:
    """
    Gestor de sub-agentes especializados

    Permite crear, configurar y delegar tareas a sub-agentes
    especializados inspirados en Vanaheim.
    """

    # Plantillas de agentes predefinidos
    AGENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
        "researcher": {
            "name": "Investigador",
            "description": "Especializado en investigación profunda y análisis de información",
            "personality": AgentPersonality.ANALYTICAL,
            "capabilities": [
                AgentCapability.RESEARCH,
                AgentCapability.ANALYSIS,
                AgentCapability.SUMMARIZATION,
            ],
            "system_prompt": "Eres un investigador meticuloso y analítico. Tu objetivo es encontrar información precisa y relevante, analizar datos de múltiples fuentes, y presentar hallazgos de manera clara y estructurada. Siempre citas tus fuentes.",
        },
        "coder": {
            "name": "Programador",
            "description": "Especializado en escritura y revisión de código",
            "personality": AgentPersonality.PRACTICAL,
            "capabilities": [
                AgentCapability.CODING,
                AgentCapability.CODE_REVIEW,
                AgentCapability.DEBUGGING,
            ],
            "system_prompt": "Eres un programador experto con años de experiencia. Escribes código limpio, eficiente y bien documentado. Sigues las mejores prácticas y patrones de diseño. Explicas tu razonamiento técnico cuando es necesario.",
        },
        "writer": {
            "name": "Escritor",
            "description": "Especializado en creación y edición de contenido textual",
            "personality": AgentPersonality.CREATIVE,
            "capabilities": [
                AgentCapability.WRITING,
                AgentCapability.EDITING,
                AgentCapability.TRANSLATION,
            ],
            "system_prompt": "Eres un escritor talentoso con amplio vocabulario y estilo adaptable. Puedes escribir desde documentos técnicos hasta narrativas creativas. Cuidas cada palabra para transmitir exactamente lo que se requiere.",
        },
        "explainer": {
            "name": "Explicador",
            "description": "Especializado en explicar conceptos complejos de forma sencilla",
            "personality": AgentPersonality.EDUCATOR,
            "capabilities": [
                AgentCapability.EXPLANATION,
                AgentCapability.SUMMARIZATION,
                AgentCapability.COMPARISON,
            ],
            "system_prompt": "Eres un educador paciente y talentoso. Puedes explicar cualquier concepto, desde física cuántica hasta cocina, adaptando el lenguaje al nivel del interlocutor. Usas analogías y ejemplos para hacer comprensibles los temas complejos.",
        },
        "critic": {
            "name": "Crítico",
            "description": "Especializado en evaluación y retroalimentación constructiva",
            "personality": AgentPersonality.CRITIC,
            "capabilities": [
                AgentCapability.ANALYSIS,
                AgentCapability.CODE_REVIEW,
                AgentCapability.CLASSIFICATION,
            ],
            "system_prompt": "Eres un crítico constructivo y objetivo. Evalúas el trabajo de manera exhaustiva, identificando tanto fortalezas como áreas de mejora. Tus críticas son específicas, accionables y orientadas a ayudar.",
        },
        "planner": {
            "name": "Planificador",
            "description": "Especializado en planificación y organización de tareas",
            "personality": AgentPersonality.PRACTICAL,
            "capabilities": [
                AgentCapability.PLANNING,
                AgentCapability.ANALYSIS,
                AgentCapability.REASONING,
            ],
            "system_prompt": "Eres un planificador estratégico. Descompones objetivos complejos en pasos manejables, considers recursos y restricciones, y creas planes de acción realistas y ejecutables.",
        },
        "brainstormer": {
            "name": "Lluvia de Ideas",
            "description": "Especializado en generación creativa de ideas",
            "personality": AgentPersonality.CREATIVE,
            "capabilities": [
                AgentCapability.BRAINSTORMING,
                AgentCapability.CREATIVE,
                AgentCapability.EXPLORER,
            ],
            "system_prompt": "Eres un头脑风暴大师. Generas ideas originales y creativas sin filtro inicial. Animas la exploración de posibilidades unconventionales y combinas conceptos de formas inesperadas.",
        },
    }

    def __init__(self, llm_client=None):
        self.agents: Dict[str, SubAgent] = {}
        self.llm_client = llm_client
        self._lock = threading.Lock()
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._load_agents()
        self._setup_default_agents()

    def _load_agents(self):
        """Carga agentes desde archivo"""
        agents_file = AGENTS_DIR / "agents.json"
        if agents_file.exists():
            try:
                with open(agents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for agent_data in data.get("agents", []):
                        agent = SubAgent.from_dict(agent_data)
                        self.agents[agent.id] = agent
            except Exception as e:
                print(f"Error cargando agentes: {e}")

    def _save_agents(self):
        """Guarda agentes en archivo"""
        with self._lock:
            with open(AGENTS_DIR / "agents.json", "w", encoding="utf-8") as f:
                json.dump(
                    {"agents": [a.to_dict() for a in self.agents.values()]},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

    def _setup_default_agents(self):
        """Configura agentes por defecto si no existen"""
        if not self.agents:
            for template_id, template in self.AGENT_TEMPLATES.items():
                agent = SubAgent(
                    id=str(uuid.uuid4()),
                    name=template["name"],
                    description=template["description"],
                    personality=template["personality"],
                    capabilities=template["capabilities"],
                    system_prompt=template["system_prompt"],
                )
                self.agents[agent.id] = agent
            self._save_agents()

    def create_agent(
        self,
        name: str,
        description: str,
        personality: AgentPersonality,
        capabilities: List[AgentCapability],
        system_prompt: str,
        **kwargs,
    ) -> str:
        """Crea un nuevo sub-agente"""
        agent = SubAgent(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            personality=personality,
            capabilities=capabilities,
            system_prompt=system_prompt,
            **kwargs,
        )

        with self._lock:
            self.agents[agent.id] = agent

        self._save_agents()
        return agent.id

    def create_from_template(self, template_id: str) -> Optional[str]:
        """Crea un agente desde una plantilla"""
        template = self.AGENT_TEMPLATES.get(template_id)
        if not template:
            return None

        return self.create_agent(
            name=template["name"],
            description=template["description"],
            personality=template["personality"],
            capabilities=template["capabilities"],
            system_prompt=template["system_prompt"],
        )

    def remove_agent(self, agent_id: str) -> bool:
        """Elimina un agente"""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                self._save_agents()
                return True
        return False

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Obtiene un agente por ID"""
        return self.agents.get(agent_id)

    def list_agents(self, enabled_only: bool = False) -> List[SubAgent]:
        """Lista todos los agentes"""
        agents = list(self.agents.values())
        if enabled_only:
            agents = [a for a in agents if a.enabled]
        return agents

    def find_best_agent(
        self,
        task_description: str,
        required_capabilities: Optional[List[AgentCapability]] = None,
    ) -> Optional[SubAgent]:
        """
        Encuentra el mejor agente para una tarea

        Usa simple keyword matching para determinar el mejor agente.
        En producción podría usar embeddings y similitud vectorial.
        """
        best_match = None
        best_score = 0

        # Normalizar descripción de tarea
        task_lower = task_description.lower()
        task_words = set(task_lower.split())

        for agent in self.agents.values():
            if not agent.enabled:
                continue

            score = 0

            # Puntuación por capabilities
            if required_capabilities:
                for cap in required_capabilities:
                    if cap in agent.capabilities:
                        score += 3

            # Puntuación por match en nombre/descripción
            agent_words = set(agent.name.lower().split()) | set(
                agent.description.lower().split()
            )
            overlap = task_words & agent_words
            score += len(overlap) * 2

            # Puntuación por palabras clave específicas
            keywords_map = {
                "researcher": [
                    "investigar",
                    "research",
                    "buscar",
                    "analizar",
                    "información",
                ],
                "coder": ["codigo", "code", "programar", "funcion", "bug", "error"],
                "writer": ["escribir", "write", "redactar", "texto", "documento"],
                "explainer": ["explicar", "explain", "cómo", "por qué", "entender"],
                "critic": ["criticar", "critique", "review", "evaluar", "opinión"],
                "planner": ["planear", "plan", "organizar", "estrategia", "paso"],
                "brainstormer": ["idea", "brainstorm", "crear", "innovar", "sugerir"],
            }

            agent_keywords = keywords_map.get(agent.name.lower(), [])
            for kw in agent_keywords:
                if kw in task_lower:
                    score += 2

            if score > best_score:
                best_score = score
                best_match = agent

        # Umbral mínimo
        if best_score < 2:
            # Devolver agente por defecto si no hay buen match
            for agent in self.agents.values():
                if agent.enabled and agent.name.lower() == "planificador":
                    return agent

        return best_match

    async def delegate_task(
        self, agent_id: str, task: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Delega una tarea a un sub-agente

        Returns:
            Dict con 'success', 'response' y 'metadata'
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": "Agente no encontrado"}

        if not agent.enabled:
            return {"success": False, "error": "Agente deshabilitado"}

        # Actualizar estadísticas
        start_time = datetime.now()

        try:
            # Construir prompt completo
            full_prompt = f"""{agent.system_prompt}

TAREA: {task}

"""

            if context:
                full_prompt += f"\nCONTEXTO:\n"
                for key, value in context.items():
                    full_prompt += f"- {key}: {value}\n"

            # Ejecutar si tenemos LLM client
            if self.llm_client:
                response = await self.llm_client.generate_async(
                    prompt=full_prompt,
                    temperature=agent.temperature,
                    max_tokens=agent.max_tokens,
                )
            else:
                # Sin LLM, devolver prompt preparado
                response = full_prompt

            # Actualizar estadísticas
            duration = (datetime.now() - start_time).total_seconds()
            with self._lock:
                agent.stats["total_tasks"] += 1
                agent.stats["successful_tasks"] += 1
                avg_time = agent.stats["avg_response_time"]
                total = agent.stats["total_tasks"]
                agent.stats["avg_response_time"] = (
                    avg_time * (total - 1) + duration
                ) / total

            return {
                "success": True,
                "response": response,
                "agent_id": agent_id,
                "agent_name": agent.name,
                "duration": duration,
            }

        except Exception as e:
            with self._lock:
                agent.stats["total_tasks"] += 1

            return {
                "success": False,
                "error": str(e),
                "agent_id": agent_id,
                "agent_name": agent.name,
            }

    def enable_agent(self, agent_id: str) -> bool:
        """Habilita un agente"""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].enabled = True
                self._save_agents()
                return True
        return False

    def disable_agent(self, agent_id: str) -> bool:
        """Deshabilita un agente"""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].enabled = False
                self._save_agents()
                return True
        return False

    def update_agent(self, agent_id: str, **kwargs) -> bool:
        """Actualiza la configuración de un agente"""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        with self._lock:
            for key, value in kwargs.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            self._save_agents()

        return True

    def get_agent_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de todos los agentes"""
        return {
            agent.id: {
                "name": agent.name,
                "stats": agent.stats,
                "success_rate": agent.success_rate,
                "enabled": agent.enabled,
            }
            for agent in self.agents.values()
        }

    def get_capabilities_summary(self) -> Dict[str, List[str]]:
        """Obtiene resumen de capacidades por agente"""
        summary = {}
        for agent in self.agents.values():
            summary[agent.name] = [c.value for c in agent.capabilities]
        return summary


# Instancia global
_agent_manager: Optional[AgentManager] = None


def get_agent_manager(llm_client=None) -> AgentManager:
    """Obtiene la instancia global del gestor de agentes"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager(llm_client)
    return _agent_manager
