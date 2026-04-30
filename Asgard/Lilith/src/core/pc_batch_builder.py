"""
PCBatchBuilder — Construye batches de operaciones PC con preview, risk scoring y tokens.
Parte del PC Agent end-to-end para Telegram.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.core.planner import Step

logger = logging.getLogger("lilith.pc_batch")


@dataclass
class PCOperationSummary:
    """Resumen de una operación PC para mostrar al usuario."""

    step_num: int
    tool_name: str
    emoji: str
    description: str
    risk: str


class PCBatchBuilder:
    """
    Construye batches de operaciones PC con preview formateado,
    risk scoring y tokens de confirmación.
    """

    RISK_MAP = {
        "pc_list": "low",
        "pc_mkdir": "low",
        "pc_copy": "medium",
        "pc_move": "medium",
        "pc_delete": "high",
        "pc_write_file": "medium",
        "pc_exec": "high",
    }

    EMOJI_MAP = {
        "pc_list": "📁",
        "pc_mkdir": "📂",
        "pc_move": "📦",
        "pc_copy": "📄",
        "pc_delete": "🗑️",
        "pc_write_file": "✏️",
        "pc_exec": "⚡",
    }

    LABEL_MAP = {
        "pc_list": "Listar",
        "pc_mkdir": "Crear carpeta",
        "pc_move": "Mover",
        "pc_copy": "Copiar",
        "pc_delete": "Eliminar",
        "pc_write_file": "Escribir archivo",
        "pc_exec": "Ejecutar comando",
    }

    # TTL para tokens de confirmación (segundos)
    TOKEN_TTL = 120  # 2 minutos

    def __init__(self):
        self._pending_batches: Dict[str, Dict[str, Any]] = {}

    def build_preview(self, steps: List[Step]) -> str:
        """
        Genera un preview legible para Telegram.

        Returns:
            String formateado con emojis y descripciones.
        """
        if not steps:
            return "⚠️ No hay operaciones para ejecutar."

        total = len(steps)
        lines = [
            f"📋 Plan de ejecución ({total} operación{'es' if total > 1 else ''}):",
            "",
        ]

        for i, step in enumerate(steps, 1):
            summary = self._summarize_step(step, i)
            lines.append(f"{summary.emoji} {i}. {summary.description}")

        # Añadir warning si hay operaciones de riesgo
        risk = self.compute_risk(steps)
        lines.append("")

        if risk == "high":
            lines.append(
                "⚠️ **Riesgo alto:** Incluye eliminación o ejecución de comandos."
            )
        elif risk == "medium":
            lines.append("⚡ Riesgo medio: Modifica archivos/carpetas.")
        else:
            lines.append("✅ Riesgo bajo: Solo lectura o creación segura.")

        return "\n".join(lines)

    def _summarize_step(self, step: Step, step_num: int) -> PCOperationSummary:
        """Genera un resumen legible de un step."""
        tool = step.tool_name
        params = step.params or {}
        emoji = self.EMOJI_MAP.get(tool, "🔧")
        risk = self.RISK_MAP.get(tool, "medium")
        label = self.LABEL_MAP.get(tool, tool.replace("pc_", ""))

        # Construir descripción específica según operación
        if tool == "pc_list":
            desc = f"{label}: `{params.get('path', '...')}`"
        elif tool == "pc_mkdir":
            desc = f"{label}: `{params.get('path', '...')}`"
        elif tool == "pc_move":
            src = params.get("source", "...")
            dst = params.get("destination", "...")
            desc = f"{label}: `{src}` → `{dst}`"
        elif tool == "pc_copy":
            src = params.get("source", "...")
            dst = params.get("destination", "...")
            desc = f"{label}: `{src}` → `{dst}`"
        elif tool == "pc_delete":
            desc = f"{label}: `{params.get('path', '...')}`"
        elif tool == "pc_write_file":
            desc = f"{label}: `{params.get('path', '...')}`"
        elif tool == "pc_exec":
            cmd = params.get("command", "...")
            desc = f"{label}: `{cmd[:50]}{'...' if len(str(cmd)) > 50 else ''}`"
        else:
            desc = f"{label}"

        return PCOperationSummary(
            step_num=step_num, tool_name=tool, emoji=emoji, description=desc, risk=risk
        )

    def compute_risk(self, steps: List[Step]) -> str:
        """
        Calcula el nivel de riesgo de un batch.

        Returns:
            "low", "medium" o "high" (basado en la operación más peligrosa)
        """
        max_risk = "low"
        risk_priority = {"low": 0, "medium": 1, "high": 2}

        for step in steps:
            tool_risk = self.RISK_MAP.get(step.tool_name, "medium")
            if risk_priority.get(tool_risk, 0) > risk_priority.get(max_risk, 0):
                max_risk = tool_risk

        return max_risk

    def needs_confirmation(self, steps: List[Step]) -> bool:
        """
        Determina si el batch necesita confirmación.
        Solo pc_list no necesita confirmación (solo lectura).
        """
        # Si todas son pc_list, no necesita confirmación
        return not all(s.tool_name == "pc_list" for s in steps)

    def generate_batch_token(self, steps: List[Step], chat_id: str) -> str:
        """
        Genera un token único para este batch.
        El token se usa para confirmar/cancelar la ejecución.
        """
        # Crear un hash único del batch
        batch_data = {
            "steps": [{"tool": s.tool_name, "params": s.params} for s in steps],
            "chat_id": chat_id,
            "timestamp": time.time(),
        }
        batch_str = json.dumps(batch_data, sort_keys=True)
        token = hashlib.sha256(batch_str.encode()).hexdigest()[:16]

        # Guardar batch pendiente
        self._pending_batches[token] = {
            "steps": steps,
            "chat_id": chat_id,
            "created_at": time.time(),
            "risk": self.compute_risk(steps),
            "executed": False,
        }

        logger.debug("PCBatch: token %s creado para %d steps", token, len(steps))
        return token

    def get_pending_batch(self, token: str) -> Optional[Dict[str, Any]]:
        """Obtiene un batch pendiente por token. Verifica TTL."""
        batch = self._pending_batches.get(token)
        if not batch:
            return None

        # Verificar TTL
        if time.time() - batch["created_at"] > self.TOKEN_TTL:
            logger.warning("PCBatch: token %s expirado", token)
            del self._pending_batches[token]
            return None

        # Verificar si ya fue ejecutado
        if batch.get("executed"):
            logger.warning("PCBatch: token %s ya ejecutado", token)
            del self._pending_batches[token]
            return None

        return batch

    def mark_executed(self, token: str) -> bool:
        """Marca un batch como ejecutado."""
        batch = self._pending_batches.get(token)
        if batch:
            batch["executed"] = True
            logger.info("PCBatch: token %s ejecutado", token)
            return True
        return False

    def cleanup_expired(self) -> int:
        """Limpia batches expirados. Retorna cantidad limpiados."""
        now = time.time()
        expired = [
            token
            for token, batch in self._pending_batches.items()
            if (now - batch["created_at"] > self.TOKEN_TTL) or batch.get("executed")
        ]
        for token in expired:
            del self._pending_batches[token]

        if expired:
            logger.debug("PCBatch: limpiados %d tokens expirados", len(expired))
        return len(expired)


# Singleton global
_batch_builder: Optional[PCBatchBuilder] = None


def get_batch_builder() -> PCBatchBuilder:
    """Obtiene el singleton de PCBatchBuilder."""
    global _batch_builder
    if _batch_builder is None:
        _batch_builder = PCBatchBuilder()
    return _batch_builder
