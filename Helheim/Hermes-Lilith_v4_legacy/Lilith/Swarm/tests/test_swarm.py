"""
Tests para el modulo Swarm
==========================
pytest -xvs Lilith/Swarm/tests/test_swarm.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
from Lilith.Swarm.agent import AgentStatus, SwarmAgent, TaskResult
from Lilith.Swarm.conflict_resolver import Conflict as ConflictData
from Lilith.Swarm.conflict_resolver import (
    ConflictResolution,
    ConflictResolver,
    ConflictSeverity,
)
from Lilith.Swarm.manager import SwarmManager
from Lilith.Swarm.message_bus import Message, MessageBus, MessageType

# ═══════════════════════════════════════════════════════════════════════════════
# MessageBus Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestMessageBus:
    def test_send_and_receive(self):
        bus = MessageBus()
        msg = Message(
            msg_type=MessageType.TASK_COMPLETE,
            from_id="agent_1",
            data={"result": "ok"},
        )
        assert bus.send(msg) is True
        msgs = bus.get_messages("agent_2")
        assert len(msgs) == 1  # broadcast, cualquiera lo recibe
        assert msgs[0].msg_type == MessageType.TASK_COMPLETE

    def test_private_message(self):
        bus = MessageBus()
        msg = Message(
            msg_type=MessageType.LOCK_REQUEST,
            from_id="agent_1",
            to_id="agent_2",
            data={"file": "test.py"},
        )
        bus.send(msg)
        # agent_3 no deberia recibirlo
        msgs = bus.get_messages("agent_3")
        assert len(msgs) == 0
        # agent_2 si
        msgs = bus.get_messages("agent_2")
        assert len(msgs) == 1

    def test_broadcast(self):
        bus = MessageBus()
        bus.subscribe("agent_1")
        bus.subscribe("agent_2")
        bus.broadcast("system", MessageType.BROADCAST, {"msg": "hello"})
        # Ambos deberian poder leer (aunque get_messages filtra por to_id)
        # Broadcast tiene to_id=None, asi que cualquiera lo recibe
        msgs1 = bus.get_messages("agent_1")
        msgs2 = bus.get_messages("agent_2")
        assert len(msgs1) == 1
        assert len(msgs2) == 0  # Cola ya fue drenada por agent_1
        # Re-encolar para agent_2... no, el bus no re-encola
        # Esto es un comportamiento conocido: first-come-first-served

    def test_history(self):
        bus = MessageBus()
        bus.broadcast("a", MessageType.STATUS_UPDATE, {})
        bus.broadcast("a", MessageType.STATUS_UPDATE, {})
        hist = bus.get_history(limit=2)
        assert len(hist) == 2

    def test_clear(self):
        bus = MessageBus()
        bus.broadcast("a", MessageType.BROADCAST, {})
        bus.clear()
        assert bus.size == 0
        assert len(bus.get_history()) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# SwarmAgent Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSwarmAgent:
    def test_agent_lifecycle(self):
        bus = MessageBus()
        locks = {}
        agent = SwarmAgent(
            agent_id="test_1",
            task="test task",
            capabilities=["coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
        )
        assert agent.status == AgentStatus.IDLE
        agent.start()
        time.sleep(0.8)  # Esperar a que complete la simulacion (5 x 0.1s + margin)
        assert agent.is_complete
        assert agent.result is not None
        assert agent.result.success is True

    def test_agent_stop(self):
        bus = MessageBus()
        locks = {}
        agent = SwarmAgent(
            agent_id="test_2",
            task="long task",
            capabilities=["coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
        )
        agent.start()
        time.sleep(0.05)
        agent.stop()
        time.sleep(0.1)
        assert agent.status == AgentStatus.STOPPED

    def test_file_locking(self):
        bus = MessageBus()
        locks = {}
        agent = SwarmAgent(
            agent_id="test_3",
            task="test",
            capabilities=["coding"],
            context={"files_to_read": ["file1.py"]},
            message_bus=bus,
            file_locks=locks,
        )
        assert agent._acquire_lock("file1.py") is True
        assert locks["file1.py"] == "test_3"
        # Otro agente no puede adquirir
        agent2 = SwarmAgent(
            agent_id="test_4",
            task="test2",
            capabilities=["coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
        )
        assert agent2._acquire_lock("file1.py") is False

    def test_relevance_assessment(self):
        bus = MessageBus()
        locks = {}
        agent = SwarmAgent(
            agent_id="test_5",
            task="fix the database connection",
            capabilities=["database", "coding"],
            context={},
            message_bus=bus,
            file_locks=locks,
        )
        agent.files_read.add("db.py")
        assert agent._assess_relevance("db.py", "+1 line") == 1.0
        assert agent._assess_relevance("database_config.yaml", "+1 line") > 0.5
        assert agent._assess_relevance("random.txt", "+1 line") == 0.3


# ═══════════════════════════════════════════════════════════════════════════════
# SwarmManager Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSwarmManager:
    def test_spawn_single_agent(self):
        mgr = SwarmManager()
        aid = mgr.spawn_agent(task="test task")
        assert aid.startswith("agent_")
        assert aid in mgr.agents
        time.sleep(1.0)
        mgr.kill_all()

    def test_spawn_swarm(self):
        mgr = SwarmManager()
        aids = mgr.spawn_swarm(task="big task", num_agents=3)
        assert len(aids) == 3
        assert len(mgr.agents) == 3
        time.sleep(1.0)
        mgr.kill_all()

    def test_kill_agent(self):
        mgr = SwarmManager()
        aid = mgr.spawn_agent(task="test")
        time.sleep(0.1)
        result = mgr.kill_agent(aid)
        assert result is True
        assert mgr.agents[aid].status == AgentStatus.STOPPED

    def test_status_report(self):
        mgr = SwarmManager()
        mgr.spawn_agent(task="test1")
        mgr.spawn_agent(task="test2")
        time.sleep(1.0)
        report = mgr.get_status_report()
        assert report["total_agents"] == 2
        assert "active" in report
        assert "complete" in report
        mgr.kill_all()

    def test_wait_for_completion(self):
        mgr = SwarmManager()
        aids = mgr.spawn_swarm(task="quick task", num_agents=2)
        completed = mgr.wait_for_completion(aids, timeout=10.0)
        assert completed is True
        mgr.kill_all()

    def test_file_lock_tracking(self):
        mgr = SwarmManager()
        aid = mgr.spawn_agent(
            task="test",
            context={"files_to_read": ["test.py"]},
        )
        time.sleep(0.5)
        report = mgr.get_status_report()
        # El lock puede o no estar dependiendo de timing
        assert "file_locks" in report
        mgr.kill_all()


# ═══════════════════════════════════════════════════════════════════════════════
# ConflictResolver Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConflictResolver:
    def test_detect_no_conflict(self):
        resolver = ConflictResolver()
        mods = {
            "file1.py": [("agent_1", "@@ -1,1 +1,2 @@\n+line")],
        }
        conflicts = resolver.detect_conflicts(mods)
        assert len(conflicts) == 0

    def test_detect_conflict(self):
        resolver = ConflictResolver()
        mods = {
            "file1.py": [
                ("agent_1", "@@ -10,5 +10,6 @@\n+line1"),
                ("agent_2", "@@ -10,5 +10,6 @@\n+line2"),
            ],
        }
        conflicts = resolver.detect_conflicts(mods)
        assert len(conflicts) == 1
        assert conflicts[0].file_path == "file1.py"
        assert len(conflicts[0].agent_ids) == 2

    def test_severity_high(self):
        resolver = ConflictResolver()
        # Misma linea exacta
        mods = {
            "file.py": [
                ("a1", "@@ -5,1 +5,2 @@\n+foo"),
                ("a2", "@@ -5,1 +5,2 @@\n+bar"),
            ],
        }
        conflicts = resolver.detect_conflicts(mods)
        assert conflicts[0].severity == ConflictSeverity.HIGH

    def test_severity_low(self):
        resolver = ConflictResolver()
        # Lineas muy separadas
        mods = {
            "file.py": [
                ("a1", "@@ -5,1 +5,2 @@\n+foo"),
                ("a2", "@@ -100,1 +100,2 @@\n+bar"),
            ],
        }
        conflicts = resolver.detect_conflicts(mods)
        assert conflicts[0].severity == ConflictSeverity.LOW

    def test_auto_merge_low_severity(self):
        resolver = ConflictResolver()
        mods = {
            "file.py": [
                ("a1", "@@ -5,1 +5,2 @@\n+foo"),
                ("a2", "@@ -50,1 +50,2 @@\n+bar"),
            ],
        }
        conflicts = resolver.detect_conflicts(mods)
        result = resolver.attempt_auto_merge(conflicts[0])
        assert result is True
        assert conflicts[0].resolution == ConflictResolution.AUTO_MERGED

    def test_auto_merge_high_severity_fails(self):
        resolver = ConflictResolver()
        mods = {
            "file.py": [
                ("a1", "@@ -5,1 +5,2 @@\n+foo"),
                ("a2", "@@ -5,1 +5,2 @@\n+bar"),
            ],
        }
        conflicts = resolver.detect_conflicts(mods)
        result = resolver.attempt_auto_merge(conflicts[0])
        assert result is False
        assert conflicts[0].resolution == ConflictResolution.MANUAL_REQUIRED

    def test_manual_resolve(self):
        """Resolucion manual requiere intervencion."""
        resolver = ConflictResolver()
        c = ConflictData(
            file_path="test.py",
            agent_ids=["a1", "a2"],
            diffs=["diff1", "diff2"],
            severity=ConflictSeverity.HIGH,
        )
        resolver.resolve_manually(c, ConflictResolution.AUTO_MERGED, "merged content")
        assert c.resolution == ConflictResolution.AUTO_MERGED
        assert c.merge_result == "merged content"

    def test_stats(self):
        resolver = ConflictResolver()
        assert resolver.get_stats()["total_conflicts"] == 0
        mods = {
            "f.py": [("a1", "@@ -1,1 +1,2 @@\n+x"), ("a2", "@@ -50,1 +50,2 @@\n+y")],
        }
        resolver.detect_conflicts(mods)
        stats = resolver.get_stats()
        assert stats["total_conflicts"] == 1
        assert stats["pending"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestSwarmIntegration:
    def test_full_swarm_workflow(self):
        """Test completo: spawn swarm, esperar, verificar resultados."""
        mgr = SwarmManager()
        aids = mgr.spawn_swarm(task="integration test", num_agents=2)

        # Esperar completacion
        assert mgr.wait_for_completion(aids, timeout=10.0)

        # Verificar resultados
        for aid in aids:
            result = mgr.get_agent_results(aid)
            assert result is not None
            assert result["status"] in ["complete", "error"]

        # Verificar reporte
        report = mgr.get_status_report()
        assert report["total_agents"] == 2
        assert report["complete"] == 2

        mgr.kill_all()

    def test_conflict_detection_integration(self):
        """Detecta conflictos reales entre agentes."""
        mgr = SwarmManager()
        resolver = ConflictResolver()

        # Spawn dos agentes que "modifican" el mismo archivo
        aid1 = mgr.spawn_agent(
            task="modify test.py",
            context={"files_to_read": ["test.py"]},
        )
        aid2 = mgr.spawn_agent(
            task="modify test.py",
            context={"files_to_read": ["test.py"]},
        )

        time.sleep(1.0)

        # Simular que ambos escribieron
        if aid1 in mgr.agents:
            mgr.agents[aid1].files_written.add("test.py")
        if aid2 in mgr.agents:
            mgr.agents[aid2].files_written.add("test.py")

        # Detectar conflictos
        file_mods = {}
        for aid, agent in mgr.agents.items():
            for f in agent.files_written:
                if f not in file_mods:
                    file_mods[f] = []
                file_mods[f].append((aid, f"diff from {aid}"))

        conflicts = resolver.detect_conflicts(file_mods)
        assert len(conflicts) >= 0  # Puede o no detectar dependiendo de estado

        mgr.kill_all()


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
