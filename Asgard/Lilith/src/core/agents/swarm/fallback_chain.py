"""
FallbackChain — Cadena de fallback configurable para agentes.
Lee la configuración de Core/Config/agents.json y determina el siguiente
agente a intentar cuando el primario falla.
Integrar en AgentCaller para cambiar de herramienta de forma transparente.
"""
import logging
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("lilith.fallback_chain")


def _load_cfg(base_path: Path) -> dict:
    try:
        from src.core.json_safe import safe_load

        return safe_load(base_path / "Config" / "agents.json", default={})
    except Exception:
        return {}


class FallbackChain:
    """
    Determina la cadena de alternativas para un tool/agente.

    Uso:
        chain = FallbackChain(base_path)
        next_tool = chain.next_after(failed_tool, error_msg)
        # None si no hay más alternativas
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._attempt_counts: dict = {}  # tool_name → intentos en esta sesión

    def _cfg(self) -> dict:
        return _load_cfg(self.base_path)

    def _is_fallback_error(self, error_msg: str, patterns: List[str]) -> bool:
        """Devuelve True si el mensaje de error coincide con algún patrón de fallback."""
        if not error_msg:
            return False
        low = error_msg.lower()
        for pat in patterns:
            if pat.lower() in low:
                return True
        return False

    def should_fallback(self, tool_name: str, error_msg: str = "") -> bool:
        """
        Decide si debe activarse el fallback para este tool y error.
        Siempre True si hay error y el tool tiene cadena; respeta max_fallback_attempts.
        """
        cfg = self._cfg()
        chains = cfg.get("fallback_chains") or {}
        if tool_name not in chains:
            return False
        max_attempts = int(cfg.get("max_fallback_attempts") or 3)
        attempts = self._attempt_counts.get(tool_name, 0)
        if attempts >= max_attempts:
            logger.debug("fallback_chain: max_attempts alcanzado para %s", tool_name)
            return False
        patterns = cfg.get("fallback_error_patterns") or []
        if patterns and error_msg:
            return self._is_fallback_error(error_msg, patterns)
        return bool(error_msg)  # cualquier error activa fallback si hay cadena

    def next_after(
        self, original_tool: str, error_msg: str = "", tried: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Devuelve el siguiente tool a intentar en la cadena de fallback.
        `tried`: lista de tools ya intentados (evita repetir).
        Retorna None si no hay más alternativas.
        """
        if not self.should_fallback(original_tool, error_msg):
            return None
        cfg = self._cfg()
        chains = cfg.get("fallback_chains") or {}
        alternatives = chains.get(original_tool) or []
        already_tried = set(tried or [original_tool])
        for candidate in alternatives:
            if candidate not in already_tried:
                self._attempt_counts[original_tool] = (
                    self._attempt_counts.get(original_tool, 0) + 1
                )
                logger.info(
                    "fallback_chain: %s falló (%s) → intentando %s",
                    original_tool,
                    (error_msg or "")[:60],
                    candidate,
                )
                return candidate
        logger.debug("fallback_chain: sin alternativas para %s", original_tool)
        return None

    def reset(self, tool_name: Optional[str] = None) -> None:
        """Reinicia contadores. Sin argumento, reinicia todos."""
        if tool_name:
            self._attempt_counts.pop(tool_name, None)
        else:
            self._attempt_counts.clear()

    def get_chain(self, tool_name: str) -> List[str]:
        """Devuelve la cadena completa definida para un tool (sin el primario)."""
        cfg = self._cfg()
        return list((cfg.get("fallback_chains") or {}).get(tool_name) or [])
