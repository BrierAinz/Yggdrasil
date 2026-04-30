"""
Shalltear — Agente táctico del Panteón de Lilith.
Backend: Venice AI (llama-3.3-70b)
Rol: clasificación, parsing NL, respuestas rápidas, triaje de intents.

Lore: Guardiana de los primeros pisos de Nazarick. Primera línea de procesamiento.
Rápida, precisa, sin rodeos. Funcional y directa.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ShalltearAgent:
    """
    Shalltear Bloodfallen — Agente táctico del Panteón.
    Especialidad: clasificación rápida, parsing NL, scoring de importancia.
    """

    AGENT_NAME = "shalltear"
    VAULT = "shalltear"
    DEFAULT_MODEL = "llama-3.3-70b"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._client = None
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent

    def _get_base_persona(self) -> str:
        """Obtiene la identidad base de Shalltear desde el persona_loader."""
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self._project_root)
            return loader.get_system_prompt("shalltear", include_common=True)
        except Exception:
            return "[Shalltear — Agente táctico] Clasificación rápida y parsing. Fallback..."

    def _load_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        # Intentar desde env
        key = os.environ.get("VENICE_API_KEY", "").strip()
        if key:
            self._api_key = key
            return key
        # Intentar desde secrets.env
        try:
            secrets_path = self._project_root / "Config" / "secrets.env"
            if secrets_path.exists():
                with open(secrets_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("VENICE_API_KEY="):
                            self._api_key = line.split("=", 1)[1].strip().strip("\"'")
                            return self._api_key or ""
        except Exception:
            pass
        return ""

    def is_available(self) -> bool:
        """Verifica si Venice API está configurada."""
        return bool(self._load_api_key())

    def _get_client(self):
        """Lazy load del Venice client."""
        if self._client is None:
            from src.llm.venice_client import VeniceClient

            self._client = VeniceClient(api_key=self._load_api_key())
        return self._client

    def _generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 200,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> str:
        """Llamada interna a Venice."""
        if not self.is_available():
            return "ESCALATE"
        try:
            client = self._get_client()
            # Usar generate_text con modelo específico
            return client.generate_text(
                prompt=user,
                system_prompt=system,
                model=self.DEFAULT_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
            )
        except Exception as e:
            return "ESCALATE"

    async def _generate_async(
        self,
        system: str,
        user: str,
        max_tokens: int = 200,
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> str:
        """Llamada async a Venice."""
        if not self.is_available():
            return "ESCALATE"
        try:
            client = self._get_client()
            return await client.generate_async(
                system=system,
                user=user,
                model=self.DEFAULT_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
            )
        except Exception as e:
            return "ESCALATE"

    def classify_intent(self, text: str, categories: Optional[List[str]] = None) -> str:
        """
        Clasifica texto en una de las categorías dadas.
        Si no se dan categorías, usa las predefinidas.
        """
        if categories:
            cats_str = ", ".join(categories)
            system = f"""Clasifica la intención del usuario en UNA de estas categorías:
{cats_str}

Responde SOLO el nombre de la categoría, nada más.
Si no encaja o no estás segura, responde: desconocido"""
        else:
            system = self._get_intent_classify_prompt()

        result = self._generate(system, text, max_tokens=50, temperature=0.1)
        result = result.strip().lower()

        # Limpiar respuesta
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]

        return result if result else "desconocido"

    def parse_nl_to_params(
        self,
        text: str,
        operation: str = "filesystem_batch",
        schema: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Extrae parámetros estructurados de lenguaje natural.
        Por defecto parsea operaciones de filesystem.
        """
        if operation == "filesystem_batch":
            system = self._get_pc_parse_prompt()
        else:
            schema_str = (
                json.dumps(schema, indent=2)
                if schema
                else "JSON con los parámetros extraídos"
            )
            system = f"""Eres un parser de lenguaje natural a parámetros estructurados.
Operación: {operation}

Responde SOLO JSON válido siguiendo este schema:
{schema_str}

Si no puedes parsear o es ambiguo, responde: {{"error": "descripción"}}"""

        result = self._generate(
            system, text, max_tokens=500, temperature=0.1, json_mode=True
        )

        if result == "ESCALATE" or not result:
            return None

        try:
            parsed = json.loads(
                result.strip().strip("`").replace("```json", "").replace("```", "")
            )
            if "error" in parsed or "operations" in parsed:
                return parsed
            return parsed
        except json.JSONDecodeError:
            return None

    def score_importance(self, text: str) -> int:
        """
        Puntúa importancia del texto de 0 a 10.
        """
        result = self._generate(
            self._get_importance_score_prompt(),
            f"Texto a evaluar:\n{text[:2000]}",  # Limitar input
            max_tokens=10,
            temperature=0.0,
        )

        result = result.strip()

        # Intentar extraer número
        try:
            # Buscar primer número en la respuesta
            import re

            numbers = re.findall(r"\d+", result)
            if numbers:
                score = int(numbers[0])
                return max(0, min(10, score))  # Clamp 0-10
        except Exception:
            pass

        return 5  # Default neutral si falla

    def quick_answer(self, question: str, context: str = "") -> str:
        """
        Respuesta rápida a pregunta simple.
        """
        if context:
            user = f"Contexto: {context}\n\nPregunta: {question}"
        else:
            user = question

        result = self._generate(
            "Responde de forma directa y concisa. Sin preámbulos ni explicaciones.",
            user,
            max_tokens=200,
            temperature=0.3,
        )

        if result == "ESCALATE":
            return "ESCALATE"
        return result.strip()

    def evaluate_output(self, output: str, criteria: str) -> Dict[str, Any]:
        """
        Evalúa output de otro agente contra criterios.
        """
        system = """Eres un evaluador de calidad. Evalúa el output contra los criterios dados.
Responde SOLO JSON válido:
{"score": 0-10, "issues": ["issue1", "issue2"], "notes": "comentario breve"}"""

        user = f"""Criterios: {criteria}

Output a evaluar:
{output[:2000]}

Evalúa:"""

        result = self._generate(
            system, user, max_tokens=200, temperature=0.1, json_mode=True
        )

        try:
            return json.loads(
                result.strip().strip("`").replace("```json", "").replace("```", "")
            )
        except json.JSONDecodeError:
            return {"score": 5, "issues": ["No se pudo evaluar"], "notes": "Fallback"}

    # Async versions para uso en código async
    async def classify_intent_async(
        self, text: str, categories: Optional[List[str]] = None
    ) -> str:
        """Async version de classify_intent."""
        if categories:
            cats_str = ", ".join(categories)
            system = f"""Clasifica la intención del usuario en UNA de estas categorías:
{cats_str}

Responde SOLO el nombre de la categoría, nada más.
Si no encaja o no estás segura, responde: desconocido"""
        else:
            system = self._get_intent_classify_prompt()

        result = await self._generate_async(
            system, text, max_tokens=50, temperature=0.1
        )
        result = result.strip().lower()

        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith("'") and result.endswith("'"):
            result = result[1:-1]

        return result if result else "desconocido"

    # ─── Métodos de prompts (pueden ser sobreescritos o extendidos desde config) ───

    def _get_pc_parse_prompt(self) -> str:
        """Prompt para parsear operaciones de filesystem."""
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self._project_root)
            # Intentar obtener prompt específico de config, fallback al default
            agent_config = loader.get_agent_config("shalltear")
            custom_prompt = agent_config.get("pc_parse_prompt", "")
            if custom_prompt:
                return custom_prompt
        except Exception:
            pass
        return """Eres un parser de operaciones de filesystem.
Dado el mensaje del usuario, descompón en operaciones individuales.

Operaciones: pc_list, pc_mkdir, pc_move, pc_copy, pc_delete, pc_write_file, pc_exec

Aliases:
- "downloads" / "descargas" → C:\\Users\\Game_\\Downloads
- "documentos" → C:\\Users\\Game_\\Documents
- "escritorio" / "desktop" → C:\\Users\\Game_\\Desktop
- "proyectos" → D:\\Proyectos
- "lilith" → D:\\Proyectos\\Lilith
- "yggdrasil" → D:\\Proyectos\\Yggdrasil
- "core" → D:\\Proyectos\\Lilith\\Core
- "backend" → D:\\Proyectos\\Lilith\\Core\\Backend

Responde SOLO JSON válido, sin markdown ni explicación:
{"operations": [{"intent": "pc_move", "params": {"source": "...", "dest": "..."}, "description": "..."}]}

Si no entiendes o es ambiguo, responde: {"operations": [], "error": "descripción del problema"}
"""

    def _get_intent_classify_prompt(self) -> str:
        """Prompt para clasificación de intenciones."""
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self._project_root)
            agent_config = loader.get_agent_config("shalltear")
            custom_prompt = agent_config.get("intent_classify_prompt", "")
            if custom_prompt:
                return custom_prompt
        except Exception:
            pass
        return """Clasifica la intención del mensaje del usuario en UNA de estas categorías:

CATEGORÍAS:
- conversacion_casual: saludos, despedidas, charla general sin contenido operativo
- pc_operation: operaciones de archivos/carpetas/comandos del sistema
- investigacion_web: buscar información en internet, investigar URLs
- codigo: generar código, refactorizar, debuggear
- analisis_documento: analizar archivos de texto/documentación extensa
- pregunta_sobre_lilith: preguntas sobre el sistema, capacidades, quién es Lilith
- pregunta_sobre_memoria: buscar en memoria, recordar hechos previos
- desconocido: no encaja en ninguna categoría

EJEMPLOS CLAVE — clasifica EXACTAMENTE como se muestra:

PC_OPERATION (operaciones de archivos/carpetas/sistema):
- "qué hay en descargas" → pc_operation
- "dime que archivos hay en downloads" → pc_operation
- "lista mi escritorio" → pc_operation
- "qué archivos tengo en documentos" → pc_operation
- "mueve los PDFs a documentos" → pc_operation
- "copia los archivos de descargas a escritorio" → pc_operation
- "borra los .tmp" → pc_operation
- "elimina la carpeta vieja" → pc_operation
- "crea una carpeta backups" → pc_operation
- "nueva carpeta en proyectos" → pc_operation
- "ejecuta npm install" → pc_operation
- "corre el script de python" → pc_operation
- "qué tiene la carpeta proyectos" → pc_operation
- "muéstrame el contenido de downloads" → pc_operation
- "dime qué hay en el escritorio" → pc_operation
- "archivos en descargas" → pc_operation
- "listar documentos" → pc_operation

CONVERSACION_CASUAL (charla general):
- "hola, cómo estás" → conversacion_casual
- "buenos días" → conversacion_casual
- "qué tal tu día" → conversacion_casual
- "gracias" → conversacion_casual
- "adiós" → conversacion_casual

PREGUNTA_SOBRE_LILITH:
- "quién eres" → pregunta_sobre_lilith
- "qué puedes hacer" → pregunta_sobre_lilith
- "cómo funcionas" → pregunta_sobre_lilith

INVESTIGACION_WEB:
- "busca información sobre pytorch" → investigacion_web
- "investiga sobre inteligencia artificial" → investigacion_web
- "qué es el machine learning" → investigacion_web

CODIGO:
- "hazme un script en python" → codigo
- "genera una función para parsear JSON" → codigo
- "refactoriza este código" → codigo

REGLA DE ORO: CUALQUIER mensaje que mencione archivos, carpetas, descargas, downloads, escritorio, desktop, documentos, documents, proyectos, listar, mostrar contenido, mover, copiar, borrar, crear carpeta, ejecutar comando → SIEMPRE es pc_operation.

Responde SOLO el nombre de la categoría en minúsculas, sin comillas, sin explicación.
Ejemplo de respuesta válida: pc_operation
Si no estás segura, responde: desconocido
"""

    def _get_importance_score_prompt(self) -> str:
        """Prompt para evaluar importancia de información."""
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self._project_root)
            agent_config = loader.get_agent_config("shalltear")
            custom_prompt = agent_config.get("importance_score_prompt", "")
            if custom_prompt:
                return custom_prompt
        except Exception:
            pass
        return """Evalúa la importancia del siguiente texto para ser guardado en memoria permanente.
Puntúa del 0 al 10 donde:
- 0-3: Información trivial, temporal o irrelevante
- 4-6: Información útil pero no crítica
- 7-8: Información importante, decisiones, hechos relevantes
- 9-10: Información crítica, contraseñas, configuraciones esenciales, decisiones de arquitectura

Responde SOLO con un número del 0 al 10, sin explicación.
Ejemplo: 7
"""

    async def score_importance_async(self, text: str) -> int:
        """Async version de score_importance."""
        result = await self._generate_async(
            self._get_importance_score_prompt(),
            f"Texto a evaluar:\n{text[:2000]}",
            max_tokens=10,
            temperature=0.0,
        )

        result = result.strip()
        try:
            import re

            numbers = re.findall(r"\d+", result)
            if numbers:
                score = int(numbers[0])
                return max(0, min(10, score))
        except Exception:
            pass

        return 5
