"""
ProgressReporter: Reportes de progreso para tareas autónomas.
Envía notificaciones al owner vía Discord.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

_MODULE_DIR = Path(__file__).resolve().parent
_YGGDRASIL_ROOT = Path(os.environ.get("YGGDRASIL_ROOT", str(_MODULE_DIR.parents[5])))


class ProgressReporter:
    """
    Gestiona reportes de progreso para tareas en AutoMode.

    Características:
    - Reportes periódicos de progreso
    - Notificaciones de errores
    - Solicitudes de aprobación
    - Reporte final al completar
    """

    def __init__(self, task_id: str, config: dict):
        """
        Args:
            task_id: ID de la tarea
            config: Configuración con owner_id, channel_id, etc.
        """
        self.task_id = task_id
        self.owner_id = config.get("owner_id")
        self.channel_id = config.get("channel_id")
        self.api_base_url = config.get("api_url", "http://localhost:8000")

        # Configuración de notificaciones
        self.notifications = config.get(
            "notifications",
            {
                "on_start": True,
                "on_checkpoint": True,
                "on_complete": True,
                "on_error": True,
                "on_approval_needed": True,
            },
        )

    async def send_start_notification(self, objective: str, total_steps: int):
        """
        Notifica inicio de tarea.
        """
        if not self.notifications.get("on_start"):
            return

        message = f"""🔥 **Auto-Mode Iniciado**

**Task ID:** `{self.task_id}`
**Objetivo:** {objective}
**Pasos estimados:** {total_steps}

Reportes cada 4 horas o checkpoints.
Para detener: `/automode stop {self.task_id}`"""

        await self._send_discord_message(message)

    async def send_progress_report(self, current: int, total: int, pct: float):
        """
        Envía reporte de progreso.
        """
        if not self.notifications.get("on_progress", True):
            return

        # Calcular barra de progreso
        bar_length = 20
        filled = int(bar_length * pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        message = f"""📊 **Auto-Mode Progress Report**

**Task:** `{self.task_id}`
**Progreso:** [{bar}] {pct:.1f}%
**Pasos:** {current}/{total}

_Checkpoints guardados en Muspelheim/AutoMode/active/{self.task_id}_"""

        await self._send_discord_message(message)

    async def send_checkpoint_notification(self, step: int):
        """
        Notifica que se guardó un checkpoint.
        """
        if not self.notifications.get("on_checkpoint"):
            return

        message = f"""💾 **Checkpoint Guardado**

**Task:** `{self.task_id}`
**Paso:** {step}

Estado guardado. Se puede reanudar desde aquí si es necesario."""

        await self._send_discord_message(message)

    async def send_final_report(
        self, completed_steps: List[Dict], artifacts: List[str] = None
    ):
        """
        Reporte final al completar tarea.
        """
        if not self.notifications.get("on_complete"):
            return

        duration = self._calculate_duration(completed_steps)
        artifacts_str = "\n".join(f"• `{a}`" for a in (artifacts or [])) or "Ninguno"

        message = f"""✅ **Auto-Mode Completado**

**Task:** `{self.task_id}`
**Total pasos:** {len(completed_steps)}
**Duración:** {duration}

**Artifacts generados:**
{artifacts_str}

**Ubicación:** Muspelheim/AutoMode/completed/{self.task_id}"""

        await self._send_discord_message(message)

    async def report_error(self, step: int, error: str, is_recoverable: bool = True):
        """
        Reporta error durante ejecución.
        """
        if not self.notifications.get("on_error"):
            return

        emoji = "⚠️" if is_recoverable else "❌"
        status = "Error recuperable" if is_recoverable else "Error fatal"

        message = f"""{emoji} **Auto-Mode Error**

**Task:** `{self.task_id}`
**Paso:** {step}
**Tipo:** {status}

```
{error[:500]}
```

{"Checkpoint disponible para recuperación." if is_recoverable else "Tarea movida a 'failed'. Revisar logs."}"""

        await self._send_discord_message(message)

    async def request_approval(self, step: Dict, reason: str = "límites de seguridad"):
        """
        Solicita aprobación para paso bloqueado.
        """
        if not self.notifications.get("on_approval_needed"):
            return

        step_tool = step.get("tool", "unknown")
        step_desc = step.get("description", "Sin descripción")

        message = f"""⏸️ **Auto-Mode: Aprobación Requerida**

**Task:** `{self.task_id}`
**Paso:** {step_tool}
**Razón:** {reason}

**Descripción:**
```
{step_desc[:300]}
```

**Acciones:**
• `/automode approve {self.task_id}` - Continuar
• `/automode skip {self.task_id}` - Saltar este paso
• `/automode stop {self.task_id}` - Detener tarea"""

        await self._send_discord_message(message)

    async def send_delegation_notice(self, step: int, agent: str, reasoning: str):
        """
        Notifica que se delegó un paso a un agente.
        """
        message = f"""🔄 **Auto-Delegación**

**Task:** `{self.task_id}`
**Paso:** {step}
**Delegado a:** `{agent}`

_Razón: {reasoning[:200]}_"""

        await self._send_discord_message(message)

    async def send_security_alert(self, step: int, operation: str, reason: str):
        """
        Alerta de seguridad.
        """
        message = f"""🛡️ **Auto-Mode: Alerta de Seguridad**

**Task:** `{self.task_id}`
**Paso:** {step}
**Operación bloqueada:** `{operation}`

**Razón:** {reason}

Este paso requiere aprobación manual."""

        await self._send_discord_message(message)

    def _calculate_duration(self, completed_steps: List[Dict]) -> str:
        """Calcula duración total de la tarea."""
        if not completed_steps:
            return "Desconocida"

        try:
            # Buscar timestamps
            timestamps = []
            for step in completed_steps:
                ts = step.get("timestamp")
                if ts:
                    timestamps.append(datetime.fromisoformat(ts))

            if len(timestamps) >= 2:
                duration = timestamps[-1] - timestamps[0]
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)

                if hours > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{minutes}m"

        except Exception:
            pass

        return "Desconocida"

    async def _send_discord_message(self, content: str):
        """
        Envía mensaje a Discord vía API de Lilith.
        """
        if not self.channel_id:
            print(
                f"[ProgressReporter] No channel_id configured, skipping: {content[:100]}..."
            )
            return

        url = f"{self.api_base_url}/api/discord/send-message"

        payload = {"channel_id": self.channel_id, "content": content}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        print(f"[ProgressReporter] Message sent to {self.channel_id}")
                    else:
                        print(
                            f"[ProgressReporter] Failed to send: HTTP {response.status}"
                        )
        except Exception as e:
            print(f"[ProgressReporter] Error sending message: {e}")

    def log_to_file(self, message: str, level: str = "INFO"):
        """
        Log local a archivo de progreso.
        """
        log_dir = _YGGDRASIL_ROOT / "Muspelheim" / "AutoMode" / "active" / self.task_id
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / "progress.log"

        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
