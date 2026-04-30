"""
Lilith v2.3 — Fase C: Ejecutor de tareas.
Ejecuta cada subtarea con el agente asignado; on_progress(subtarea_id, estado, resultado).
Cuando el agente es kimi/lilith, AgentRouter no ejecuta — se llama a KimiClient directamente.
Fallback a Kimi si otro agente falla.
"""
import asyncio
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("TaskExecutor")


class TaskExecutor:
    def __init__(self, router=None, task_monitor=None):
        self._router = router
        self._monitor = task_monitor

    def _get_router(self):
        if self._router is None:
            from src.core.agent_router import AgentRouter

            return AgentRouter()
        return self._router

    def _get_monitor(self):
        if self._monitor is None:
            from src.auto_mode.task_monitor import TaskMonitor

            return TaskMonitor()
        return self._monitor

    async def execute(
        self,
        task_id: str,
        plan: Dict[str, Any],
        file_context: Optional[Dict[str, str]] = None,
        on_progress: Optional[Callable[[int, int, str, str, Any], None]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta cada subtarea secuencialmente.
        on_progress(subtarea_id, total, estado, descripcion, resultado).
        Estado: "running" | "done" | "failed".
        Si una subtarea falla → reintentar con kimi.
        """
        router = self._get_router()
        monitor = self._get_monitor()
        subtareas = plan.get("subtareas") or []
        total = len(subtareas)
        file_context = file_context or plan.get("file_context") or {}
        logger.info("[AutoMode] file_context keys: %s", list(file_context.keys()))
        resultados = []

        def progress(st_id: int, estado: str, desc: str, res: Any):
            if on_progress:
                try:
                    on_progress(st_id, total, estado, desc, res)
                except Exception as e:
                    logger.warning("on_progress error: %s", e)
            resultados.append(
                {
                    "subtarea_id": st_id,
                    "estado": estado,
                    "descripcion": desc,
                    "resultado": res,
                }
            )

        for i, st in enumerate(subtareas):
            # Comprobar pausa
            task = monitor.get_task(task_id)
            if task and task.get("estado") == "paused":
                progress(st.get("id", i + 1), "paused", st.get("descripcion", ""), None)
                while True:
                    await asyncio.sleep(0.5)
                    t = monitor.get_task(task_id)
                    if not t or t.get("estado") != "paused":
                        break
                if (
                    monitor.get_task(task_id)
                    and monitor.get_task(task_id).get("estado") == "failed"
                ):
                    break

            st_id = st.get("id", i + 1)
            desc = st.get("descripcion", "")
            agente = (st.get("agente") or "kimi").lower()

            # Construir prompt con contexto de archivos, si existe
            prompt = desc
            if file_context:
                bloques = []
                for fname, content in file_context.items():
                    bloques.append(f"[{fname}]\n{content}")
                prompt = f"{desc}\n\nContexto del archivo:\n" + "\n\n".join(bloques)

            logger.info("[AutoMode] Subtarea %s → agente=%s", st_id, agente)
            logger.info(
                "[AutoMode] Prompt (primeros 200 chars): %s",
                (prompt[:200] if prompt else "(vacío)"),
            )
            if agente == "adan":
                logger.info("[AutoMode] Adán prompt length: %s", len(prompt))

            progress(st_id, "running", desc, None)

            try:
                # kimi/lilith: AgentRouter.execute(agent_name="kimi") no llama al LLM, retorna result=None
                if agente in ("kimi", "lilith"):
                    logger.info("[AutoMode] Llamando Kimi directo...")
                    try:
                        from src.llm.kimi_client import KimiClient

                        kimi = KimiClient()
                        system = "Eres Lilith, orquestadora. Responde de forma directa y útil, sin rodeos."
                        res = await asyncio.to_thread(
                            kimi.generate_text,
                            prompt,
                            system_prompt=system,
                            max_tokens=2048,
                        )
                        if not res:
                            res = "(Sin respuesta de Kimi)"
                        progress(st_id, "done", desc, res)
                    except Exception as e_kimi:
                        logger.error(
                            "[AutoMode] Kimi error: %s", traceback.format_exc()
                        )
                        raise
                else:
                    out = await router.execute(
                        prompt,
                        agent_name=agente,
                        context_tokens=0,
                    )
                    res = out.get("result")
                    if not res:
                        res = "(Sin salida)"
                    if isinstance(res, str) and "[offline]" in res.lower():
                        # Fallback a Kimi directo
                        from src.llm.kimi_client import KimiClient

                        kimi = KimiClient()
                        res = await asyncio.to_thread(
                            kimi.generate_text,
                            prompt,
                            system_prompt="Eres Lilith. Responde de forma directa.",
                            max_tokens=2048,
                        )
                        res = res or "(Fallback Lilith sin salida)"
                    progress(st_id, "done", desc, res)
            except Exception as e:
                logger.warning("Subtarea %s failed: %s", st_id, e)
                if agente in ("kimi", "lilith"):
                    logger.error("[AutoMode] Kimi error: %s", traceback.format_exc())
                try:
                    from src.llm.kimi_client import KimiClient

                    kimi = KimiClient()
                    res = await asyncio.to_thread(
                        kimi.generate_text,
                        prompt,
                        system_prompt="Eres Lilith. Responde brevemente.",
                        max_tokens=1024,
                    )
                    res = res or str(e)
                except Exception as e2:
                    res = str(e2)
                progress(st_id, "failed", desc, res)

        return {
            "task_id": task_id,
            "objetivo": plan.get("objetivo", ""),
            "resultados": resultados,
            "total": total,
        }
