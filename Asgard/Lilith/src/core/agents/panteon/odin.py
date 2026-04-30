"""
ODIN - Padre del Conocimiento + Pensador Profundo (Kimi 262k)
Absorbe a Lucifer. Especialidad: analisis masivo Y creativo segun intent.
Motor: Kimi (contexto 262k tokens).
"""
import asyncio
from pathlib import Path

from .base_agent import BaseAgent

# Intent modifiers (anadidos a la persona base)
_INTENT_MODIFIERS = {
    "creative": (
        "\n\n[MODO CREATIVO ACTIVADO]\n"
        "Hoy actuas como pensador creativo y provocador. Explora alternativas no convencionales, "
        "cuestiona supuestos, propone angulos inesperados. Se audaz, util, y ofrece perspectivas "
        "que otros no verian."
    ),
    "analysis": (
        "\n\n[MODO ANALISIS PROFUNDO]\n"
        "Hoy actuas como arquitecto de conocimiento. Analiza exhaustivamente. "
        "Sacrifico tokens por profundidad: estructura tu respuesta en:\n"
        "1) Resumen ejecutivo (3-7 bullets)\n"
        "2) Hallazgos detallados\n"
        "3) Riesgos identificados\n"
        "4) Recomendaciones accionables\n"
        "5) Siguientes pasos sugeridos"
    ),
    "default": "",  # Sin modificador para default
}


class OdinAgent(BaseAgent):
    """
    Odin - El Buscador Supremo. Pensador profundo (creativo + exhaustivo).
    Absorbe a Lucifer. Usa Kimi (contexto 262k).
    """

    name = "Odin"
    description = "Pensador profundo: creativo, exhaustivo o equilibrado segun intent. (Kimi 262k)"

    def __init__(self):
        self._api_key = None
        self._project_root = Path(__file__).resolve().parent.parent.parent.parent

    def _load_api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key
        try:
            secrets_path = self._project_root / "Config" / "secrets.env"
            if secrets_path.exists():
                with open(secrets_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("KIMI_API_KEY="):
                            self._api_key = line.split("=", 1)[1].strip().strip("'\"")
                            return self._api_key or ""
        except Exception:
            pass
        return ""

    def is_available(self) -> bool:
        return bool(self._load_api_key())

    def _get_base_persona(self) -> str:
        """Obtiene la persona de Odin desde personas.json."""
        try:
            from src.core.persona.loader import get_persona_loader

            loader = get_persona_loader(self._project_root)
            return loader.get_system_prompt("odin", include_common=True)
        except Exception:
            # Fallback
            return "[ODIN - Investigador del Panteon]\nEres Odin, el ojo que todo lo ve. Sabio, directo y profundo."

    def get_system_prompt(self, intent: str = "default") -> str:
        """Compone el system prompt: persona base + modificador de intent."""
        base = self._get_base_persona()
        modifier = _INTENT_MODIFIERS.get(intent, "")
        return base + modifier

    async def execute(
        self, task: str, context: str = "", intent: str = "default"
    ) -> str:
        if not self.is_available():
            return "[Odin offline] KIMI_API_KEY no configurada. No puedo procesar la tarea."
        try:
            from pathlib import Path as _Path

            from src.llm.kimi_client import KimiClient

            api_key = self._load_api_key()
            kimi = KimiClient(api_key=api_key or None)
            _bp = _Path(__file__).resolve().parent.parent.parent.parent

            # Mejora-1: leer memoria previa del vault de Odin
            memory_block = ""
            try:
                from src.core.memory.muninn_memory import MuninnMemory

                memory_block = await MuninnMemory(_bp).get_agent_memory("odin", task)
            except Exception:
                pass

            system_prompt = self.get_system_prompt(intent)
            if memory_block:
                system_prompt = system_prompt + "\n\n" + memory_block

            user_content = (
                f"{task}\n\n[Contexto proporcionado]:\n{context}" if context else task
            )
            result = await asyncio.to_thread(
                kimi.generate_text,
                user_content,
                system_prompt=system_prompt,
                max_tokens=8192,
            )
            response = (result or "").strip() or "(Sin respuesta)"

            # Mejora-1: escribir resultado en vault de Odin (fire-and-forget)
            try:
                from src.core.memory.muninn_memory import (
                    MuninnMemory,
                    _run_coro_fire_and_forget,
                )

                _run_coro_fire_and_forget(
                    MuninnMemory(_bp).write_agent_output(
                        "odin", task, response, intent=intent
                    )
                )
            except Exception:
                pass

            return response
        except Exception as e:
            return f"[Odin] Error: {e}"
