"""
Tests para FASE 4 (LLM Integration) y FASE 5 (Swarm Persistence)
===============================================================
pytest -xvs Lilith/Swarm/tests/test_fase4_5.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
from Lilith.Swarm.agent import AgentStatus, SwarmAgent
from Lilith.Swarm.database import SwarmDatabase
from Lilith.Swarm.executor import SwarmExecutor
from Lilith.Swarm.manager import SwarmManager
from Lilith.Swarm.message_bus import MessageBus

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 5: Swarm Persistence
# ═══════════════════════════════════════════════════════════════════════════════


class TestSwarmDatabase:
    """Tests de persistencia SQLite."""

    def setup_method(self):
        """Crear DB temporal para cada test."""
        import tempfile

        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db = SwarmDatabase(db_path=Path(self.tmp_db.name))

    def teardown_method(self):
        """Limpiar DB temporal."""
        import os

        self.db.close()
        os.unlink(self.tmp_db.name)

    def test_save_and_load_session(self):
        self.db.save_session(
            "test_s1",
            "tarea de prueba",
            status="active",
            repo_path="/tmp",
            use_llm=True,
        )
        s = self.db.get_session("test_s1")
        assert s is not None
        assert s["task"] == "tarea de prueba"
        assert s["status"] == "active"
        assert s["repo_path"] == "/tmp"
        assert s["use_llm"] == 1

    def test_list_sessions(self):
        self.db.save_session("test_s2", "tarea 2")
        self.db.save_session("test_s3", "tarea 3")
        sessions = self.db.list_sessions(limit=10)
        ids = [s["id"] for s in sessions]
        assert "test_s2" in ids
        assert "test_s3" in ids

    def test_save_and_get_agents(self):
        self.db.save_session("test_s4", "tarea")
        self.db.save_agent(
            "test_s4",
            {
                "id": "agent_1",
                "task": "subtarea",
                "status": "complete",
                "capabilities": ["coding"],
                "context": {"key": "val"},
                "result": {"success": True, "output": "done"},
                "files_read": ["a.py"],
                "files_written": ["b.py"],
                "duration_seconds": 1.5,
            },
        )
        agents = self.db.get_agents("test_s4")
        assert len(agents) == 1
        a = agents[0]
        assert a["id"] == "agent_1"
        assert a["status"] == "complete"
        assert a["capabilities"] == ["coding"]
        assert a["context"] == {"key": "val"}
        assert a["result"]["success"] is True
        assert a["files_read"] == ["a.py"]
        assert a["duration_seconds"] == 1.5

    def test_save_and_get_messages(self):
        self.db.save_session("test_s5", "tarea")
        self.db.save_message(
            "test_s5",
            {
                "from_id": "agent_1",
                "to_id": "agent_2",
                "msg_type": "task_complete",
                "content": "done",
                "data": {"result": "ok"},
                "timestamp": time.time(),
            },
        )
        msgs = self.db.get_messages("test_s5")
        assert len(msgs) == 1
        assert msgs[0]["from_id"] == "agent_1"
        assert msgs[0]["data"]["result"] == "ok"

    def test_save_and_get_conflicts(self):
        self.db.save_session("test_s6", "tarea")
        self.db.save_conflict(
            "test_s6",
            {
                "file_path": "test.py",
                "agent_ids": ["a1", "a2"],
                "severity": "high",
                "resolution": "manual",
                "resolved": False,
                "created_at": time.time(),
            },
        )
        conflicts = self.db.get_conflicts("test_s6")
        assert len(conflicts) == 1
        assert conflicts[0]["file_path"] == "test.py"
        assert conflicts[0]["severity"] == "high"
        assert conflicts[0]["resolved"] is False

    def test_update_conflict_resolution(self):
        self.db.save_session("test_s7", "tarea")
        self.db.save_conflict(
            "test_s7",
            {
                "file_path": "test.py",
                "agent_ids": ["a1"],
                "severity": "low",
                "resolved": False,
                "created_at": time.time(),
            },
        )
        # Obtener el id del conflicto recien insertado
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT id FROM swarm_conflicts WHERE session_id = ? ORDER BY id DESC LIMIT 1",
            ("test_s7",),
        ).fetchone()
        conflict_id = row["id"]
        self.db.update_conflict_resolution(conflict_id, "merged")
        conflicts = self.db.get_conflicts("test_s7")
        # Buscar el conflicto actualizado
        updated = [c for c in conflicts if c["id"] == conflict_id][0]
        assert updated["resolved"] is True
        assert updated["resolution"] == "merged"

    def test_delete_session(self):
        self.db.save_session("test_s8", "tarea")
        self.db.save_agent("test_s8", {"id": "a1", "task": "t"})
        self.db.save_message("test_s8", {"msg_type": "test"})
        self.db.save_conflict("test_s8", {"file_path": "f.py", "agent_ids": ["a1"]})
        self.db.delete_session("test_s8")
        assert self.db.get_session("test_s8") is None
        assert self.db.get_agents("test_s8") == []
        assert self.db.get_messages("test_s8") == []
        assert self.db.get_conflicts("test_s8") == []


class TestSwarmManagerPersistence:
    """Tests de persistencia integrada en SwarmManager."""

    def test_save_and_load_session(self):
        mgr = SwarmManager()
        mgr.spawn_agent(task="test task")
        mgr.enable_persistence()
        sid = mgr.save_session(task="test task")
        assert sid.startswith("swarm_")

        # Nueva instancia, cargar
        mgr2 = SwarmManager()
        ok = mgr2.load_session(sid)
        assert ok is True
        assert mgr2._use_llm == mgr._use_llm

    def test_list_sessions(self):
        mgr = SwarmManager()
        mgr.enable_persistence()
        sid = mgr.save_session(task="list test")
        sessions = mgr.list_saved_sessions()
        ids = [s["id"] for s in sessions]
        assert sid in ids

    def test_get_session_history(self):
        mgr = SwarmManager()
        mgr.enable_persistence()
        sid = mgr.save_session(task="history test")
        history = mgr.get_session_history(sid)
        assert history["session"] is not None
        assert history["agents"] == []  # No agentes spawnados
        assert history["messages"] == []
        assert history["conflicts"] == []

    def test_auto_save_on_stop(self):
        mgr = SwarmManager()
        mgr.enable_persistence()
        sid = mgr.save_session(task="auto test")
        mgr._session_id = sid
        mgr.stop_coordinator()
        # Verificar que se guardo al detener
        history = mgr.get_session_history(sid)
        assert history["session"] is not None


class TestSwarmAgentLLMMode:
    """Tests de agente con LLM (simulado)."""

    def test_agent_with_executor(self):
        """Agente con executor mock."""
        bus = MessageBus()
        locks = {}

        class MockExecutor:
            def execute(self, agent_id, task, context, on_progress):
                on_progress("step 1")
                on_progress("step 2")
                return {
                    "success": True,
                    "output": "mock result",
                    "files_modified": ["test.py"],
                }

        agent = SwarmAgent(
            agent_id="llm_agent",
            task="test with llm",
            capabilities=["coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
            executor=MockExecutor(),
            use_llm=True,
        )
        agent.start()
        time.sleep(1.5)

        assert agent.status in (AgentStatus.COMPLETE, AgentStatus.ERROR)
        if agent.status == AgentStatus.COMPLETE:
            assert agent.result is not None
            assert agent.result.success is True
        agent.stop()

    def test_agent_without_executor_uses_simulation(self):
        """Agente sin executor usa simulacion."""
        bus = MessageBus()
        locks = {}
        agent = SwarmAgent(
            agent_id="sim_agent",
            task="simulated task",
            capabilities=["coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
            use_llm=False,
        )
        agent.start()
        time.sleep(1.5)
        assert agent.status in (AgentStatus.COMPLETE, AgentStatus.ERROR)
        agent.stop()


class TestSwarmExecutor:
    """Tests del executor."""

    def test_executor_initialization(self):
        """El executor se inicializa correctamente."""

        # No requiere conexion real para test de init
        class MockClient:
            pass

        ex = SwarmExecutor(MockClient())
        assert ex is not None
        assert ex.client is not None
        assert ex.max_tool_calls >= 1

    def test_executor_execute_with_mock(self):
        """El executor ejecuta con LLM mock."""

        class MockClient:
            def chat(self, messages, tools=None, tool_choice=None):
                # Simular respuesta del LLM
                return {"choices": [{"message": {"content": "resultado mock"}}]}

        ex = SwarmExecutor(MockClient())
        result = ex.execute_task(
            task="test task",
            context={},
            capabilities=["coding"],
        )
        assert result["success"] is True
        assert "resultado mock" in result["output"]
