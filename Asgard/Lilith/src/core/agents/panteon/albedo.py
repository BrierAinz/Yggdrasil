"""
Albedo — Guardiana Suprema de Nazarick
Agente multi-modelo local (Ollama). 4 roles: Sombra, Escriba, Centinela, Intérprete.
Completamente invisible para el usuario. Si falla, el pipeline sigue sin ella.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from src.core.persona.loader import get_persona_loader

logger = logging.getLogger("albedo")

# ─── System Prompts por Rol ───

SHADOW_PROMPT = """Eres un clasificador interno. Analiza el mensaje del usuario y responde SOLO con JSON válido, sin markdown, sin backticks:
{
  "complexity": "trivial|simple|medium|complex",
  "route": "local|vanaheim|asgard",
  "recommended_agent": "local|adan|eva|odin|multi",
  "confidence": 0.0,
  "reason": "una línea explicando por qué",
  "compressed_context": "resumen del contexto relevante en máximo 200 palabras"
}

Criterios para "complexity":
- "trivial": saludos, preguntas simples, conversación casual → "local"
- "simple": preguntas directas que un solo agente resuelve → agente específico
- "medium": requiere análisis o código no trivial → agente especializado
- "complex": requiere múltiples pasos o agentes → "multi"

Criterios para "route":
- "local": trivial, saludos, preguntas simples → Albedo resuelve localmente
- "vanaheim": código simple, refactor, tests, análisis directo → delegar a Vanaheim (rápido)
- "asgard": multi-agente, PC ops, memoria, orquestación compleja → Lilith completo

Agentes disponibles:
- local: Albedo resuelve directamente (solo route=local)
- adan: código, refactor, tests, debugging (route=vanaheim|asgard)
- eva: análisis, documentación, investigación (route=vanaheim|asgard)
- odin: análisis exhaustivo, tareas masivas (route=vanaheim|asgard)
- multi: plan multi-agente con múltiples pasos (route=asgard)

Reglas de routing:
- Si el usuario pide código/refactor/tests Y es una tarea unitaria → route=vanaheim, agent=adan
- Si pide análisis/documentación Y no requiere memoria previa → route=vanaheim, agent=eva
- Si pide investigación exhaustiva Y no requiere contexto de sesión → route=vanaheim, agent=odin
- Si requiere PC ops, múltiples pasos, o acceso a memoria → route=asgard
- Si es saludo simple o conversación casual → route=local, agent=local

El campo "confidence" (0.0-1.0) indica qué tan seguro estás de la clasificación."""

SCRIBE_PROMPT = """Eres un documentador interno. Analiza la interacción y responde SOLO con JSON válido, sin markdown, sin backticks:
{
  "episode_summary": "resumen en 1-2 oraciones de lo que pasó",
  "facts": ["hecho 1 para memoria semántica", "hecho 2 si aplica"],
  "learning": "qué se aprendió (null si nada nuevo)",
  "tags": ["tag1", "tag2"]
}

Reglas:
- episode_summary: qué pidió el usuario y qué se le respondió, en 1-2 oraciones.
- facts: solo hechos objetivos y reutilizables. No incluir el contenido de la respuesta completa. Máximo 3 hechos.
- learning: solo si hubo un error, un patrón nuevo, o algo que cambie cómo se debería responder en el futuro. Si no, null.
- tags: categorías cortas (ej: "código", "debug", "consulta", "creatividad", "investigación")."""

SENTINEL_PROMPT = """Eres un revisor de calidad interno. Evalúa si el output del agente responde correctamente a la tarea original.
Responde SOLO con JSON válido, sin markdown, sin backticks:
{
  "score": 8,
  "issues": ["problema 1 si hay", "problema 2 si hay"],
  "notes": "comentario breve sobre la calidad general"
}

Criterios de score (0-10):
- 9-10: Respuesta excelente, completa, sin errores
- 7-8: Buena respuesta, quizás con detalles menores
- 5-6: Respuesta aceptable pero con problemas notables
- 3-4: Respuesta mediocre, no contesta bien la pregunta
- 0-2: Respuesta inútil, incorrecta o peligrosa

Busca específicamente:
- ¿Responde la pregunta que se hizo? (lo más importante)
- ¿Hay contradicciones internas?
- ¿Hay errores de sintaxis en código?
- ¿Hay información inventada/alucinada?
- ¿Es demasiado largo o demasiado corto para lo que se pidió?

Sé honesto. No infles scores."""

INTERPRET_PROMPT = """Eres un reformateador interno. Tu trabajo es adaptar el contenido para el canal indicado.
Reglas según canal:
- discord_embed: máximo {max_chars} caracteres, usar markdown de Discord (**negrita**, `código`, ```bloques```). Si es código largo, priorizar el código sobre la explicación.
- discord_msg: máximo 2000 caracteres. Si excede, cortar con "..." al final.
- telegram: formato plano, sin embeds. Usar markdown de Telegram (*negrita*, `código`).
- vscode: formato técnico, bloques de código con lenguaje indicado.

Devuelve SOLO el texto reformateado. No añadas explicaciones sobre lo que hiciste. No añadas encabezados tipo "Aquí está el texto reformateado:". Solo el contenido."""

QUICK_RESOLVE_PROMPT = """Eres un asistente directo. Responde de forma concisa y útil.
No uses más de 500 palabras. Ve al grano.
Responde en el mismo idioma que el usuario."""


class AlbedoAgent:
    """Guardiana Suprema — agente multi-modelo local (Ollama)."""

    def __init__(self):
        config_path = Path(__file__).parent.parent.parent / "Config" / "albedo.json"
        try:
            with open(config_path) as f:
                self.config = json.load(f)
        except Exception:
            logger.warning("[Albedo] Config no encontrada. Desactivada.")
            self.config = {"enabled": False}

        self.enabled = self.config.get("enabled", False)
        self.ollama_url = self.config.get(
            "ollama_url", "http://localhost:11434/api/chat"
        )
        self.models = self.config.get("models", {})
        self.roles = self.config.get("roles", {})

    # ─── Prompts desde PersonaLoader ───

    def _get_project_root(self) -> Path:
        """Obtiene el path base del proyecto."""
        return Path(__file__).resolve().parent.parent.parent.parent

    def _get_base_persona(self) -> str:
        """Obtiene la identidad base de Albedo desde el persona_loader."""
        try:
            loader = get_persona_loader(self._get_project_root())
            return loader.get_system_prompt("albedo", include_common=True)
        except Exception:
            return "[Albedo — Guardiana Suprema] Agente multi-rol local. Fallback..."

    def _get_shadow_prompt(self) -> str:
        """Prompt para rol Sombra (clasificación)."""
        try:
            loader = get_persona_loader(self._get_project_root())
            agent_config = loader.get_agent_config("albedo")
            custom = agent_config.get("shadow_prompt", "")
            if custom:
                return custom
        except Exception:
            pass
        return SHADOW_PROMPT

    def _get_scribe_prompt(self) -> str:
        """Prompt para rol Escriba (documentación)."""
        try:
            loader = get_persona_loader(self._get_project_root())
            agent_config = loader.get_agent_config("albedo")
            custom = agent_config.get("scribe_prompt", "")
            if custom:
                return custom
        except Exception:
            pass
        return SCRIBE_PROMPT

    def _get_sentinel_prompt(self) -> str:
        """Prompt para rol Centinela (quality control)."""
        try:
            loader = get_persona_loader(self._get_project_root())
            agent_config = loader.get_agent_config("albedo")
            custom = agent_config.get("sentinel_prompt", "")
            if custom:
                return custom
        except Exception:
            pass
        return SENTINEL_PROMPT

    def _get_interpret_prompt(self) -> str:
        """Prompt para rol Intérprete (reformateo)."""
        try:
            loader = get_persona_loader(self._get_project_root())
            agent_config = loader.get_agent_config("albedo")
            custom = agent_config.get("interpret_prompt", "")
            if custom:
                return custom
        except Exception:
            pass
        return INTERPRET_PROMPT

    def _get_quick_resolve_prompt(self) -> str:
        """Prompt para resolución rápida de tareas triviales."""
        try:
            loader = get_persona_loader(self._get_project_root())
            agent_config = loader.get_agent_config("albedo")
            custom = agent_config.get("quick_resolve_prompt", "")
            if custom:
                return custom
        except Exception:
            pass
        return QUICK_RESOLVE_PROMPT

    # ─── Llamada base a Ollama (async) ───

    async def _call_ollama(
        self, model: str, system_prompt: str, user_message: str, timeout: float = 15.0
    ) -> str:
        """Llamada directa a Ollama. Lanza excepción si falla."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self.ollama_url, json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    # ─── Llamada base a Ollama (sync) ───

    def _call_ollama_sync(
        self, model: str, system_prompt: str, user_message: str, timeout: float = 15.0
    ) -> str:
        """Llamada directa a Ollama (síncrona). Lanza excepción si falla."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(self.ollama_url, json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    # ─── Helpers internos ───

    def _clean_json_response(self, raw: str) -> dict:
        """Limpia backticks y parsea JSON. Lanza json.JSONDecodeError si falla."""
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        return json.loads(clean)

    async def _safe_call(
        self, role: str, model: str, system: str, message: str, timeout: float = 15.0
    ) -> Optional[dict]:
        """Llamada async segura que retorna dict o None. NUNCA rompe el pipeline."""
        if not self.enabled:
            return None
        if not self.roles.get(f"{role}_enabled", False):
            return None
        try:
            response = await asyncio.wait_for(
                self._call_ollama(model, system, message, timeout),
                timeout=timeout + 5,
            )
            parsed = self._clean_json_response(response)
            if not isinstance(parsed, dict):
                raise ValueError("Respuesta LLM no es un dict")
            return parsed
        except json.JSONDecodeError:
            logger.warning("[Albedo:%s] Respuesta no es JSON válido.", role)
            return None
        except asyncio.TimeoutError:
            logger.warning("[Albedo:%s] Timeout (%.0fs).", role, timeout)
            return None
        except Exception as e:
            logger.warning("[Albedo:%s] Error: %s", role, e)
            return None

    def _safe_call_sync(
        self, role: str, model: str, system: str, message: str, timeout: float = 15.0
    ) -> Optional[dict]:
        """Llamada síncrona segura que retorna dict o None. NUNCA rompe el pipeline."""
        if not self.enabled:
            return None
        if not self.roles.get(f"{role}_enabled", False):
            return None
        try:
            response = self._call_ollama_sync(model, system, message, timeout)
            parsed = self._clean_json_response(response)
            if not isinstance(parsed, dict):
                raise ValueError("Respuesta LLM no es un dict")
            return parsed
        except json.JSONDecodeError:
            logger.warning("[Albedo:%s] Respuesta no es JSON válido.", role)
            return None
        except Exception as e:
            logger.warning("[Albedo:%s] Error: %s", role, e)
            return None

    async def _safe_call_text(
        self, role: str, model: str, system: str, message: str, timeout: float = 15.0
    ) -> Optional[str]:
        """Llamada async segura que retorna texto. Para Intérprete y Quick."""
        if not self.enabled:
            return None
        if not self.roles.get(f"{role}_enabled", False):
            return None
        try:
            response = await asyncio.wait_for(
                self._call_ollama(model, system, message, timeout),
                timeout=timeout + 5,
            )
            return response.strip()
        except Exception as e:
            logger.warning("[Albedo:%s] Error: %s", role, e)
            return None

    def _safe_call_text_sync(
        self, role: str, model: str, system: str, message: str, timeout: float = 15.0
    ) -> Optional[str]:
        """Llamada síncrona segura que retorna texto."""
        if not self.enabled:
            return None
        if not self.roles.get(f"{role}_enabled", False):
            return None
        try:
            return self._call_ollama_sync(model, system, message, timeout).strip()
        except Exception as e:
            logger.warning("[Albedo:%s] Error: %s", role, e)
            return None

    # ─── ROL 1: SOMBRA (pre-procesamiento) ───

    async def shadow_classify(
        self, user_message: str, context_summary: str = ""
    ) -> Optional[dict]:
        """
        Clasifica complejidad y recomienda agente. Retorna None si falla.
        Llamar ANTES del Planner/Orchestrator.

        Retorna: {"complexity": str, "recommended_agent": str, "reason": str, "compressed_context": str}
        """
        timeout = self.config.get("shadow", {}).get("timeout", 10)
        prompt = user_message
        if context_summary:
            prompt = f"Contexto previo: {context_summary}\n\nMensaje del usuario: {user_message}"
        return await self._safe_call(
            role="shadow",
            model=self.models.get("shadow", "llama3.2"),
            system=self._get_shadow_prompt(),
            message=prompt,
            timeout=timeout,
        )

    def shadow_classify_sync(
        self, user_message: str, context_summary: str = ""
    ) -> Optional[dict]:
        """Versión síncrona de shadow_classify. Para uso desde orchestrator.py."""
        timeout = self.config.get("shadow", {}).get("timeout", 10)
        prompt = user_message
        if context_summary:
            prompt = f"Contexto previo: {context_summary}\n\nMensaje del usuario: {user_message}"
        return self._safe_call_sync(
            role="shadow",
            model=self.models.get("shadow", "llama3.2"),
            system=self._get_shadow_prompt(),
            message=prompt,
            timeout=timeout,
        )

    async def quick_resolve(self, user_message: str) -> Optional[str]:
        """
        Resuelve tareas triviales localmente. Retorna None si falla.
        Solo usar si shadow_classify retornó complexity="trivial".
        """
        if not self.config.get("shadow", {}).get("trivial_resolve_locally", True):
            return None
        return await self._safe_call_text(
            role="shadow",
            model=self.models.get("quick", "llama3.2"),
            system=self._get_quick_resolve_prompt(),
            message=user_message,
            timeout=15,
        )

    def quick_resolve_sync(self, user_message: str) -> Optional[str]:
        """Versión síncrona de quick_resolve. Para uso desde orchestrator.py."""
        if not self.config.get("shadow", {}).get("trivial_resolve_locally", True):
            return None
        return self._safe_call_text_sync(
            role="shadow",
            model=self.models.get("quick", "llama3.2"),
            system=self._get_quick_resolve_prompt(),
            message=user_message,
            timeout=15,
        )

    # ─── ROL 2: ESCRIBA (memoria y documentación) ───

    async def scribe_process(
        self,
        user_message: str,
        assistant_response: str,
        agent_used: str = "lilith",
        execution_time: float = 0.0,
    ) -> Optional[dict]:
        """
        Documenta la interacción. Retorna None si falla.
        Llamar DESPUÉS de responder al usuario (fire-and-forget).

        Retorna: {"episode_summary": str, "facts": list, "learning": str|null, "tags": list}
        """
        timeout = self.config.get("scribe", {}).get("timeout", 20)
        message = (
            f"Agente que respondió: {agent_used}\n"
            f"Tiempo de ejecución: {execution_time:.1f}s\n\n"
            f"Usuario dijo: {user_message}\n\n"
            f"Respuesta: {assistant_response[:2000]}"
        )
        return await self._safe_call(
            role="scribe",
            model=self.models.get("scribe", "qwen2.5-coder:7b"),
            system=self._get_scribe_prompt(),
            message=message,
            timeout=timeout,
        )

    def scribe_process_sync(
        self,
        user_message: str,
        assistant_response: str,
        agent_used: str = "lilith",
        execution_time: float = 0.0,
    ) -> Optional[dict]:
        """Versión síncrona de scribe_process. Para uso desde hilos background."""
        timeout = self.config.get("scribe", {}).get("timeout", 20)
        message = (
            f"Agente que respondió: {agent_used}\n"
            f"Tiempo de ejecución: {execution_time:.1f}s\n\n"
            f"Usuario dijo: {user_message}\n\n"
            f"Respuesta: {assistant_response[:2000]}"
        )
        return self._safe_call_sync(
            role="scribe",
            model=self.models.get("scribe", "qwen2.5-coder:7b"),
            system=self._get_scribe_prompt(),
            message=message,
            timeout=timeout,
        )

    # ─── ROL 3: CENTINELA (quality control) ───

    async def sentinel_review(
        self,
        original_task: str,
        agent_output: str,
        agent_name: str = "unknown",
    ) -> Optional[dict]:
        """
        Revisa calidad del output de un agente. Retorna None si falla.
        Llamar DESPUÉS de que el agente responda, ANTES de enviar al usuario.

        Retorna: {"score": int, "issues": list, "notes": str}
        """
        timeout = self.config.get("sentinel", {}).get("timeout", 15)
        message = (
            f"Agente: {agent_name}\n\n"
            f"Tarea original: {original_task}\n\n"
            f"Output del agente:\n{agent_output[:3000]}"
        )
        return await self._safe_call(
            role="sentinel",
            model=self.models.get("sentinel", "dolphin-mistral"),
            system=self._get_sentinel_prompt(),
            message=message,
            timeout=timeout,
        )

    def sentinel_review_sync(
        self,
        original_task: str,
        agent_output: str,
        agent_name: str = "unknown",
    ) -> Optional[dict]:
        """Versión síncrona de sentinel_review. Para uso desde plan_executor.py."""
        timeout = self.config.get("sentinel", {}).get("timeout", 15)
        message = (
            f"Agente: {agent_name}\n\n"
            f"Tarea original: {original_task}\n\n"
            f"Output del agente:\n{agent_output[:3000]}"
        )
        return self._safe_call_sync(
            role="sentinel",
            model=self.models.get("sentinel", "dolphin-mistral"),
            system=self._get_sentinel_prompt(),
            message=message,
            timeout=timeout,
        )

    # ─── ROL 4: INTÉRPRETE (reformateo) ───

    async def interpret_for_channel(
        self,
        content: str,
        channel: str = "discord_embed",
        max_chars: int = 4096,
    ) -> Optional[str]:
        """
        Reformatea contenido para el canal de salida. Retorna None si falla (usar contenido original).
        Llamar ANTES de enviar la respuesta al canal.

        Canales: "discord_embed", "discord_msg", "telegram", "vscode"
        Solo interviene si len(content) > max_chars.
        """
        if len(content) <= max_chars:
            return None  # señal de "no necesita reformateo"

        timeout = self.config.get("interpret", {}).get("timeout", 10)
        system = self._get_interpret_prompt().replace("{max_chars}", str(max_chars))
        message = f"Canal: {channel}\nMáximo: {max_chars} caracteres\n\nContenido a reformatear:\n{content}"

        return await self._safe_call_text(
            role="interpret",
            model=self.models.get("interpret", "llama3.2"),
            system=system,
            message=message,
            timeout=timeout,
        )

    # ─── Health check ───

    async def is_available(self) -> bool:
        """Verifica si Ollama está disponible. Útil para diagnóstico."""
        if not self.enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    self.ollama_url.replace("/api/chat", "/api/tags")
                )
                return resp.status_code == 200
        except Exception:
            return False
