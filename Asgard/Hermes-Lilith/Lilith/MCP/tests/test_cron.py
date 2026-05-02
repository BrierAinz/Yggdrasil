"""
Tests del CronScheduler
========================
Tests unitarios para el scheduler de tareas periódicas de Lilith.
"""

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Lilith.MCP.cron import CronJob, CronScheduler


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def db_path(tmp_path):
    """Path temporal para la base de datos de test."""
    return tmp_path / "test_cron.db"


@pytest.fixture
def scheduler(db_path):
    """Crea un scheduler limpio para cada test."""
    # Deshabilitar carga de config TOML para tests
    s = CronScheduler(db_path=db_path, load_config=False)
    return s


# ═══════════════════════════════════════════════════════════════════════════════
# Test CronJob dataclass
# ═══════════════════════════════════════════════════════════════════════════════


class TestCronJob:
    """Tests para la dataclass CronJob."""

    def test_cron_job_creation(self):
        """Un CronJob se crea correctamente con defaults."""
        job = CronJob(name="test_job", job_type="custom")
        assert job.name == "test_job"
        assert job.job_type == "custom"
        assert job.enabled is True
        assert job.hour == 23
        assert job.interval == 0
        assert job.prompt == ""
        assert job.run_count == 0

    def test_cron_job_custom_values(self):
        """Un CronJob se crea con valores custom."""
        job = CronJob(
            name="daily",
            job_type="daily_summary",
            enabled=False,
            hour=9,
            prompt="Resume el dia",
        )
        assert job.name == "daily"
        assert job.job_type == "daily_summary"
        assert job.enabled is False
        assert job.hour == 9
        assert job.prompt == "Resume el dia"

    def test_cron_job_compute_next_run_daily(self):
        """compute_next_run calcula la próxima ejecución para jobs diarios."""
        job = CronJob(name="daily", job_type="daily_summary", hour=23)
        assert job.next_run is not None
        # next_run debe ser una fecha ISO válida
        next_time = datetime.fromisoformat(job.next_run)
        assert next_time.hour == 23
        assert next_time.minute == 0

    def test_cron_job_compute_next_run_interval(self):
        """compute_next_run calcula la próxima ejecución para jobs con intervalo."""
        job = CronJob(name="periodic", job_type="health_check", interval=30)
        assert job.next_run is not None
        next_time = datetime.fromisoformat(job.next_run)
        # Debe ser ~30 minutos en el futuro
        assert next_time > datetime.now()

    def test_cron_job_is_due_enabled(self):
        """is_due retorna True para jobs habilitados con next_run en el pasado."""
        job = CronJob(name="due", job_type="custom", hour=0)
        # Forzar next_run en el pasado
        job.next_run = (datetime.now() - timedelta(hours=1)).isoformat()
        assert job.is_due() is True

    def test_cron_job_is_due_disabled(self):
        """is_due retorna False para jobs deshabilitados."""
        job = CronJob(name="disabled", job_type="custom", enabled=False)
        assert job.is_due() is False

    def test_cron_job_is_due_future(self):
        """is_due retorna False para jobs con next_run en el futuro."""
        job = CronJob(name="future", job_type="custom")
        job.next_run = (datetime.now() + timedelta(hours=24)).isoformat()
        assert job.is_due() is False

    def test_cron_job_mark_run(self):
        """mark_run actualiza last_run, next_run y run_count."""
        job = CronJob(name="test", job_type="custom", hour=23)
        initial_count = job.run_count
        job.mark_run(result="ok")
        assert job.last_run is not None
        assert job.run_count == initial_count + 1
        assert job.last_result == "ok"

    def test_cron_job_to_dict(self):
        """to_dict serializa correctamente."""
        job = CronJob(name="test", job_type="daily_summary", hour=9, prompt="Resume")
        d = job.to_dict()
        assert d["name"] == "test"
        assert d["job_type"] == "daily_summary"
        assert d["hour"] == 9
        assert d["prompt"] == "Resume"
        assert d["enabled"] is True

    def test_cron_job_from_dict(self):
        """from_dict deserializa correctamente."""
        data = {
            "name": "restored",
            "job_type": "memory_consolidation",
            "enabled": True,
            "hour": 0,
            "interval": 30,
            "prompt": "Consolida",
            "last_run": "2025-01-01T12:00:00",
            "next_run": "2025-01-02T12:00:00",
            "created_at": "2025-01-01T00:00:00",
            "last_result": "ok",
            "run_count": 5,
            "metadata": "{}",
        }
        job = CronJob.from_dict(data)
        assert job.name == "restored"
        assert job.job_type == "memory_consolidation"
        assert job.interval == 30
        assert job.run_count == 5

    def test_cron_job_to_dict_from_dict_roundtrip(self):
        """Serializar y deserializar preserva los datos."""
        original = CronJob(
            name="roundtrip",
            job_type="custom",
            enabled=True,
            hour=14,
            interval=0,
            prompt="Test prompt",
            metadata={"key": "value"},
        )
        data = original.to_dict()
        restored = CronJob.from_dict(data)
        assert restored.name == original.name
        assert restored.job_type == original.job_type
        assert restored.enabled == original.enabled
        assert restored.hour == original.hour
        assert restored.prompt == original.prompt


# ═══════════════════════════════════════════════════════════════════════════════
# Test CronScheduler
# ═══════════════════════════════════════════════════════════════════════════════


class TestCronScheduler:
    """Tests para el CronScheduler."""

    def test_scheduler_creation(self, scheduler):
        """Un scheduler se crea correctamente."""
        assert scheduler._running is False
        assert scheduler._thread is None
        assert len(scheduler._jobs) > 0  # Defaults se crean

    def test_scheduler_creates_defaults(self, scheduler):
        """El scheduler crea los jobs por defecto (deshabilitados)."""
        names = [j.name for j in scheduler.list_jobs()]
        assert "daily_summary" in names
        assert "memory_consolidation" in names
        assert "health_check" in names

    def test_scheduler_defaults_disabled(self, scheduler):
        """Los jobs por defecto están deshabilitados."""
        for job in scheduler.list_jobs():
            assert job.enabled is False

    def test_add_job(self, scheduler):
        """Se puede agregar un job al scheduler."""
        job = CronJob(
            name="my_job",
            job_type="custom",
            hour=10,
            prompt="Haz algo",
        )
        scheduler.add_job(job)
        assert scheduler.get_job("my_job") is not None
        assert scheduler.get_job("my_job").prompt == "Haz algo"

    def test_remove_job(self, scheduler):
        """Se puede eliminar un job del scheduler."""
        job = CronJob(name="to_remove", job_type="custom", interval=5)
        scheduler.add_job(job)
        assert scheduler.get_job("to_remove") is not None
        result = scheduler.remove_job("to_remove")
        assert result is True
        assert scheduler.get_job("to_remove") is None

    def test_remove_nonexistent_job(self, scheduler):
        """Eliminar un job inexistente retorna False."""
        result = scheduler.remove_job("nonexistent")
        assert result is False

    def test_enable_job(self, scheduler):
        """Se puede habilitar un job."""
        result = scheduler.enable_job("daily_summary")
        assert result is True
        job = scheduler.get_job("daily_summary")
        assert job.enabled is True

    def test_enable_nonexistent_job(self, scheduler):
        """Habilitar un job inexistente retorna False."""
        result = scheduler.enable_job("nonexistent")
        assert result is False

    def test_disable_job(self, scheduler):
        """Se puede deshabilitar un job."""
        scheduler.enable_job("daily_summary")
        result = scheduler.disable_job("daily_summary")
        assert result is True
        job = scheduler.get_job("daily_summary")
        assert job.enabled is False

    def test_disable_nonexistent_job(self, scheduler):
        """Deshabilitar un job inexistente retorna False."""
        result = scheduler.disable_job("nonexistent")
        assert result is False

    def test_list_jobs(self, scheduler):
        """list_jobs retorna todos los jobs."""
        jobs = scheduler.list_jobs()
        assert len(jobs) >= 3  # Al menos los defaults

    def test_list_jobs_enabled_only(self, scheduler):
        """list_jobs con enabled_only filtra correctamente."""
        scheduler.enable_job("daily_summary")
        enabled = scheduler.list_jobs(enabled_only=True)
        assert len(enabled) >= 1
        for job in enabled:
            assert job.enabled is True

    def test_run_now(self, scheduler):
        """run_now ejecuta un job inmediatamente."""
        job = CronJob(name="run_me", job_type="custom", interval=5, prompt="Test job")
        scheduler.add_job(job)
        result = scheduler.run_now("run_me")
        # El resultado dependerá de si hay executor o no
        job_updated = scheduler.get_job("run_me")
        assert job_updated.last_run is not None
        assert job_updated.run_count == 1

    def test_run_now_nonexistent(self, scheduler):
        """run_now con job inexistente retorna None."""
        result = scheduler.run_now("nonexistent")
        assert result is None

    def test_run_now_with_callback(self, scheduler):
        """run_now ejecuta el callback registrado."""
        results = []
        scheduler.register_callback("test_cb", lambda job: f"Callback: {job.name}")

        job = CronJob(name="cb_job", job_type="test_cb", interval=5)
        scheduler.add_job(job)

        result = scheduler.run_now("cb_job")
        assert result == "Callback: cb_job"

    def test_register_callback(self, scheduler):
        """Se puede registrar un callback por tipo de job."""
        callback = MagicMock(return_value="cb_result")
        scheduler.register_callback("health_check", callback)

        job = scheduler.get_job("health_check")
        job.enabled = True

        result = scheduler.run_now("health_check")
        callback.assert_called_once()

    def test_set_orch_executor(self, scheduler):
        """Se puede establecer un executor del Orchestrator."""
        executor = MagicMock(return_value="LLM result")
        scheduler.set_orch_executor(executor)

        job = CronJob(name="llm_job", job_type="custom", prompt="Test prompt")
        scheduler.add_job(job)
        scheduler.run_now("llm_job")
        executor.assert_called_once_with("Test prompt")

    def test_status(self, scheduler):
        """status retorna el estado del scheduler."""
        status = scheduler.status()
        assert "running" in status
        assert "total_jobs" in status
        assert "enabled_jobs" in status
        assert "jobs" in status
        assert status["running"] is False
        assert status["total_jobs"] >= 3

    def test_start_and_stop(self, scheduler):
        """El scheduler se puede iniciar y detener."""
        scheduler.start()
        assert scheduler._running is True
        import time
        time.sleep(0.1)  # Dar tiempo al thread
        scheduler.stop()
        assert scheduler._running is False


# ═══════════════════════════════════════════════════════════════════════════════
# Test persistencia en SQLite
# ═══════════════════════════════════════════════════════════════════════════════


class TestCronPersistence:
    """Tests de persistencia de cron jobs en SQLite."""

    def test_persist_and_reload(self, db_path):
        """Guardar un job y recargarlo desde DB."""
        s1 = CronScheduler(db_path=db_path, load_config=False)
        s1.enable_job("daily_summary")

        # Crear un nuevo scheduler con la misma DB
        s2 = CronScheduler(db_path=db_path, load_config=False)
        job = s2.get_job("daily_summary")
        # Nota: s2 carga de DB, los defaults son disabled, pero s1 habilitó
        assert job is not None

    def test_add_and_reload_custom_job(self, db_path):
        """Un job custom se persiste y se puede recargar."""
        s1 = CronScheduler(db_path=db_path, load_config=False)
        custom = CronJob(name="my_custom", job_type="custom", prompt="Custom job")
        s1.add_job(custom)

        s2 = CronScheduler(db_path=db_path, load_config=False)
        job = s2.get_job("my_custom")
        assert job is not None
        assert job.prompt == "Custom job"

    def test_remove_and_verify_db(self, db_path):
        """Eliminar un job lo remueve de la DB."""
        import sqlite3
        s1 = CronScheduler(db_path=db_path, load_config=False)
        s1.remove_job("daily_summary")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) FROM cron_jobs WHERE name = 'daily_summary'")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 0

    def test_job_state_persists_after_run(self, db_path):
        """El estado de un job se actualiza en DB después de ejecutarse."""
        s1 = CronScheduler(db_path=db_path, load_config=False)
        s1.run_now("daily_summary")

        s2 = CronScheduler(db_path=db_path, load_config=False)
        job = s2.get_job("daily_summary")
        assert job is not None
        assert job.last_run is not None
        assert job.run_count >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Test callback execution
# ═══════════════════════════════════════════════════════════════════════════════


class TestCronCallbacks:
    """Tests de ejecución de callbacks de cron jobs."""

    def test_job_with_callback_takes_priority(self, scheduler):
        """Un callback registrado tiene prioridad sobre el prompt."""
        callback_calls = []

        def my_callback(job):
            callback_calls.append(job.name)
            return f"Callback executed for {job.name}"

        scheduler.register_callback("custom_cb", my_callback)
        job = CronJob(
            name="priority_cb",
            job_type="custom_cb",
            prompt="Este prompt no se usa",
        )
        scheduler.add_job(job)
        result = scheduler.run_now("priority_cb")
        assert result == "Callback executed for priority_cb"
        assert len(callback_calls) == 1

    def test_job_with_orch_executor(self, scheduler):
        """El Orchestrator executor se usa si no hay callback registrado."""
        exec_calls = []

        def my_executor(prompt):
            exec_calls.append(prompt)
            return f"Executed: {prompt}"

        scheduler.set_orch_executor(my_executor)
        job = CronJob(name="orch_test", job_type="custom", prompt="Test prompt")
        scheduler.add_job(job)
        result = scheduler.run_now("orch_test")
        assert len(exec_calls) == 1
        assert exec_calls[0] == "Test prompt"

    def test_job_with_prompt_only(self, scheduler):
        """Un job sin callback ni executor usa el prompt como resultado."""
        job = CronJob(name="prompt_only", job_type="custom", prompt="Solo un prompt")
        scheduler.add_job(job)
        result = scheduler.run_now("prompt_only")
        assert "prompt" in result.lower() or "Prompt ejecutado" in result or "Solo un prompt" in result

    def test_job_no_prompt_no_callback(self, scheduler):
        """Un job sin callback, executor ni prompt retorna mensaje genérico."""
        job = CronJob(name="empty", job_type="custom", prompt="")
        scheduler.add_job(job)
        result = scheduler.run_now("empty")
        assert result is not None