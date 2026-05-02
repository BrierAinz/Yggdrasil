"""
CronScheduler — Tareas periódicas para Lilith
==============================================
Scheduler basado en threading con intervalos configurables.
Ejecuta tareas recurrentes como resúmenes diarios, consolidación
de memoria, y health checks.

Tipos de cron:
    - daily_summary       — Resumen del día a una hora fija
    - memory_consolidation — Consolidación periódica de memoria
    - health_check         — Verificación del estado del sistema
    - custom              — Tareas personalizadas del usuario

Config en TOML:
    [cron.daily_summary]
    enabled = true
    hour = 23
    prompt = "Resume el dia"

Cada cron job tiene: name, enabled, schedule (hour/interval), prompt,
last_run, next_run. Persiste estado en SQLite (cron_jobs table).
"""

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Lilith.MCP.Cron")

# ─── Paths ─────────────────────────────────────────────────────────────────────

DATA_DIR = Path.home() / ".lilith" / "cron"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CRON_DB = DATA_DIR / "cron_jobs.db"


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CronJob:
    """Un trabajo cron de Lilith.

    Los cron jobs se configuran con un nombre, tipo de schedule,
    y opcionalmente un prompt que se envía al LLM al ejecutarse.
    """
    name: str
    job_type: str  # daily_summary, memory_consolidation, health_check, custom
    enabled: bool = True
    hour: int = 23  # Hora del día (0-23) para daily
    interval: int = 0  # Intervalo en minutos para periodic jobs
    prompt: str = ""
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = ""
    last_result: Optional[str] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self._compute_next_run()

    def _compute_next_run(self):
        """Calcula la próxima ejecución basándose en el tipo de schedule."""
        now = datetime.now()
        if self.job_type == "daily_summary" or self.hour > 0:
            # Ejecutar a una hora específica del día
            target = now.replace(hour=self.hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            self.next_run = target.isoformat()
        elif self.interval > 0:
            # Ejecutar cada N minutos
            target = now + timedelta(minutes=self.interval)
            self.next_run = target.isoformat()
        else:
            # Default: mañana a la hora configurada
            target = now.replace(hour=self.hour or 23, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            self.next_run = target.isoformat()

    def is_due(self) -> bool:
        """Verifica si el job está pendiente de ejecución."""
        if not self.enabled:
            return False
        if not self.next_run:
            return True
        try:
            next_time = datetime.fromisoformat(self.next_run)
            return datetime.now() >= next_time
        except (ValueError, TypeError):
            return True

    def mark_run(self, result: Optional[str] = None):
        """Marca el job como ejecutado y calcula la próxima ejecución."""
        self.last_run = datetime.now().isoformat()
        self.last_result = result
        self.run_count += 1
        self._compute_next_run()

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el job a diccionario."""
        return {
            "name": self.name,
            "job_type": self.job_type,
            "enabled": self.enabled,
            "hour": self.hour,
            "interval": self.interval,
            "prompt": self.prompt,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "created_at": self.created_at,
            "last_result": self.last_result,
            "run_count": self.run_count,
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CronJob":
        """Deserializa un job desde diccionario."""
        metadata_str = data.get("metadata", "{}")
        if isinstance(metadata_str, str):
            try:
                metadata = json.loads(metadata_str)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = metadata_str if isinstance(metadata_str, dict) else {}

        return cls(
            name=data["name"],
            job_type=data.get("job_type", "custom"),
            enabled=data.get("enabled", True),
            hour=data.get("hour", 23),
            interval=data.get("interval", 0),
            prompt=data.get("prompt", ""),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            created_at=data.get("created_at", ""),
            last_result=data.get("last_result"),
            run_count=data.get("run_count", 0),
            metadata=metadata,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Cron Scheduler
# ═══════════════════════════════════════════════════════════════════════════════


class CronScheduler:
    """Scheduler de tareas periódicas para Lilith.

    Ejecuta cron jobs en un thread de background. Cada job puede ser
    un prompt al LLM, una función callback, o una combinación de ambos.

    Uso:
        scheduler = CronScheduler()
        scheduler.add_job(CronJob(
            name="daily_summary",
            job_type="daily_summary",
            hour=23,
            prompt="Resume el dia",
        ))
        scheduler.start()
        # ...
        scheduler.stop()
    """

    # Jobs predefinidos
    DEFAULT_JOBS = [
        {
            "name": "daily_summary",
            "job_type": "daily_summary",
            "hour": 23,
            "prompt": "Resume las actividades del dia",
            "enabled": False,
        },
        {
            "name": "memory_consolidation",
            "job_type": "memory_consolidation",
            "interval": 30,
            "prompt": "Consolida los recuerdos recientes",
            "enabled": False,
        },
        {
            "name": "health_check",
            "job_type": "health_check",
            "interval": 5,
            "prompt": "Verifica el estado del sistema",
            "enabled": False,
        },
    ]

    def __init__(self, db_path: Optional[Path] = None, load_config: bool = True):
        self.db_path = db_path or CRON_DB
        self._jobs: Dict[str, CronJob] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._orch_executor: Optional[Callable] = None

        # Inicializar DB
        self._init_db()

        # Cargar jobs desde DB
        self._load_from_db()

        # Cargar config TOML
        if load_config:
            self._load_from_config()

        # Si no hay jobs, crear los defaults (deshabilitados)
        if not self._jobs:
            self._create_defaults()

    # ═══════════════════════════════════════════════════════════════════════
    # SQLite persistence
    # ═══════════════════════════════════════════════════════════════════════

    def _init_db(self):
        """Crea la tabla de cron_jobs en SQLite si no existe."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cron_jobs (
                name TEXT PRIMARY KEY,
                job_type TEXT NOT NULL DEFAULT 'custom',
                enabled INTEGER NOT NULL DEFAULT 1,
                hour INTEGER DEFAULT 23,
                interval INTEGER DEFAULT 0,
                prompt TEXT DEFAULT '',
                last_run TEXT,
                next_run TEXT,
                created_at TEXT DEFAULT '',
                last_result TEXT,
                run_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()

    def _load_from_db(self):
        """Carga jobs desde la base de datos SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM cron_jobs")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                data = dict(row)
                job = CronJob.from_dict(data)
                self._jobs[job.name] = job
        except Exception as e:
            logger.warning("[Cron] Error cargando desde DB: %s", e)

    def _save_job_to_db(self, job: CronJob):
        """Guarda o actualiza un job en SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            data = job.to_dict()
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = list(data.values())

            # UPSERT
            conn.execute(
                f"INSERT OR REPLACE INTO cron_jobs ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("[Cron] Error guardando job %s en DB: %s", job.name, e)

    def _remove_job_from_db(self, name: str):
        """Elimina un job de SQLite."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("DELETE FROM cron_jobs WHERE name = ?", (name,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("[Cron] Error eliminando job %s de DB: %s", name, e)

    # ═══════════════════════════════════════════════════════════════════════
    # Config TOML
    # ═══════════════════════════════════════════════════════════════════════

    def _load_from_config(self):
        """Carga configuración de cron desde el config TOML de Lilith."""
        try:
            from Lilith.Core.toml_config import get_config
            config = get_config()
            cron_config = config.get("cron", {})
            if not cron_config:
                return

            for job_name, job_conf in cron_config.items():
                if isinstance(job_conf, dict):
                    enabled = job_conf.get("enabled", False)
                    hour = job_conf.get("hour", 23)
                    interval = job_conf.get("interval", 0)
                    prompt = job_conf.get("prompt", "")

                    if job_name in self._jobs:
                        # Actualizar job existente
                        job = self._jobs[job_name]
                        job.enabled = enabled
                        if hour:
                            job.hour = hour
                        if interval:
                            job.interval = interval
                        if prompt:
                            job.prompt = prompt
                        job._compute_next_run()
                        self._save_job_to_db(job)
                    else:
                        # Crear nuevo job
                        job = CronJob(
                            name=job_name,
                            job_type=job_name,
                            enabled=enabled,
                            hour=hour,
                            interval=interval,
                            prompt=prompt,
                        )
                        self._jobs[job_name] = job
                        self._save_job_to_db(job)

        except ImportError:
            logger.debug("[Cron] Config TOML no disponible, usando defaults")
        except Exception as e:
            logger.warning("[Cron] Error cargando config TOML: %s", e)

    def _create_defaults(self):
        """Crea los jobs por defecto (deshabilitados)."""
        for default in self.DEFAULT_JOBS:
            job = CronJob(**default)
            self._jobs[job.name] = job
            self._save_job_to_db(job)

    # ═══════════════════════════════════════════════════════════════════════
    # API pública
    # ═══════════════════════════════════════════════════════════════════════

    def add_job(self, job: CronJob) -> None:
        """Agrega un nuevo cron job.

        Args:
            job: El CronJob a agregar.
        """
        with self._lock:
            self._jobs[job.name] = job
            self._save_job_to_db(job)
        logger.info("[Cron] Job agregado: %s (tipo=%s, enabled=%s)", job.name, job.job_type, job.enabled)

    def remove_job(self, name: str) -> bool:
        """Elimina un cron job por nombre.

        Args:
            name: Nombre del job a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        with self._lock:
            if name in self._jobs:
                del self._jobs[name]
                self._remove_job_from_db(name)
                logger.info("[Cron] Job eliminado: %s", name)
                return True
        return False

    def enable_job(self, name: str) -> bool:
        """Habilita un cron job.

        Args:
            name: Nombre del job a habilitar.

        Returns:
            True si se habilitó, False si no se encontró.
        """
        with self._lock:
            if name in self._jobs:
                self._jobs[name].enabled = True
                self._jobs[name]._compute_next_run()
                self._save_job_to_db(self._jobs[name])
                logger.info("[Cron] Job habilitado: %s", name)
                return True
        return False

    def disable_job(self, name: str) -> bool:
        """Deshabilita un cron job.

        Args:
            name: Nombre del job a deshabilitar.

        Returns:
            True si se deshabilitó, False si no se encontró.
        """
        with self._lock:
            if name in self._jobs:
                self._jobs[name].enabled = False
                self._save_job_to_db(self._jobs[name])
                logger.info("[Cron] Job deshabilitado: %s", name)
                return True
        return False

    def get_job(self, name: str) -> Optional[CronJob]:
        """Obtiene un job por nombre."""
        return self._jobs.get(name)

    def list_jobs(self, enabled_only: bool = False) -> List[CronJob]:
        """Lista todos los cron jobs.

        Args:
            enabled_only: Si True, solo retorna jobs habilitados.
        """
        jobs = list(self._jobs.values())
        if enabled_only:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.name)

    def run_now(self, name: str) -> Optional[str]:
        """Ejecuta un cron job inmediatamente.

        Args:
            name: Nombre del job a ejecutar.

        Returns:
            Resultado de la ejecución, o None si no se encontró el job.
        """
        job = self._jobs.get(name)
        if not job:
            return None

        result = self._execute_job(job)
        return result

    def register_callback(self, job_type: str, callback: Callable) -> None:
        """Registra un callback para un tipo de job.

        Cuando un job de este tipo se ejecuta, se llama al callback
        en vez de (o además de) enviar el prompt al LLM.

        Args:
            job_type: Tipo de job (ej: "health_check").
            callback: Función que recibe el CronJob y retorna un string.
        """
        self._callbacks[job_type] = callback

    def set_orch_executor(self, executor: Callable) -> None:
        """Establece la función que ejecuta prompts vía el Orchestrator.

        Args:
            executor: Función que recibe un string (prompt) y retorna
                      un string (respuesta del LLM).
        """
        self._orch_executor = executor

    # ═══════════════════════════════════════════════════════════════════════
    # Ejecución de jobs
    # ═══════════════════════════════════════════════════════════════════════

    def _execute_job(self, job: CronJob) -> str:
        """Ejecuta un cron job.

        Prioridad de ejecución:
            1. Callback registrado para el job_type
            2. Executor del Orchestrator (prompt al LLM)
            3. Callback genérico

        Returns:
            El resultado de la ejecución como string.
        """
        logger.info("[Cron] Ejecutando job: %s (tipo=%s)", job.name, job.job_type)

        result = ""
        try:
            # 1. Intentar callback específico
            callback = self._callbacks.get(job.job_type)
            if callback:
                result = callback(job)
            # 2. Intentar callback por nombre
            elif job.name in self._callbacks:
                result = self._callbacks[job.name](job)
            # 3. Intentar el Orchestrator
            elif self._orch_executor and job.prompt:
                result = self._orch_executor(job.prompt)
            # 4. Solo prompt
            elif job.prompt:
                result = f"[Prompt ejecutado: {job.prompt[:50]}...]"
            else:
                result = f"[Job {job.name} ejecutado sin prompt]"

            logger.info("[Cron] Job %s completado: %s", job.name, str(result)[:100])

        except Exception as e:
            result = f"Error: {e}"
            logger.error("[Cron] Error ejecutando job %s: %s", job.name, e)

        # Actualizar estado
        with self._lock:
            job.mark_run(result=result)
            self._save_job_to_db(job)

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # Loop de background
    # ═══════════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """Inicia el scheduler en un thread de background."""
        if self._running:
            logger.warning("[Cron] Scheduler ya está corriendo")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CronScheduler")
        self._thread.start()
        logger.info("[Cron] Scheduler iniciado")

    def stop(self) -> None:
        """Detiene el scheduler de background."""
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[Cron] Scheduler detenido")

    def _run_loop(self) -> None:
        """Loop principal del scheduler (corre en background)."""
        logger.info("[Cron] Loop iniciado — verificando jobs cada 30s")
        while self._running:
            try:
                self._check_and_run()
            except Exception as e:
                logger.error("[Cron] Error en loop: %s", e)
            time.sleep(30)  # Verificar cada 30 segundos

    def _check_and_run(self) -> None:
        """Verifica y ejecuta los jobs pendientes."""
        with self._lock:
            due_jobs = [job for job in self._jobs.values() if job.is_due()]

        for job in due_jobs:
            try:
                self._execute_job(job)
            except Exception as e:
                logger.error("[Cron] Error ejecutando job %s: %s", job.name, e)

    # ═══════════════════════════════════════════════════════════════════════
    # Status
    # ═══════════════════════════════════════════════════════════════════════

    def status(self) -> Dict[str, Any]:
        """Retorna el estado del scheduler y sus jobs."""
        jobs_status = []
        for job in self.list_jobs():
            jobs_status.append({
                "name": job.name,
                "type": job.job_type,
                "enabled": job.enabled,
                "hour": job.hour,
                "interval": job.interval,
                "last_run": job.last_run,
                "next_run": job.next_run,
                "run_count": job.run_count,
                "has_prompt": bool(job.prompt),
            })
        return {
            "running": self._running,
            "total_jobs": len(self._jobs),
            "enabled_jobs": len([j for j in self._jobs.values() if j.enabled]),
            "jobs": jobs_status,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_scheduler_instance: Optional[CronScheduler] = None


def get_cron_scheduler() -> CronScheduler:
    """Obtiene la instancia singleton del CronScheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CronScheduler()
    return _scheduler_instance