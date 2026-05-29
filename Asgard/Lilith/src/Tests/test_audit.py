"""
Tests for Audit Trail

v4.2.8: Tests unitarios para el sistema de auditoría.
"""
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from src.core.audit.audit_logger import AuditLogger
from src.core.audit.events import AuditEvent, EventCategory, EventType
from src.core.audit.storage import AuditStorage, StorageConfig


class TestAuditEvent:
    """Tests para eventos de auditoría."""

    def test_event_creation(self):
        """Test creación de evento."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.TOOL_EXECUTION,
            actor="user_123",
            resource="tool:calculator",
            action="execute",
            status="success",
            details={"input": "2+2", "output": "4"},
        )

        assert event.event_type == EventType.TOOL_EXECUTION
        assert event.actor == "user_123"
        assert event.status == "success"

    def test_event_to_dict(self):
        """Test serialización a dict."""
        now = datetime.utcnow()
        event = AuditEvent(
            timestamp=now,
            event_type=EventType.AUTH_LOGIN,
            actor="user_123",
            resource="user:user_123",
            action="login",
            status="success",
        )

        data = event.to_dict()

        assert data["event_type"] == "auth_login"
        assert data["actor"] == "user_123"
        assert data["timestamp"] == now.isoformat()

    def test_event_from_dict(self):
        """Test deserialización desde dict."""
        now = datetime.utcnow().isoformat()
        data = {
            "timestamp": now,
            "event_type": "tool_execution",
            "actor": "system",
            "resource": "tool:test",
            "action": "execute",
            "status": "success",
            "details": {},
            "ip_address": "127.0.0.1",
            "request_id": "req_123",
            "session_id": "sess_456",
            "metadata": {},
        }

        event = AuditEvent.from_dict(data)

        assert event.event_type == EventType.TOOL_EXECUTION
        assert event.actor == "system"

    def test_event_to_jsonl(self):
        """Test conversión a JSONL."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.TOOL_SUCCESS,
            actor="system",
            resource="tool:test",
            action="execute",
            status="success",
        )

        jsonl = event.to_jsonl()

        assert isinstance(jsonl, str)
        data = json.loads(jsonl)
        assert data["actor"] == "system"


class TestEventCategory:
    """Tests para categorías de eventos."""

    def test_get_category_security(self):
        """Test categoría security."""
        cat = EventCategory.get_category(EventType.AUTH_LOGIN)
        assert cat == "security"

    def test_get_category_operational(self):
        """Test categoría operational."""
        cat = EventCategory.get_category(EventType.TOOL_EXECUTION)
        assert cat == "operational"

    def test_get_category_data(self):
        """Test categoría data."""
        cat = EventCategory.get_category(EventType.FILE_ACCESS)
        assert cat == "data"

    def test_get_category_system(self):
        """Test categoría system."""
        cat = EventCategory.get_category(EventType.SYSTEM_STARTUP)
        assert cat == "system"


class TestAuditStorage:
    """Tests para almacenamiento de auditoría."""

    def setup_method(self):
        """Setup con directorio temporal."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=Path(self.temp_dir))
        self.storage = AuditStorage(self.config)

    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_event(self):
        """Test agregar evento."""
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type=EventType.TOOL_EXECUTION,
            actor="user_1",
            resource="tool:test",
            action="execute",
            status="success",
        )

        result = self.storage.append(event)

        assert result is True
        # Verificar que se creó el archivo
        files = list(Path(self.temp_dir).glob("audit_*.jsonl"))
        assert len(files) > 0

    def test_query_events(self):
        """Test consulta de eventos."""
        # Agregar algunos eventos
        for i in range(5):
            event = AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_EXECUTION,
                actor=f"user_{i}",
                resource="tool:test",
                action="execute",
                status="success",
            )
            self.storage.append(event)

        results = self.storage.query(limit=3)

        assert len(results) == 3

    def test_query_with_filter(self):
        """Test consulta con filtro."""
        # Evento exitoso
        self.storage.append(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_SUCCESS,
                actor="user_1",
                resource="tool:test",
                action="execute",
                status="success",
            )
        )

        # Evento fallido
        self.storage.append(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_FAILURE,
                actor="user_2",
                resource="tool:test",
                action="execute",
                status="failure",
            )
        )

        results = self.storage.query(status="success")

        assert len(results) == 1
        assert results[0].status == "success"

    def test_query_by_actor(self):
        """Test consulta por actor."""
        self.storage.append(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_EXECUTION,
                actor="target_user",
                resource="tool:test",
                action="execute",
                status="success",
            )
        )

        self.storage.append(
            AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_EXECUTION,
                actor="other_user",
                resource="tool:test",
                action="execute",
                status="success",
            )
        )

        results = self.storage.query(actor="target_user")

        assert len(results) == 1
        assert results[0].actor == "target_user"

    def test_get_stats(self):
        """Test obtención de estadísticas."""
        for i in range(10):
            event = AuditEvent(
                timestamp=datetime.utcnow(),
                event_type=EventType.TOOL_EXECUTION,
                actor="user",
                resource="tool:test",
                action="execute",
                status="success",
            )
            self.storage.append(event)

        stats = self.storage.get_stats()

        assert stats["document_count"] == 10
        assert stats["base_path"] == str(self.temp_dir)


class TestAuditLogger:
    """Tests para el logger de auditoría."""

    def setup_method(self):
        """Setup."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=Path(self.temp_dir))
        self.storage = AuditStorage(self.config)
        self.logger = AuditLogger(self.storage)

    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_simple_event(self):
        """Test logging de evento simple."""
        result = self.logger.log(
            event_type=EventType.TOOL_EXECUTION,
            resource="tool:calculator",
            action="execute",
            status="success",
        )

        assert result is True

    def test_log_tool_execution(self):
        """Test logging de ejecución de tool."""
        result = self.logger.log_tool_execution(
            tool_name="calculator",
            params={"expression": "2+2"},
            success=True,
            result="4",
        )

        assert result is True

    def test_log_auth(self):
        """Test logging de autenticación."""
        result = self.logger.log_auth(
            action="login", user_id="user_123", success=True, ip_address="192.168.1.1"
        )

        assert result is True

    def test_log_permission_denied(self):
        """Test logging de permiso denegado."""
        result = self.logger.log_permission(
            user_id="user_123", resource="admin:panel", action="access", granted=False
        )

        assert result is True

    def test_log_file_access(self):
        """Test logging de acceso a archivo."""
        result = self.logger.log_file_access(
            file_path="/sensitive/data.txt", action="read", success=True
        )

        assert result is True

    def test_query_logged_events(self):
        """Test consulta de eventos logueados."""
        self.logger.log_tool_execution(tool_name="test_tool", params={}, success=True)

        events = self.logger.query(limit=10)

        assert len(events) >= 1

    def test_get_stats(self):
        """Test obtención de estadísticas."""
        for i in range(5):
            self.logger.log(
                event_type=EventType.TOOL_EXECUTION,
                resource="tool:test",
                action="execute",
                status="success",
            )

        stats = self.logger.get_stats()

        assert "total_files" in stats
        assert "total_size_mb" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
