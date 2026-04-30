import asyncio
import json
import logging
from pathlib import Path

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.scheduler")


class TaskScheduler:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._scheduler = None

    def start(self):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        if self._scheduler is not None:
            return
        self._scheduler = AsyncIOScheduler()

        # Cargar tareas programadas
        self._load_scheduled_tasks()
        # Cargar monitores de fuentes
        self._load_source_monitors()
        # Cargar modo proactivo (Muninn activations)
        self._load_proactive()
        # Consolidador de aprendizaje (cada 6h)
        self._load_learning_consolidator()
        # Cleanup episódico (diario), purge ChromaDB (semanal), session summarizer (cada 15 min)
        self._load_memory_maintenance()
        self._load_session_summarizer_job()
        # D.11 Aprendizaje activo: job diario de detección de patrones
        self._load_pattern_analysis_job()
        # A.1 Auto-recovery: monitoreo periódico de subsistemas críticos
        self._load_auto_recovery_job()
        # A.3 Backup: snapshot diario automático + verificación semanal
        self._load_backup_job()
        self._load_backup_verify_job()

        self._scheduler.start()
        logger.info("TaskScheduler iniciado.")

    def list_jobs(self) -> str:
        """Devuelve JSON string con jobs y metadatos."""
        import json as _json

        if not self._scheduler:
            return _json.dumps({"jobs": [], "count": 0})
        jobs = self._scheduler.get_jobs()
        out = []
        for j in jobs:
            try:
                out.append(
                    {
                        "id": j.id,
                        "name": j.name,
                        "next_run_time": j.next_run_time.isoformat()
                        if getattr(j, "next_run_time", None)
                        else None,
                        "trigger": str(getattr(j, "trigger", "")),
                        "paused": (j.next_run_time is None),
                    }
                )
            except Exception:
                continue
        return _json.dumps({"jobs": out, "count": len(out)}, ensure_ascii=False)

    def pause_job(self, job_id: str) -> bool:
        if not self._scheduler:
            return False
        try:
            self._scheduler.pause_job(job_id)
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        if not self._scheduler:
            return False
        try:
            self._scheduler.resume_job(job_id)
            return True
        except Exception:
            return False

    def run_now(self, job_id: str) -> bool:
        """Ejecuta el job inmediatamente (sin esperar al trigger)."""
        if not self._scheduler:
            return False
        try:
            job = self._scheduler.get_job(job_id)
            if not job:
                return False
            # Ejecutar la misma función con args actuales en el loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            loop.create_task(job.func(*list(job.args or []), **dict(job.kwargs or {})))
            return True
        except Exception:
            return False

    def stop(self):
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def shutdown(self) -> None:
        """Wrapper async de stop() para compatibilidad con lifespan de FastAPI (await)."""
        self.stop()
        # APScheduler.shutdown(wait=False) es síncrono; no hay pasos async pendientes.

    def _load_scheduled_tasks(self):
        tasks = safe_load(
            self.base_path / "Config" / "scheduled_tasks.json", default=[]
        )
        if not isinstance(tasks, list) or not self._scheduler:
            return
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if not task.get("enabled"):
                continue
            cron = str(task.get("cron", "0 9 * * *"))
            self._scheduler.add_job(
                self._run_task,
                trigger="cron",
                args=[task],
                id=f"task_{task.get('id')}",
                **self._parse_cron(cron),
                replace_existing=True,
                misfire_grace_time=300,
            )
            logger.info("Tarea cargada: %s (%s)", task.get("id"), cron)

    def _load_source_monitors(self):
        monitors = safe_load(
            self.base_path / "Config" / "source_monitors.json", default=[]
        )
        if not isinstance(monitors, list) or not self._scheduler:
            return
        for monitor in monitors:
            if not isinstance(monitor, dict):
                continue
            if not monitor.get("enabled"):
                continue
            interval = int(monitor.get("interval_minutes", 15))
            self._scheduler.add_job(
                self._run_monitor,
                trigger="interval",
                args=[monitor],
                id=f"monitor_{monitor.get('id')}",
                minutes=interval,
                replace_existing=True,
                misfire_grace_time=120,
            )
            logger.info(
                "Monitor cargado: %s (cada %d min)", monitor.get("id"), interval
            )

    def _load_proactive(self):
        cfg = safe_load(self.base_path / "Config" / "proactive_mode.json", default={})
        if not isinstance(cfg, dict) or not self._scheduler:
            return
        if not cfg.get("enabled", True):
            return
        try:
            interval = max(5, int(cfg.get("interval_minutes") or 10))
        except Exception:
            interval = 10
        self._scheduler.add_job(
            self._run_proactive,
            trigger="interval",
            args=[],
            id="proactive_mode",
            minutes=interval,
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("Proactivo cargado: proactive_mode (cada %d min)", interval)

    def _load_learning_consolidator(self):
        """Registra el job de consolidación de aprendizaje (cada 6h por defecto)."""
        if not self._scheduler:
            return
        try:
            cfg = safe_load(self.base_path / "Config" / "learning.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
            if not cfg.get("consolidation_enabled", True):
                return
            interval_hours = max(1, int(cfg.get("consolidation_interval_hours", 6)))
            self._scheduler.add_job(
                self._run_learning_consolidator,
                trigger="interval",
                args=[],
                id="learning_consolidation",
                hours=interval_hours,
                replace_existing=True,
                misfire_grace_time=600,
            )
            logger.info("Learning consolidator cargado (cada %dh).", interval_hours)
        except Exception as e:
            logger.debug("Error cargando learning_consolidator: %s", e)

    async def _run_learning_consolidator(self):
        """Ejecuta el consolidador de aprendizaje."""
        logger.info("[Scheduler] Ejecutando learning_consolidation...")
        try:
            from src.core.learning_consolidator import LearningConsolidator

            stats = await asyncio.to_thread(
                LearningConsolidator(self.base_path).consolidate
            )
            logger.info("[Scheduler] learning_consolidation: %s", stats)
        except Exception as e:
            logger.warning("[Scheduler] Error en learning_consolidation: %s", e)

    def _load_memory_maintenance(self):
        """Registra jobs de mantenimiento de memoria: cleanup episódico (diario) y purge ChromaDB (semanal)."""
        if not self._scheduler:
            return
        # Cleanup episódico — cada día a las 03:00
        self._scheduler.add_job(
            self._run_episodic_cleanup,
            trigger="cron",
            hour=3,
            minute=0,
            id="episodic_cleanup",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Purge ChromaDB decaído — cada lunes a las 04:00
        self._scheduler.add_job(
            self._run_chromadb_purge,
            trigger="cron",
            day_of_week="mon",
            hour=4,
            minute=0,
            id="chromadb_purge",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info(
            "Memory maintenance jobs registrados (episodic_cleanup diario, chromadb_purge semanal)."
        )

    def _load_session_summarizer_job(self):
        """Registra el job de revisión de inactividad de sesión (cada 15 min)."""
        if not self._scheduler:
            return
        self._scheduler.add_job(
            self._run_session_summarizer_check,
            trigger="interval",
            minutes=15,
            id="session_summarizer_check",
            replace_existing=True,
            misfire_grace_time=120,
        )
        logger.info("Session summarizer check job registrado (cada 15 min).")

    async def _run_session_summarizer_check(self):
        """Genera resúmenes para canales inactivos."""
        try:
            from src.core.memory.legacy_adapter import EpisodicStore
            from src.core.session_summarizer import get_session_summarizer

            summarizer = get_session_summarizer(self.base_path)
            store = EpisodicStore(self.base_path)
            summaries = await summarizer.check_inactivity_and_summarize(store)
            if summaries:
                logger.info(
                    "[Scheduler] session_summarizer: %d resúmenes generados",
                    len(summaries),
                )
        except Exception as e:
            logger.warning("[Scheduler] Error en session_summarizer_check: %s", e)

    async def _run_episodic_cleanup(self):
        """Poda episodios viejos. ANTES de purgar, genera resumen pre-purge."""
        logger.info("[Scheduler] Ejecutando episodic_cleanup...")
        try:
            cfg = safe_load(self.base_path / "Config" / "memory.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
            max_ep = int(cfg.get("episodic_max_episodes") or 5000)
            ret_days = int(cfg.get("episodic_retention_days") or 90)
            from src.core.memory.legacy_adapter import EpisodicStore

            store = EpisodicStore(self.base_path)

            # Pre-purge: resumir antes de eliminar
            try:
                from src.core.session_summarizer import get_session_summarizer

                _, to_purge = await asyncio.to_thread(
                    store.get_purgeable, max_ep, ret_days
                )
                if to_purge:
                    await get_session_summarizer(self.base_path).summarize_before_purge(
                        to_purge
                    )
            except Exception as e:
                logger.debug("[Scheduler] pre-purge summary error: %s", e)

            stats = await asyncio.to_thread(store.cleanup, max_ep, ret_days)
            logger.info("[Scheduler] episodic_cleanup: %s", stats)
        except Exception as e:
            logger.warning("[Scheduler] Error en episodic_cleanup: %s", e)

    async def _run_chromadb_purge(self):
        """Elimina hechos de ChromaDB cuyo decay temporal sea < threshold."""
        logger.info("[Scheduler] Ejecutando chromadb_purge...")
        try:
            cfg = safe_load(self.base_path / "Config" / "memory.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
            threshold = float(cfg.get("vector_decay_purge_threshold") or 0.1)
            half_life = float(cfg.get("vector_decay_half_life_days") or 30.0)
            from src.core.memory.semantic.vector_store import purge_decayed_facts

            removed = await asyncio.to_thread(
                purge_decayed_facts, self.base_path, threshold, half_life
            )
            logger.info("[Scheduler] chromadb_purge: %d hechos eliminados", removed)
        except Exception as e:
            logger.warning("[Scheduler] Error en chromadb_purge: %s", e)

    def _load_pattern_analysis_job(self):
        """D.11 — Registra el job diario de detección de patrones repetitivos."""
        if not self._scheduler:
            return
        try:
            cfg = safe_load(self.base_path / "Config" / "learning.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
            pd_cfg = cfg.get("pattern_detection", {})
            if not pd_cfg.get("enabled", True):
                return
            self._scheduler.add_job(
                self._run_pattern_analysis,
                trigger="cron",
                hour=8,
                minute=30,
                id="pattern_analysis",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Pattern analysis job registrado (diario a las 08:30).")
        except Exception as e:
            logger.debug("Error cargando pattern_analysis_job: %s", e)

    async def _run_pattern_analysis(self):
        """D.11 — Ejecuta PatternDetector y notifica al owner si hay patrones."""
        logger.info("[Scheduler] Ejecutando pattern_analysis...")
        try:
            from src.core.learning.pattern_detector import PatternDetector

            count = await PatternDetector(self.base_path).detect_and_notify()
            logger.info(
                "[Scheduler] pattern_analysis: %d sugerencias generadas.", count
            )
        except Exception as e:
            logger.warning("[Scheduler] Error en pattern_analysis: %s", e)

    def _load_auto_recovery_job(self):
        """A.1 — Job periódico de health check y auto-recuperación."""
        if not self._scheduler:
            return
        try:
            cfg = safe_load(
                self.base_path / "Config" / "auto_recovery.json", default={}
            )
            cfg = cfg if isinstance(cfg, dict) else {}
            if not cfg.get("enabled", True):
                return
            interval_s = max(30, int(cfg.get("check_interval_seconds", 60)))
            self._scheduler.add_job(
                self._run_auto_recovery,
                trigger="interval",
                seconds=interval_s,
                id="auto_recovery",
                replace_existing=True,
                misfire_grace_time=30,
            )
            logger.info("Auto-recovery job registrado (cada %ds).", interval_s)
        except Exception as e:
            logger.debug("Error cargando auto_recovery_job: %s", e)

    async def _run_auto_recovery(self):
        """A.1 — Ejecuta ciclo de health check y recuperación."""
        try:
            from src.core.auto_recovery import AutoRecoveryManager

            result = await AutoRecoveryManager(self.base_path).run_check_cycle()
            if result.get("actions"):
                logger.info("[Scheduler] auto_recovery: %s", result["actions"])
        except Exception as e:
            logger.debug("[Scheduler] Error en auto_recovery: %s", e)

    def _load_backup_job(self):
        """A.3 — Job de backup automático diario."""
        if not self._scheduler:
            return
        try:
            cfg = safe_load(self.base_path / "Config" / "backups.json", default={})
            cfg = cfg if isinstance(cfg, dict) else {}
            if not cfg.get("enabled", True):
                return
            time_str = str(cfg.get("time", "03:00"))
            hour, minute = (int(x) for x in time_str.split(":"))
            self._scheduler.add_job(
                self._run_backup,
                trigger="cron",
                hour=hour,
                minute=minute,
                id="daily_backup",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Backup job registrado (diario a las %s).", time_str)
        except Exception as e:
            logger.debug("Error cargando backup_job: %s", e)

    async def _run_backup(self):
        """A.3 — Crea snapshot diario y notifica al owner si falla."""
        logger.info("[Scheduler] Ejecutando daily_backup...")
        try:
            from src.core.backup_manager import BackupManager

            result = await asyncio.to_thread(
                BackupManager(self.base_path).create_snapshot
            )
            if result.get("ok"):
                logger.info(
                    "[Scheduler] daily_backup: %s (%.1f MB)",
                    result.get("path", "?"),
                    result.get("size_bytes", 0) / 1_048_576,
                )
            else:
                logger.error("[Scheduler] daily_backup falló: %s", result.get("reason"))
                from src.core.transport.discord import notify_owner

                await notify_owner(
                    self.base_path,
                    f"❌ Backup diario falló: {result.get('reason', 'error desconocido')}",
                )
        except Exception as e:
            logger.error("[Scheduler] Error en daily_backup: %s", e)

    def _load_backup_verify_job(self):
        """A.3 — Job semanal de verificación de integridad de backups."""
        if not self._scheduler:
            return
        try:
            self._scheduler.add_job(
                self._run_backup_verify,
                trigger="cron",
                day_of_week="sun",
                hour=5,
                minute=0,
                id="backup_verify",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            logger.info("Backup verify job registrado (domingos 05:00).")
        except Exception as e:
            logger.debug("Error cargando backup_verify_job: %s", e)

    async def _run_backup_verify(self):
        """A.3 — Verifica integridad de todos los snapshots."""
        logger.info("[Scheduler] Ejecutando backup_verify...")
        try:
            from src.core.backup_manager import BackupManager

            result = await asyncio.to_thread(
                BackupManager(self.base_path).verify_all_snapshots
            )
            corrupted = result.get("corrupted", [])
            if corrupted:
                from src.core.transport.discord import notify_owner

                await notify_owner(
                    self.base_path,
                    f"⚠️ Backup verify: {len(corrupted)} snapshot(s) corrupto(s): {', '.join(corrupted[:3])}",
                )
                logger.error(
                    "[Scheduler] backup_verify: snapshots corruptos: %s", corrupted
                )
            else:
                logger.info(
                    "[Scheduler] backup_verify: %d snapshots OK.",
                    result.get("total", 0),
                )
        except Exception as e:
            logger.warning("[Scheduler] Error en backup_verify: %s", e)

    def reload_proactive_mode(self) -> bool:
        """Recarga el job proactivo según config (add/remove)."""
        if not self._scheduler:
            return False
        try:
            cfg = safe_load(
                self.base_path / "Config" / "proactive_mode.json", default={}
            )
            cfg = cfg if isinstance(cfg, dict) else {}
            enabled = bool(cfg.get("enabled", True))
            try:
                self._scheduler.remove_job("proactive_mode")
            except Exception:
                pass
            if enabled:
                self._load_proactive()
            return True
        except Exception:
            return False

    @staticmethod
    def _parse_cron(cron_str: str) -> dict:
        parts = (cron_str or "").split()
        keys = ["minute", "hour", "day", "month", "day_of_week"]
        return {k: v for k, v in zip(keys, parts)}

    async def _run_monitor(self, monitor: dict):
        logger.info("Checking monitor: %s", monitor.get("id"))
        try:
            from src.core.source_monitor import SourceMonitorChecker

            checker = SourceMonitorChecker(self.base_path)
            result = checker.check_v2(monitor)
            if result is None:
                return  # Sin cambio
            if "error" in result:
                logger.warning(
                    "Monitor error %s: %s", monitor.get("id"), result.get("error")
                )
                return

            new_items = result.get("new_items") or []
            field_changes = result.get("changes") or {}

            lines = [f"🌍 **{result.get('description', '')}**"]
            if new_items:
                lines.append(f"\n**{len(new_items)} nuevos ítems:**")
                for item in new_items:
                    lines.append(f"  • {(item.get('text') or '')[:120]}")
            if field_changes:
                lines.append("\n**Campos actualizados:**")
                for k, v in field_changes.items():
                    lines.append(f"  **{k}**: {v.get('before')} → {v.get('after')}")
            msg_raw = "\n".join(lines)

            summary_text = msg_raw
            if new_items and monitor.get("store_fact"):
                try:
                    from src.api.dependencies import get_orchestrator

                    orch = get_orchestrator()
                    items_txt = "\n".join(f"- {i.get('text','')}" for i in new_items)
                    summary_text = await asyncio.to_thread(
                        orch.execute_plan,
                        f"Resume en 3-8 bullets en español estos titulares, sin repetir:\n{items_txt}",
                        context="",
                        user_id="monitor",
                        skip_cache=True,
                    )
                    summary_text = (summary_text or msg_raw).strip()
                    lines.append(f"\n**Resumen:**\n{summary_text}")
                    msg_raw = "\n".join(lines)
                except Exception:
                    summary_text = msg_raw

            from src.core.transport.discord import notify_owner

            await notify_owner(
                self.base_path,
                msg_raw[:1800],
                channel_id=monitor.get("notify_channel") or "",
            )

            from src.core.episode_builder import build_episode
            from src.core.memory.legacy_adapter import EpisodicStore

            EpisodicStore(self.base_path).append(
                build_episode(
                    summary=summary_text[:400],
                    outcome="success",
                    source="monitor",
                    url=monitor.get("url") or "",
                    channel_name=str(monitor.get("id") or ""),
                )
            )

            # Hecho semántico
            if monitor.get("store_fact"):
                try:
                    fact = (
                        f"[{monitor.get('id')}] {monitor.get('description', '')} — "
                        f"{summary_text[:300]}"
                    )
                    from src.core.tools.builtin.memory_tools import (
                        StoreSemanticFactTool,
                    )

                    await asyncio.to_thread(
                        StoreSemanticFactTool(self.base_path).execute,
                        {
                            "fact": fact,
                            "topic": monitor.get("id"),
                            "source_id": monitor.get("url"),
                        },
                    )
                    logger.info(
                        "Hecho semántico guardado para monitor: %s", monitor.get("id")
                    )
                except Exception as e:
                    logger.warning("No se pudo guardar hecho semántico: %s", e)
        except Exception as e:
            logger.exception("Error en monitor %s: %s", monitor.get("id"), e)

    async def _run_task(self, task: dict):
        logger.info("Ejecutando tarea: %s", task.get("id"))
        action = task.get("action", "notify")
        params = task.get("params", {})
        try:
            result_text = await self._dispatch(action, params or {})
            if result_text:
                from src.core.transport.discord import notify_owner

                msg = f"⏰ **Tarea: {task.get('description', task.get('id'))}**\n{str(result_text)[:800]}"
                await notify_owner(
                    self.base_path,
                    msg,
                    channel_id=task.get("notify_channel") or "",
                )

            from src.core.episode_builder import build_episode
            from src.core.memory.legacy_adapter import EpisodicStore

            EpisodicStore(self.base_path).append(
                build_episode(
                    summary=(str(result_text or "")[:400]),
                    outcome="success",
                    source="scheduled_task",
                    channel_name=str(task.get("id") or ""),
                )
            )
        except Exception as e:
            logger.exception("Error en tarea %s: %s", task.get("id"), e)

    async def _dispatch(self, action: str, params: dict) -> str:
        if action == "notify":
            return str(params.get("message", "") or "")

        if action == "daily_briefing":
            # Briefing diario (últimas 24h): episodios + activaciones Muninn
            try:
                import time as _time

                from src.api.dependencies import get_orchestrator
                from src.core.memory.legacy_adapter import EpisodicStore
                from src.core.memory.muninn_memory import MuninnMemory

                since = _time.time() - (24 * 3600)
                eps = EpisodicStore(self.base_path).recent_since(
                    since_ts=since, limit=40
                )
                eps_lines = []
                for e in (eps or [])[:20]:
                    src = (e.get("source") or "").strip()
                    summ = (e.get("summary") or "").strip().replace("\n", " ")
                    url = (e.get("url") or "").strip()
                    tail = f" ({url})" if url else ""
                    eps_lines.append(f"- [{src}] {summ[:140]}{tail}")
                eps_txt = (
                    "\n".join(eps_lines) if eps_lines else "(sin episodios en 24h)"
                )

                cfg = safe_load(
                    self.base_path / "Config" / "proactive_mode.json", default={}
                )
                cfg = cfg if isinstance(cfg, dict) else {}
                contexts = list(cfg.get("contexts") or [])
                # enriquecer con tags frecuentes
                for e in (eps or [])[:10]:
                    try:
                        contexts.extend(e.get("tags") or [])
                    except Exception:
                        pass
                contexts = list(
                    dict.fromkeys([str(x).strip() for x in contexts if str(x).strip()])
                )[:10]

                acts = await MuninnMemory(self.base_path).activate(
                    context=contexts,
                    vault=str(cfg.get("vault") or "facts"),
                    max_results=8,
                )
                act_lines = []
                for a in (acts or [])[:6]:
                    try:
                        score = float(a.get("score") or 0.0)
                    except Exception:
                        score = 0.0
                    concept = (a.get("concept") or "").strip()[:90]
                    act_lines.append(f"- {concept} (score {score:.2f})")
                act_txt = "\n".join(act_lines) if act_lines else "(sin activaciones)"

                orch = get_orchestrator()
                prompt = (
                    "Genera un briefing matutino en español, corto y accionable.\n"
                    "Formato:\n"
                    "1) 5-10 bullets de lo más importante\n"
                    "2) 3 próximas acciones sugeridas\n"
                    "3) 3 cosas a vigilar\n\n"
                    f"Episodios_24h:\n{eps_txt}\n\n"
                    f"Muninn_activations:\n{act_txt}\n"
                )
                result = await asyncio.to_thread(
                    orch.execute_plan,
                    prompt,
                    context="",
                    user_id="scheduler",
                    skip_cache=True,
                )
                return (result or "").strip()
            except Exception as e:
                logger.debug("daily_briefing error: %s", e)
                return ""

        if action == "run_plan":
            from src.api.dependencies import get_orchestrator

            orch = get_orchestrator()
            result = await asyncio.to_thread(
                orch.execute_plan,
                params.get("query", ""),
                context="",
                user_id="scheduler",
            )
            return (result or "").strip()

        if action == "investiga":
            from src.api.dependencies import get_orchestrator

            orch = get_orchestrator()
            url = params.get("url", "")
            result = await asyncio.to_thread(
                orch.execute_plan,
                f"Investiga y resume: {url}",
                context="",
                user_id="scheduler",
                skip_cache=True,
            )
            return (result or "").strip()

        return ""

    async def _run_proactive(self):
        try:
            from src.core.proactive_engine import ProactiveEngine

            engine = ProactiveEngine(self.base_path)
            await engine.run_once()
        except Exception as e:
            logger.exception("Error en proactive: %s", e)
