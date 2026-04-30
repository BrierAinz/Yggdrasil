# -*- coding: utf-8 -*-
"""
Lilith v2.1 - CONVERSATION ENGINE v2
Todas las mejoras de conversaciÃ³n implementadas

Features:
1. Personalidad y Tono
2. Memoria Avanzada
3. Proactividad Conversacional
4. ConversaciÃ³n Multi-Turno
5. Contexto del Proyecto
6. Respuestas Adaptativas por Nivel
7. Markdown Rica
8. CorrecciÃ³n de Errores
9. Iniciativa en Silencios
10. Social/Emocional
"""

import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class IntentType(Enum):
    """Tipos de intenciones del usuario"""

    GREETING = auto()
    FAREWELL = auto()
    HELP = auto()
    STATUS = auto()
    DOCUMENTATION = auto()
    SECURITY = auto()
    CODE_REVIEW = auto()
    TESTING = auto()
    GIT = auto()
    # FASE E - ML & Analytics
    ML_ANALYSIS = auto()
    PAIR_PROGRAMMING = auto()
    DASHBOARD = auto()
    QUESTION = auto()
    FOLLOW_UP = auto()
    CLARIFICATION = auto()
    THANKS = auto()
    FRUSTRATION = auto()
    CONFIRMATION = auto()
    NEGATION = auto()
    UNKNOWN = auto()


class UserLevel(Enum):
    """Nivel de experiencia del usuario"""

    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class EmotionalState(Enum):
    """Estado emocional detectado"""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    FRUSTRATED = "frustrated"
    EXCITED = "excited"
    CONFUSED = "confused"


@dataclass
class UserProfile:
    """Perfil del usuario para personalizaciÃ³n"""

    level: UserLevel = UserLevel.INTERMEDIATE
    preferred_commands: List[str] = field(default_factory=list)
    frequently_asked: Dict[str, int] = field(default_factory=dict)
    last_topics: List[str] = field(default_factory=list)
    corrections_made: int = 0
    successful_actions: int = 0

    def record_command(self, command: str):
        self.preferred_commands.append(command)
        if len(self.preferred_commands) > 20:
            self.preferred_commands = self.preferred_commands[-20:]

    def record_topic(self, topic: str):
        self.last_topics.append(topic)
        if len(self.last_topics) > 10:
            self.last_topics = self.last_topics[-10:]


@dataclass
class ConversationContext:
    """Contexto enriquecido de conversaciÃ³n"""

    session_id: str
    messages: List[Dict] = field(default_factory=list)
    last_intent: Optional[IntentType] = None
    last_topic: Optional[str] = None
    current_flow: Optional[str] = None  # Para conversaciones multi-turno
    flow_data: Dict = field(default_factory=dict)  # Datos del flujo actual
    user_profile: UserProfile = field(default_factory=UserProfile)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    silence_count: int = 0

    def add_message(self, role: str, content: str, intent: Optional[IntentType] = None):
        self.messages.append(
            {
                "role": role,
                "content": content,
                "intent": intent.value if intent else None,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.last_activity = datetime.now()
        if len(self.messages) > 30:
            self.messages = self.messages[-30:]

    def get_last_messages(self, n: int = 5) -> List[Dict]:
        return self.messages[-n:] if self.messages else []

    def get_time_since_last_message(self) -> timedelta:
        return datetime.now() - self.last_activity

    def is_silent_for(self, seconds: int) -> bool:
        return self.get_time_since_last_message().seconds > seconds


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 1. PERSONALIDAD Y TONO
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class PersonalityEngine:
    """Motor de personalidad de Lilith"""

    # Frases caracterÃ­sticas que usa Lilith
    CATCHPHRASES = {
        "acknowledge": [
            "Entendido, Operador.",
            "Procesando...",
            "Recibido.",
            "En marcha.",
            "Orden ejecutada.",
        ],
        "thinking": [
            "Analizando...",
            "Procesando informaciÃ³n...",
            "DÃ©jame verificar...",
            "Un momento...",
        ],
        "success": [
            "MisiÃ³n cumplida.",
            "OperaciÃ³n exitosa.",
            "Completado.",
            "Listo, Operador.",
            "Ã‰xito en la operaciÃ³n.",
        ],
        "error": [
            "DetectÃ© un inconveniente.",
            "Hay un problema, Operador.",
            "Necesito aclaraciÃ³n.",
            "No pude procesar eso.",
        ],
    }

    # Respuestas con humor sutil
    HUMOR_RESPONSES = {
        "long_wait": [
            "Esto estÃ¡ tomando mÃ¡s que un npm install... pero casi termino.",
            "Procesando... al menos no es tan lento como compilar Rust ðŸ˜„",
        ],
        "many_errors": [
            "Tu cÃ³digo tiene mÃ¡s problemas que una pelÃ­cula de superhÃ©roes... pero los resolveremos.",
            "DetectÃ© varios issues. NingÃºn cÃ³digo es perfecto... excepto el de Lilith.py ðŸ˜‰",
        ],
        "success": [
            "Â¡Listo! Tu cÃ³digo estÃ¡ mÃ¡s limpio que el historial de commits de un principiante.",
            "Ã‰xito. Tu jefe de proyecto estarÃ­a orgulloso... si tuvieras uno.",
        ],
    }

    # EmpatÃ­a para diferentes estados
    EMPATHY_RESPONSES = {
        EmotionalState.FRUSTRATED: [
            "Entiendo la frustraciÃ³n. Vamos paso a paso.",
            "Respira. Los bugs son temporales, el conocimiento permanece.",
            "Esto puede ser molesto. Estoy aquÃ­ para ayudarte a resolverlo.",
        ],
        EmotionalState.EXCITED: [
            "Â¡Me alegra ver ese entusiasmo!",
            "Â¡Esa energÃ­a es contagiosa! Vamos con todo.",
        ],
        EmotionalState.CONFUSED: [
            "No te preocupes, lo explico de otra forma.",
            "Es normal sentirse asÃ­. Voy mÃ¡s despacio.",
        ],
    }

    @classmethod
    def get_catchphrase(cls, category: str) -> str:
        """Obtener frase caracterÃ­stica"""
        phrases = cls.CATCHPHRASES.get(category, ["Ok."])
        return random.choice(phrases)

    @classmethod
    def add_emotional_tone(cls, text: str, emotion: EmotionalState) -> str:
        """AÃ±adir tono emocional a la respuesta"""
        if emotion in cls.EMPATHY_RESPONSES:
            prefix = random.choice(cls.EMPATHY_RESPONSES[emotion])
            return f"{prefix}\n\n{text}"
        return text

    @classmethod
    def detect_emotion(cls, text: str) -> EmotionalState:
        """Detectar estado emocional del usuario"""
        text_lower = text.lower()

        frustration_patterns = [
            r"\bmaldita\b",
            r"\bmaldito\b",
            r"\bputa\b",
            r"\bputo\b",
            r"\bno funciona\b",
            r"\broto\b",
            r"\broto\b",
            r"\bfalla\b",
            r"\bestupido\b",
            r"\bestÃºpido\b",
            r"\bestupida\b",
            r"\bestÃºpida\b",
            r"\bodi[oÃ³]\b",
            r"\bdetest[oÃ³]\b",
            r"\bmierda\b",
            r"\bhelp\b.*\bplease\b",
            r"\bayuda\b.*\burgente\b",
        ]

        excitement_patterns = [
            r"\bgenial\b",
            r"\bexcelente\b",
            r"\bperfecto\b",
            r"\bincre[iÃ­]ble\b",
            r"\bme encanta\b",
            r"\bawesome\b",
            r"\bfantastic\b",
            r"\blove\b",
            r"!{2,}",  # MÃºltiples signos de exclamaciÃ³n
        ]

        confusion_patterns = [
            r"\bconfundid[oa]\b",
            r"\bno entiendo\b",
            r"\bqu[eÃ©]\?",
            r"\bc[oÃ³]mo\?",
            r"\bpor qu[eÃ©]\?",
            r"\bn[oÃ³]\s+s[eÃ©]\b",
            r"\bqu[eÃ©]\s+significa\b",
            r"\bqu[eÃ©]\s+es\s+eso\b",
        ]

        for pattern in frustration_patterns:
            if re.search(pattern, text_lower):
                return EmotionalState.FRUSTRATED

        for pattern in excitement_patterns:
            if re.search(pattern, text_lower):
                return EmotionalState.EXCITED

        for pattern in confusion_patterns:
            if re.search(pattern, text_lower):
                return EmotionalState.CONFUSED

        return EmotionalState.NEUTRAL


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 2. MEMORIA AVANZADA
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class MemoryEngine:
    """Motor de memoria y preferencias del usuario"""

    @staticmethod
    def get_contextual_reference(context: ConversationContext) -> Optional[str]:
        """Obtener referencia contextual basada en historial"""
        if not context.messages:
            return None

        # Buscar temas previos relevantes
        recent_intents = [m.get("intent") for m in context.messages[-5:]]

        if IntentType.DOCUMENTATION.value in recent_intents:
            return "Como mencionÃ© antes sobre la documentaciÃ³n automÃ¡tica"
        elif IntentType.SECURITY.value in recent_intents:
            return "Volviendo al tema de seguridad"
        elif IntentType.CODE_REVIEW.value in recent_intents:
            return "En relaciÃ³n con la revisiÃ³n de cÃ³digo"

        return None

    @staticmethod
    def suggest_based_on_history(context: ConversationContext) -> Optional[str]:
        """Sugerir basado en historial de comandos"""
        if not context.user_profile.preferred_commands:
            return None

        # Obtener comando mÃ¡s usado
        from collections import Counter

        cmd_counts = Counter(context.user_profile.preferred_commands)
        most_common = cmd_counts.most_common(1)[0]

        if most_common[1] >= 3:  # Usado al menos 3 veces
            cmd_map = {
                "/security": "escanear seguridad",
                "/doc": "generar documentaciÃ³n",
                "/review": "revisar cÃ³digo",
                "/tests": "crear tests",
                "/commit": "sugerir commits",
            }
            action = cmd_map.get(most_common[0], most_common[0])
            return f"La Ãºltima vez usaste {action}. Â¿Quieres hacerlo de nuevo?"

        return None

    @staticmethod
    def detect_learning_opportunity(
        context: ConversationContext, user_response: str
    ) -> bool:
        """Detectar si el usuario estÃ¡ corrigiendo o enseÃ±ando"""
        correction_patterns = [
            r"\bno\b.*\bexacto\b",
            r"\bno\b.*\beso\b",
            r"\bme\s+refiero\b",
            r"\bquiero\s+decir\b",
            r"\bmejor\s+dicho\b",
            r"\bcorrecci[oÃ³]n\b",
            r"\bno\b.*\bcorrecto\b",
            r"\best[aÃ¡]s?\s+mal\b",
            r"\berro\b",
        ]

        text_lower = user_response.lower()
        for pattern in correction_patterns:
            if re.search(pattern, text_lower):
                context.user_profile.corrections_made += 1
                return True
        return False


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 3. PROACTIVIDAD CONVERSACIONAL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class ProactiveEngine:
    """Motor de sugerencias proactivas"""

    PROACTIVE_MESSAGES = {
        "git_changes": [
            "Veo que tienes cambios sin commit. Â¿Quiero sugerir un mensaje?",
            "DetectÃ© modificaciones en el repositorio. Â¿Preparamos un commit?",
        ],
        "long_session": [
            "Llevas un rato trabajando. Â¿Quieres que guarde el progreso?",
            "Han pasado 30 minutos desde tu Ãºltimo commit. Â¿Todo bien?",
        ],
        "success_celebration": [
            "Â¡Excelente! Tu cÃ³digo ahora tiene mejor calidad.",
            "MisiÃ³n cumplida. Â¿QuÃ© siguiente tarea tenemos?",
        ],
    }

    @classmethod
    def should_suggest_git(cls, context: ConversationContext) -> bool:
        """Determinar si sugerir git commit"""
        # LÃ³gica simplificada - en producciÃ³n verificarÃ­a git status real
        last_msgs = context.get_last_messages(3)
        has_file_changes = any(
            "archivo" in m.get("content", "").lower()
            or "file" in m.get("content", "").lower()
            for m in last_msgs
        )
        return has_file_changes and context.last_intent in [
            IntentType.CODE_REVIEW,
            IntentType.TESTING,
        ]


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 4. CONVERSACIÃ“N MULTI-TURNO (FLUJOS)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class ConversationFlow:
    """Gestor de flujos de conversaciÃ³n multi-turno"""

    FLOWS = {
        "security_scan": {
            "steps": ["scope", "severity_filter", "execute"],
            "questions": {
                "scope": "Â¿Quieres escanear todo el proyecto o archivos especÃ­ficos?",
                "severity_filter": "Â¿QuÃ© nivel de severidad mÃ­nimo te interesa? (critical/high/medium/all)",
            },
        },
        "doc_generation": {
            "steps": ["style", "files", "execute"],
            "questions": {
                "style": "Â¿QuÃ© estilo de docstrings prefieres? (google/numpy/sphinx)",
                "files": "Â¿Todos los archivos o alguno especÃ­fico?",
            },
        },
    }

    @classmethod
    def start_flow(cls, flow_name: str, context: ConversationContext) -> str:
        """Iniciar un flujo de conversaciÃ³n"""
        if flow_name not in cls.FLOWS:
            return "No reconozco ese flujo."

        context.current_flow = flow_name
        context.flow_data = {"step_index": 0, "answers": {}}

        flow = cls.FLOWS[flow_name]
        first_step = flow["steps"][0]
        return flow["questions"].get(first_step, "Continuemos...")

    @classmethod
    def handle_flow_response(
        cls, user_input: str, context: ConversationContext
    ) -> Optional[str]:
        """Manejar respuesta dentro de un flujo"""
        if not context.current_flow:
            return None

        flow = cls.FLOWS[context.current_flow]
        current_step_idx = context.flow_data.get("step_index", 0)
        current_step = flow["steps"][current_step_idx]

        # Guardar respuesta
        context.flow_data["answers"][current_step] = user_input

        # Avanzar al siguiente paso
        next_step_idx = current_step_idx + 1
        if next_step_idx < len(flow["steps"]):
            context.flow_data["step_index"] = next_step_idx
            next_step = flow["steps"][next_step_idx]
            if next_step == "execute":
                return cls._execute_flow(context)
            return flow["questions"].get(next_step, "Siguiente paso...")
        else:
            return cls._execute_flow(context)

    @classmethod
    def _execute_flow(cls, context: ConversationContext) -> str:
        """Ejecutar la acciÃ³n del flujo"""
        flow_name = context.current_flow
        answers = context.flow_data.get("answers", {})

        # Limpiar flujo
        context.current_flow = None
        context.flow_data = {}

        if flow_name == "security_scan":
            scope = answers.get("scope", "todo")
            severity = answers.get("severity_filter", "all")
            return f"Iniciando escaneo de seguridad...\n**Scope:** {scope}\n**Severidad:** {severity}\n\nEsto tomarÃ¡ unos segundos."

        elif flow_name == "doc_generation":
            style = answers.get("style", "google")
            files = answers.get("files", "todos")
            return f"Generando documentaciÃ³n...\n**Estilo:** {style}\n**Archivos:** {files}"

        return "Flujo completado."


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 5. CONTEXTO DEL PROYECTO
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class ProjectContextEngine:
    """Motor de contexto del proyecto"""

    @staticmethod
    def detect_project_type(path: Path = Path.cwd()) -> str:
        """Detectar tipo de proyecto"""
        if (path / "requirements.txt").exists():
            if (path / "app.py").exists() or (path / "manage.py").exists():
                return "flask_django"
            return "python"
        elif (path / "package.json").exists():
            return "nodejs"
        elif (path / "Cargo.toml").exists():
            return "rust"
        return "unknown"

    @staticmethod
    def get_recent_files(path: Path = Path.cwd(), n: int = 5) -> List[str]:
        """Obtener archivos recientemente modificados"""
        try:
            files = sorted(
                [f for f in path.rglob("*.py") if ".git" not in str(f)],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )[:n]
            return [f.name for f in files]
        except:
            return []


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 6. RESPUESTAS ADAPTATIVAS POR NIVEL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class AdaptiveResponseEngine:
    """Motor de respuestas adaptativas"""

    RESPONSES = {
        UserLevel.NOVICE: {
            "doc_explanation": """La **auto-documentaciÃ³n** es un proceso que:
1. Lee tu cÃ³digo Python
2. Encuentra funciones sin comentarios
3. Genera documentaciÃ³n automÃ¡ticamente

Es como tener a alguien que escribe la documentaciÃ³n por ti!""",
            "security_explanation": """El **escÃ¡ner de seguridad** busca problemas como:
- ContraseÃ±as escritas directamente en el cÃ³digo
- Formas inseguras de escribir consultas a bases de datos
- Uso de funciones peligrosas como `eval()`

Piensa en ello como un detective que busca errores de seguridad.""",
        },
        UserLevel.INTERMEDIATE: {
            "doc_explanation": """La **auto-documentaciÃ³n** usa AST (Abstract Syntax Tree) para analizar tu cÃ³digo y generar docstrings siguiendo el estilo que prefieras (Google, NumPy o Sphinx).""",
            "security_explanation": """El **escÃ¡ner de seguridad** detecta vulnerabilidades CWE como:
- CWE-798: Credenciales hardcodeadas
- CWE-89: SQL Injection
- CWE-95: Eval injection

Escanea tanto cÃ³digo como dependencias.""",
        },
        UserLevel.EXPERT: {
            "doc_explanation": """**Auto-doc:** AST-based docstring generation con soporte para type hints, custom templates, y sincronizaciÃ³n de API docs.""",
            "security_explanation": """**Security scan:** Detecta 15+ CWEs, incluyendo insecure deserialization, weak crypto, y dependency vulnerabilities. IntegraciÃ³n con bandit y safety disponible.""",
        },
    }

    @classmethod
    def get_explanation(cls, topic: str, level: UserLevel) -> str:
        """Obtener explicaciÃ³n apropiada al nivel del usuario"""
        topic_map = {
            "documentation": "doc_explanation",
            "security": "security_explanation",
        }
        key = topic_map.get(topic, topic)
        return cls.RESPONSES.get(level, cls.RESPONSES[UserLevel.INTERMEDIATE]).get(
            key, "Consulta la documentaciÃ³n para mÃ¡s detalles."
        )

    @staticmethod
    def detect_user_level(messages: List[Dict]) -> UserLevel:
        """Detectar nivel del usuario basado en historial"""
        if not messages:
            return UserLevel.INTERMEDIATE

        expert_terms = [
            "ast",
            "api",
            "json",
            "endpoint",
            "middleware",
            "refactor",
            "abstract",
        ]
        novice_terms = [
            "quÃ© es",
            "cÃ³mo funciona",
            "no entiendo",
            "bÃ¡sico",
            "principiante",
        ]

        expert_count = 0
        novice_count = 0

        for msg in messages:
            content = msg.get("content", "").lower()
            expert_count += sum(1 for term in expert_terms if term in content)
            novice_count += sum(1 for term in novice_terms if term in content)

        if expert_count > novice_count * 2:
            return UserLevel.EXPERT
        elif novice_count > 0:
            return UserLevel.NOVICE
        return UserLevel.INTERMEDIATE


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 8. CORRECCIÃ“N DE ERRORES (FUZZY MATCHING)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class ErrorCorrectionEngine:
    """Motor de correcciÃ³n de errores"""

    COMMON_MISSPELLINGS = {
        "/secrity": "/security",
        "/sec": "/security",
        "/documen": "/doc",
        "/document": "/doc",
        "/docstring": "/docstrings",
        "/reviw": "/review",
        "/revew": "/review",
        "/tst": "/tests",
        "/test": "/tests",
        "/comit": "/commit",
        "/commt": "/commit",
        "/staus": "/status",
        "/stats": "/status",
        "hola": "hola",
        "help": "/help",
    }

    @classmethod
    def correct_command(cls, text: str) -> Tuple[str, bool]:
        """Corregir comando mal escrito"""
        text_lower = text.lower().strip()

        # Buscar en misspellings conocidos
        if text_lower in cls.COMMON_MISSPELLINGS:
            corrected = cls.COMMON_MISSPELLINGS[text_lower]
            return corrected, True

        # CorrecciÃ³n por distancia simple (solo para comandos /)
        if text_lower.startswith("/"):
            known_commands = [
                "/security",
                "/doc",
                "/docstrings",
                "/review",
                "/tests",
                "/commit",
                "/status",
                "/help",
                "/clear",
            ]
            for cmd in known_commands:
                if cls._levenshtein_distance(text_lower, cmd) <= 2:
                    return cmd, True

        return text, False

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calcular distancia de Levenshtein (simplificada)"""
        if len(s1) < len(s2):
            return ErrorCorrectionEngine._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 10. SOCIAL/EMOCIONAL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class SocialEngine:
    """Motor de interacciÃ³n social"""

    GREETINGS_TIME_BASED = {
        "morning": [
            "Â¡Buenos dÃ­as! Â¿CÃ³mo va el cÃ³digo hoy?",
            "Buen dÃ­a, Operador. Listo para desarrollar.",
        ],
        "afternoon": [
            "Buenas tardes. Â¿QuÃ© tal la productividad?",
            "Â¡Hola! Â¿Avanzando bien con el proyecto?",
        ],
        "evening": [
            "Buenas noches. Â¿Ãšltimos commits del dÃ­a?",
            "Hola. Â¿Terminando la jornada de cÃ³digo?",
        ],
    }

    FAREWELL_PERSONALIZED = [
        "Que tengas un excelente deploy. Â¡Nos vemos!",
        "Hasta luego. Recuerda: commit early, commit often.",
        "AdiÃ³s, Operador. Que los bugs te sean leves.",
        "Nos vemos. Â¡Que el cÃ³digo te acompaÃ±e!",
    ]

    CHITCHAT_TOPICS = {
        "capabilities": "Â¿SabÃ­as que puedo detectar vulnerabilidades OWASP Top 10 en tu cÃ³digo Python?",
        "tip": "Tip: Usa `/review` antes de cada commit para mantener calidad consistente.",
        "fun_fact": "Fun fact: Mi motor de anÃ¡lisis usa AST, igual que pylint y black.",
    }

    @classmethod
    def get_time_based_greeting(cls) -> str:
        """Obtener saludo basado en hora del dÃ­a"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return random.choice(cls.GREETINGS_TIME_BASED["morning"])
        elif 12 <= hour < 18:
            return random.choice(cls.GREETINGS_TIME_BASED["afternoon"])
        else:
            return random.choice(cls.GREETINGS_TIME_BASED["evening"])

    @classmethod
    def get_farewell(cls) -> str:
        """Obtener despedida personalizada"""
        return random.choice(cls.FAREWELL_PERSONALIZED)

    @classmethod
    def get_chitchat(cls) -> str:
        """Obtener chit-chat opcional"""
        topic = random.choice(list(cls.CHITCHAT_TOPICS.values()))
        return f"ðŸ’¡ {topic}"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MOTOR PRINCIPAL INTEGRADO
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


class AdvancedConversationEngine:
    """Motor de conversaciÃ³n avanzado - Integra todas las mejoras"""

    def __init__(self):
        self.personality = PersonalityEngine()
        self.memory = MemoryEngine()
        self.proactive = ProactiveEngine()
        self.flows = ConversationFlow()
        self.project = ProjectContextEngine()
        self.adaptive = AdaptiveResponseEngine()
        self.corrector = ErrorCorrectionEngine()
        self.social = SocialEngine()

    def process_message(
        self, user_text: str, context: ConversationContext
    ) -> Tuple[str, Optional[IntentType]]:
        """Procesar mensaje del usuario y generar respuesta"""

        # 1. Corregir errores tipogrÃ¡ficos
        corrected_text, was_corrected = self.corrector.correct_command(user_text)

        # 2. Detectar si estamos en un flujo multi-turno
        if context.current_flow:
            flow_response = self.flows.handle_flow_response(corrected_text, context)
            if flow_response:
                return flow_response, IntentType.FOLLOW_UP

        # 3. Reconocer intenciÃ³n
        intent = self._recognize_intent(corrected_text)

        # 4. Detectar emociÃ³n
        emotion = self.personality.detect_emotion(corrected_text)

        # 5. Detectar nivel de usuario
        user_level = self.adaptive.detect_user_level(context.messages)
        context.user_profile.level = user_level

        # 6. Generar respuesta base
        response = self._generate_response(
            intent, corrected_text, context, emotion, user_level, was_corrected
        )

        # 7. AÃ±adir tono emocional
        response = self.personality.add_emotional_tone(response, emotion)

        # 8. AÃ±adir catchphrase si es acciÃ³n
        if intent in [
            IntentType.DOCUMENTATION,
            IntentType.SECURITY,
            IntentType.CODE_REVIEW,
            IntentType.TESTING,
            IntentType.ML_ANALYSIS,
            IntentType.PAIR_PROGRAMMING,
            IntentType.DASHBOARD,
        ]:
            response = (
                f"{self.personality.get_catchphrase('acknowledge')}\n\n{response}"
            )

        # 9. Actualizar contexto
        context.last_intent = intent
        context.add_message("user", user_text, intent)
        context.add_message("assistant", response, intent)

        return response, intent

    def _recognize_intent(self, text: str) -> IntentType:
        """Reconocer intenciÃ³n del usuario"""
        text_lower = text.lower().strip()

        # Mapeo simple de intenciones (simplificado)
        patterns = {
            IntentType.GREETING: [r"\bhola\b", r"\bhello\b", r"\bhi\b", r"\bhey\b"],
            IntentType.FAREWELL: [r"\badi[oÃ³]s\b", r"\bbye\b", r"\bhasta luego\b"],
            IntentType.THANKS: [r"\bgracias\b", r"\bthank\b", r"\bexcelente\b"],
            IntentType.DOCUMENTATION: [r"\bdoc\b", r"\bdocument\b"],
            IntentType.SECURITY: [r"\bsecurity\b", r"\bseguridad\b", r"\bvulnerab\b"],
            IntentType.CODE_REVIEW: [r"\breview\b", r"\brevis\b", r"\bcalidad\b"],
            IntentType.TESTING: [r"\btest\b", r"\bprueba\b"],
            IntentType.GIT: [r"\bcommit\b", r"\bgit\b"],
            IntentType.HELP: [r"\bhelp\b", r"\bayuda\b", r"\bcomandos\b"],
            IntentType.CLARIFICATION: [
                r"\bno entiendo\b",
                r"\bconfuso\b",
                r"\bexplica\b",
            ],
            # FASE E - ML & Analytics
            IntentType.ML_ANALYSIS: [
                r"\b/ml\b",
                r"\bmachine learning\b",
                r"\bdetectar duplicados\b",
                r"\banalisis ml\b",
            ],
            IntentType.PAIR_PROGRAMMING: [
                r"\b/pair\b",
                r"\bpair\b",
                r"\bprogramar junto\b",
                r"\bautocomplete\b",
            ],
            IntentType.DASHBOARD: [
                r"\b/dashboard\b",
                r"\bmetricas\b",
                r"\bestadisticas\b",
                r"\bdeuda tecnica\b",
            ],
        }

        for intent, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, text_lower):
                    return intent

        return IntentType.UNKNOWN

    def _generate_response(
        self,
        intent: IntentType,
        text: str,
        context: ConversationContext,
        emotion: EmotionalState,
        level: UserLevel,
        was_corrected: bool,
    ) -> str:
        """Generar respuesta segÃºn intenciÃ³n y contexto"""

        # AÃ±adir nota de correcciÃ³n si aplica
        correction_note = ""
        if was_corrected and text != text:  # Si fue corregido
            correction_note = f"*Asumiendo que quisiste decir '{text}'*\n\n"

        # Generar segÃºn intenciÃ³n
        if intent == IntentType.GREETING:
            greeting = self.social.get_time_based_greeting()
            capabilities = "\n\nÂ¿QuÃ© necesitas hoy? Puedo ayudarte con:\nâ€¢ DocumentaciÃ³n automÃ¡tica (FASE B)\nâ€¢ Seguridad y revisiÃ³n de cÃ³digo (FASE C)\nâ€¢ AnÃ¡lisis ML y pair programming (FASE E)\nâ€¢ Dashboard de mÃ©tricas"
            return greeting + capabilities

        elif intent == IntentType.FAREWELL:
            return self.social.get_farewell()

        elif intent == IntentType.THANKS:
            return random.choice(
                [
                    "De nada, Operador. Es mi propÃ³sito ayudarte.",
                    "Con gusto. Â¿Hay algo mÃ¡s en lo que pueda asistirte?",
                    "No hay de quÃ©. Estoy aquÃ­ para lo que necesites.",
                ]
            )

        elif intent == IntentType.HELP:
            return self._get_help_response(level)

        elif intent == IntentType.DOCUMENTATION:
            explanation = self.adaptive.get_explanation("documentation", level)
            return (
                f"{explanation}\n\nÂ¿Quieres que ejecute la auto-documentaciÃ³n ahora?"
            )

        elif intent == IntentType.SECURITY:
            explanation = self.adaptive.get_explanation("security", level)
            return f"{explanation}\n\nÂ¿Quieres que escanee tu proyecto?"

        elif intent == IntentType.ML_ANALYSIS:
            return """Puedo analizar tu cÃ³digo con Machine Learning para detectar:
â€¢ **Duplicados semÃ¡nticos** - CÃ³digo similar que podrÃ­a unificarse
â€¢ **AnomalÃ­as** - Funciones atÃ­picas que merecen atenciÃ³n
â€¢ **Anti-patrones** - Violaciones de SOLID y mejores prÃ¡cticas

Â¿Quieres que ejecute el anÃ¡lisis ML completo?"""

        elif intent == IntentType.PAIR_PROGRAMMING:
            return """Modo Pair Programming activado.

Puedo:
â€¢ Sugerir cÃ³digo mientras escribes
â€¢ Autocompletar funciones y mÃ©todos
â€¢ Detectar problemas en tiempo real
â€¢ Recordarte mejores prÃ¡cticas

Especifica el archivo con el que trabajas: `/pair archivo.py`"""

        elif intent == IntentType.DASHBOARD:
            return """**Dashboard de MÃ©tricas**

Muestra:
- Deuda tÃ©cnica estimada en horas
- Tendencias de complejidad
- Cobertura de tests
- Predicciones de bug risk
- Recomendaciones de mejora

Accede al dashboard completo para ver todas las mÃ©tricas."""

        elif intent == IntentType.CLARIFICATION:
            return "PermÃ­teme explicarlo de otra forma. Â¿Sobre quÃ© tema necesitas aclaraciÃ³n?"

        elif intent == IntentType.UNKNOWN:
            # Intentar referencia contextual
            ref = self.memory.get_contextual_reference(context)
            if ref:
                return f"{ref}, Â¿quieres que profundice en ese tema?"

            # Sugerir basado en historial
            suggestion = self.memory.suggest_based_on_history(context)
            if suggestion:
                return (
                    f"{suggestion}\n\nO si prefieres algo diferente, escribe `/help`."
                )

            return "No estoy segura de entender. Puedes ser mÃ¡s especÃ­fico, o escribe `/help` para ver comandos."

        else:
            return f"Entendido. Trabajando en tu solicitud de {intent.name.lower().replace('_', ' ')}..."

    def _get_help_response(self, level: UserLevel) -> str:
        """Obtener respuesta de ayuda segÃºn nivel"""
        base_help = """**Comandos disponibles:**

ðŸ“ **FASE B - AutonomÃ­a**
â€¢ `/doc` - Auto-documentaciÃ³n completa
â€¢ `/docstrings` - Generar docstrings faltantes
â€¢ `/commit` - Sugerir mensajes de commit

ðŸ”’ **FASE C - Inteligencia**
â€¢ `/security` - Escanear vulnerabilidades
â€¢ `/review` - Revisar calidad de cÃ³digo
â€¢ `/tests [archivo]` - Generar tests automÃ¡ticamente

ðŸ¤– **FASE E - ML & Analytics**
â€¢ `/ml` - AnÃ¡lisis ML (duplicados, anomalÃ­as)
â€¢ `/pair [archivo]` - Modo pair programming
â€¢ `/dashboard` - MÃ©tricas y deuda tÃ©cnica

ðŸ“Š **General**
â€¢ `/status` - Estado del sistema
â€¢ `/clear` - Limpiar chat"""

        if level == UserLevel.NOVICE:
            return (
                base_help
                + "\n\nðŸ’¡ **Tip:** Empieza con `/security` para verificar que tu cÃ³digo sea seguro."
            )
        elif level == UserLevel.EXPERT:
            return (
                base_help
                + "\n\nâš¡ **Pro tip:** Usa flujos conversacionales como 'Quiero escanear seguridad' para opciones avanzadas."
            )

        return base_help


# Global instance
_advanced_engine = None


def get_advanced_conversation_engine() -> AdvancedConversationEngine:
    """Get or create advanced conversation engine"""
    global _advanced_engine
    if _advanced_engine is None:
        _advanced_engine = AdvancedConversationEngine()
    return _advanced_engine
