"""
Crystal Agent - Asistente pública para canales Discord

Crystal es la cara pública de Lilith. Tiene personalidad propia, sin acceso a
herramientas peligrosas ni información sensible.

v4.2: Usa Kimi API directamente (no OpenRouter)
v4.2.4: Agregado sistema de aprendizaje de FAQs
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CrystalAgent:
    """
    Agente Crystal - Asistente pública

    Características:
    - Kimi API como backend principal (directo, no OpenRouter)
    - Fallback a Ollama local
    - Sin acceso a herramientas peligrosas
    - Memoria aislada (solo discord_public)
    - Aprendizaje de FAQs (v4.2.4)
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Args:
            config_path: Ruta al crystal.json con configuración
        """
        # Cargar config
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            # Config por defecto
            self.config = {
                "enabled": True,
                "system_prompt_base": "Eres Crystal, asistente pública de Lilith.",
                "allowed_tools": ["web_search", "charla", "chiste", "meme"],
                "forbidden_tools": [],
                "memory_isolation": {
                    "excluded_tags": [
                        "telegram",
                        "pc_ops",
                        "owner",
                        "sensitive",
                        "internal",
                    ],
                    "vault": "discord_public",
                },
                "kimi_model": "kimi-for-coding",
                "learning": {
                    "enabled": True,
                    "min_hits_to_learn": 2,
                    "similarity_threshold": 0.85,
                    "max_faqs": 100,
                },
            }

        self.allowed_tools = set(self.config.get("allowed_tools", []))
        self.forbidden_tools = set(self.config.get("forbidden_tools", []))
        self.excluded_tags = set(self.config["memory_isolation"]["excluded_tags"])
        self.vault = self.config["memory_isolation"]["vault"]

        # Inicializar sistema de aprendizaje (v4.2.4)
        self._init_learning()

        # Inicializar cliente Kimi
        self._init_kimi_client()

    def _init_kimi_client(self):
        """Inicializar cliente Kimi con API key de Crystal"""
        try:
            from ...llm.kimi_client import KimiClient

            # Intentar obtener API key específica de Crystal
            api_key = os.environ.get("CRYSTAL_KIMI_API_KEY")

            # Fallback a KIMI_API_KEY general si no hay específica
            if not api_key:
                api_key = os.environ.get("KIMI_API_KEY")

            if api_key:
                self.kimi_client = KimiClient(api_key=api_key)
                logger.info("Crystal: Kimi client initialized")
            else:
                self.kimi_client = None
                logger.warning("Crystal: No Kimi API key found")

        except Exception as e:
            logger.error(f"Crystal: Failed to initialize Kimi client: {e}")
            self.kimi_client = None

    def _init_learning(self):
        """Inicializar sistema de aprendizaje de FAQs (v4.2.4)"""
        try:
            from .crystal_learning import CrystalLearning

            learning_config = self.config.get("learning", {})

            if learning_config.get("enabled", True):
                self.learning = CrystalLearning(
                    min_hits_to_learn=learning_config.get("min_hits_to_learn", 2),
                    similarity_threshold=learning_config.get(
                        "similarity_threshold", 0.85
                    ),
                    max_faqs=learning_config.get("max_faqs", 100),
                )
                logger.info("Crystal Learning: Initialized")
            else:
                self.learning = None

        except Exception as e:
            logger.warning(f"Crystal Learning: Failed to initialize: {e}")
            self.learning = None

    def get_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Construir system prompt para Crystal

        Args:
            context: Contexto adicional (memoria, usuario, etc.)

        Returns:
            System prompt completo
        """
        base = self.config.get("system_prompt_base", "")

        prompt_parts = [base]

        # Agregar restricciones de herramientas
        prompt_parts.append("\n## Herramientas disponibles")
        prompt_parts.append(f"Tienes acceso SOLO a: {', '.join(self.allowed_tools)}")
        prompt_parts.append(
            f"\nNO PUEDES usar: operaciones de sistema, archivos, PC Agent, agentes especializados."
        )

        # Contexto de memoria (si hay)
        if context and "memory_facts" in context:
            facts = context["memory_facts"]
            if facts:
                prompt_parts.append("\n## Contexto relevante")
                for fact in facts[:10]:  # Máximo 10 hechos
                    prompt_parts.append(f"- {fact}")

        # Guías de respuesta
        prompt_parts.append("\n## Guías de respuesta")
        prompt_parts.append("- Sé amigable y profesional")
        prompt_parts.append("- Mantén respuestas concisas (< 2000 chars)")
        prompt_parts.append("- No reveles detalles de implementación interna")
        prompt_parts.append(
            "- Si te piden algo fuera de tus capacidades, explica cortésmente tus limitaciones"
        )

        return "\n".join(prompt_parts)

    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        openrouter_client=None,  # Deprecated, kept for compatibility
        ollama_client=None,
    ) -> Dict[str, Any]:
        """
        Procesar mensaje usando Cache → FAQs → Kimi API → Ollama fallback

        v4.2.8: Agregado caché multi-nivel antes de FAQs
        v4.2.4: Agregado paso de FAQs antes de llamar a la API

        Args:
            message: Mensaje del usuario
            context: Contexto (memoria, etc.)
            openrouter_client: Deprecated, no longer used
            ollama_client: Cliente Ollama para fallback

        Returns:
            Dict con response, success, backend usado
        """
        # v4.2.8: Verificar caché multi-nivel primero
        cache_key = None
        try:
            from src.core.cache import get_cache

            cache = get_cache()
            cache_key = f"crystal:{hash(message)}"
            cached_response = await cache.get(cache_key, namespace="agent_responses")
            if cached_response:
                logger.info("Crystal: L1/L2 cache hit")
                return {
                    "success": True,
                    "response": cached_response,
                    "backend": "cache",
                    "cached": True,
                    "cache_level": "L1",  # o L2 dependiendo de dónde vino
                }
        except Exception as e:
            logger.debug("Crystal: Cache lookup failed: %s", e)

        # v4.2.4: Verificar FAQs
        if self.learning:
            try:
                cached = await self.learning.find_similar_faq(message)
                if cached and cached.get("found"):
                    logger.info(
                        "Crystal: FAQ cache hit (confidence=%.2f, hits=%d)",
                        cached.get("confidence", 0),
                        cached.get("hit_count", 0),
                    )
                    return {
                        "success": True,
                        "response": cached["response"],
                        "backend": "faq_cache",
                        "cached": True,
                        "confidence": cached.get("confidence"),
                        "hit_count": cached.get("hit_count"),
                    }
            except Exception as e:
                logger.debug("Crystal: FAQ lookup failed: %s", e)

        system_prompt = self.get_system_prompt(context=context)

        # Intentar Kimi primero
        backend_used = "none"
        response_text = ""

        if self.kimi_client:
            try:
                result = self._chat_with_kimi(
                    message=message, system_prompt=system_prompt
                )

                if result:
                    response_text = result
                    backend_used = "kimi"

            except Exception as e:
                logger.error(f"Kimi API error: {e}")

        # Fallback a Ollama local
        if not response_text and ollama_client:
            try:
                logger.info("Falling back to Ollama local")

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ]

                result = await ollama_client.chat(
                    model="llama3.2:latest", messages=messages
                )

                response_text = result["message"]["content"]
                backend_used = "ollama_local"

            except Exception as e:
                logger.error(f"Ollama local fallback failed: {e}")

        # Si tuvimos respuesta, procesar
        if response_text:
            # v4.2.8: Guardar en caché multi-nivel
            if cache_key:
                try:
                    from src.core.cache import get_cache

                    cache = get_cache()
                    await cache.set(
                        cache_key,
                        response_text,
                        namespace="agent_responses",
                        ttl=600,  # 10 minutos para respuestas de agente
                        tags={"crystal", "llm_response"},
                    )
                    logger.debug("Crystal: Response cached (L1/L2)")
                except Exception as e:
                    logger.debug("Crystal: Cache store failed: %s", e)

            # v4.2.4: Aprender de esta interacción
            if self.learning and backend_used in ("kimi", "ollama_local"):
                try:
                    await self.learning.learn_from_interaction(
                        question=message, response=response_text, backend=backend_used
                    )
                except Exception as e:
                    logger.debug("Crystal: Learning failed: %s", e)

            return {
                "success": True,
                "response": response_text,
                "backend": backend_used,
                "model": self.config.get("kimi_model", "kimi-for-coding")
                if backend_used == "kimi"
                else "llama3.2:latest",
                "used_fallback": backend_used == "ollama_local",
                "cached": False,
            }

        # Todo falló
        return {
            "success": False,
            "response": "🔮 Disculpa, tengo dificultades técnicas en este momento. Intenta de nuevo en unos momentos.",
            "backend": "none",
            "error": "All backends failed",
        }

    def _chat_with_kimi(self, message: str, system_prompt: str) -> str:
        """
        Chat síncrono con Kimi API

        Args:
            message: Mensaje del usuario
            system_prompt: System prompt completo

        Returns:
            Texto de respuesta
        """
        if not self.kimi_client:
            return ""

        # Usar el método generate_text del KimiClient
        return self.kimi_client.generate_text(
            prompt=message,
            system_prompt=system_prompt,
            model=self.config.get("kimi_model", "kimi-for-coding"),
            max_tokens=2000,
        )

    def filter_memory_facts(self, facts: List[Dict[str, Any]]) -> List[str]:
        """
        Filtrar hechos de memoria para excluir tags sensibles

        Args:
            facts: Lista de hechos con metadata

        Returns:
            Lista de strings con hechos permitidos
        """
        filtered = []

        for fact in facts:
            tags = set(fact.get("tags", []))

            # Excluir si tiene algún tag prohibido
            if tags & self.excluded_tags:
                continue

            # Agregar el contenido
            content = fact.get("content") or fact.get("text")
            if content:
                filtered.append(content)

        return filtered

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Verificar si una herramienta está permitida para Crystal"""
        return tool_name in self.allowed_tools and tool_name not in self.forbidden_tools


# Singleton global
_crystal_agent: Optional[CrystalAgent] = None


def get_crystal_agent(config_path: Optional[Path] = None) -> CrystalAgent:
    """Obtener instancia singleton de Crystal"""
    global _crystal_agent
    if _crystal_agent is None:
        _crystal_agent = CrystalAgent(config_path=config_path)
    return _crystal_agent
