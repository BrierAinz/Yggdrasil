"""
Tests para Memory RAG (SessionStore + BackgroundConsolidator)
=============================================================
RED-GREEN-REFACTOR: TDD estricto para los nuevos módulos de memoria.

Los vestigios de la oscuridad se someten a juicio ante
el tribunal invisible de las pruebas.
"""

import json
import sqlite3
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def db_path(tmp_path):
    """Crea una DB aislada para tests."""
    return tmp_path / "test_memory_rag.db"


def _init_episodes_table(db_path):
    """Inicializa la tabla episodes necesaria para los tests."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                response TEXT,
                tools_used TEXT,
                embedding BLOB,
                session_id TEXT DEFAULT 'default',
                compressed INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                first_seen TEXT,
                last_seen TEXT,
                mentions INTEGER DEFAULT 1,
                context TEXT,
                embedding BLOB
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created TEXT,
                updated TEXT,
                UNIQUE(category, key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation_type TEXT NOT NULL DEFAULT 'related',
                strength REAL DEFAULT 1.0,
                first_seen TEXT,
                last_seen TEXT,
                context TEXT,
                UNIQUE(source, target, relation_type)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consolidation_queue (
                id INTEGER PRIMARY KEY,
                episode_id INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                priority REAL DEFAULT 1.0,
                FOREIGN KEY (episode_id) REFERENCES episodes(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consolidated_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                content TEXT NOT NULL,
                source_episodes TEXT,
                embedding BLOB,
                relevance_score REAL DEFAULT 1.0
            )
            """
        )
        conn.commit()


@pytest.fixture
def session_store(db_path):
    """Fixture de SessionStore con DB aislada y EmbeddingModel mockeado."""
    _init_episodes_table(db_path)
    with patch("Lilith.memory.session_store.EmbeddingModel") as MockEmbedder:
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        # Dummy embedding de 384 dims
        import numpy as np
        dummy_emb = np.random.rand(1, 384).astype(np.float32)
        mock_instance.encode.return_value = dummy_emb
        MockEmbedder.return_value = mock_instance

        from Lilith.memory.session_store import SessionStore
        store = SessionStore(db_path=db_path)
        store.embedder = mock_instance
        yield store


@pytest.fixture
def consolidator_db(db_path):
    """Fixture de BackgroundConsolidator con DB aislada."""
    _init_episodes_table(db_path)
    with patch("Lilith.memory.background_consolidator.MemoryConsolidation") as MockConsolidation, \
         patch("Lilith.memory.background_consolidator.MemoryGraph") as MockGraph:
        mock_consolidation = MagicMock()
        mock_consolidation.consolidate_episodes.return_value = {
            "merged_groups": 0, "deduplicated": 0, "processed": 0
        }

        mock_graph = MagicMock()

        MockConsolidation.return_value = mock_consolidation
        MockGraph.return_value = mock_graph

        from Lilith.memory.background_consolidator import BackgroundConsolidator
        bg = BackgroundConsolidator(db_path=db_path, interval_seconds=1)
        bg.consolidation = mock_consolidation
        bg.graph = mock_graph
        yield bg


# =====================================================================
# TestSessionStore
# =====================================================================

class TestSessionStore:
    """Tests para el SessionStore — el archivo de ecos perdidos."""

    def test_init_tables(self, session_store, db_path):
        """Las tablas de sesiones deben crearse al inicializar."""
        with sqlite3.connect(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            assert tables is not None
            assert tables[0] == "sessions"

    def test_save_and_load_session(self, session_store):
        """Guardar y cargar una sesión preserva todos los campos."""
        session_store.save_session(
            session_id="test-session-1",
            summary="Sesión de prueba con Python y Docker",
            episode_count=5,
            metadata={"topic": "devops", "language": "es"},
        )
        loaded = session_store.load_session("test-session-1")

        assert loaded is not None
        assert loaded["id"] == "test-session-1"
        assert loaded["summary"] == "Sesión de prueba con Python y Docker"
        assert loaded["episode_count"] == 5
        assert loaded["metadata"]["topic"] == "devops"

    def test_save_session_creates_timestamps(self, session_store):
        """Una sesión nueva debe tener created y last_active."""
        session_store.save_session(
            session_id="ts-test",
            summary="test",
            episode_count=1,
        )
        loaded = session_store.load_session("ts-test")

        assert loaded is not None
        assert loaded["created"] is not None
        assert loaded["last_active"] is not None
        assert len(loaded["created"]) > 10  # ISO format

    def test_save_session_update_preserves_created(self, session_store):
        """Actualizar una sesión preserva el created original."""
        session_store.save_session(
            session_id="update-test",
            summary="versión 1",
            episode_count=3,
        )
        first = session_store.load_session("update-test")
        original_created = first["created"]

        # Esperar un instante para que last_active cambie
        import time
        time.sleep(0.05)

        session_store.save_session(
            session_id="update-test",
            summary="versión 2",
            episode_count=5,
        )
        updated = session_store.load_session("update-test")

        assert updated["created"] == original_created
        assert updated["summary"] == "versión 2"
        assert updated["episode_count"] == 5

    def test_load_nonexistent_session(self, session_store):
        """Cargar una sesión inexistente retorna None."""
        result = session_store.load_session("no-existe")
        assert result is None

    def test_list_sessions(self, session_store):
        """list_sessions retorna sesiones ordenadas por last_active."""
        session_store.save_session("s1", "primera", 1)
        session_store.save_session("s2", "segunda", 2)
        session_store.save_session("s3", "tercera", 3)

        sessions = session_store.list_sessions()
        assert len(sessions) == 3
        # Ordenadas por last_active DESC — la más reciente primero
        assert sessions[0]["id"] == "s3"

    def test_list_sessions_limit(self, session_store):
        """list_sessions respeta el límite."""
        for i in range(10):
            session_store.save_session(f"lim-{i}", f"s{i}", i)

        sessions = session_store.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_list_sessions_default_limit(self, session_store):
        """list_sessions con límite por defecto (20)."""
        for i in range(25):
            session_store.save_session(f"def-{i}", f"s{i}", i)

        sessions = session_store.list_sessions()
        assert len(sessions) == 20

    def test_delete_session(self, session_store):
        """Eliminar una sesión la remueve del almacén."""
        session_store.save_session("to-delete", "borrar", 1)
        assert session_store.load_session("to-delete") is not None

        session_store.delete_session("to-delete")
        assert session_store.load_session("to-delete") is None

    def test_delete_nonexistent_session(self, session_store):
        """Eliminar una sesión inexistente no genera error."""
        # No debe lanzar excepción
        session_store.delete_session("ghost-session")

    def test_search_sessions_with_embeddings(self, session_store):
        """search_sessions con embeddings activos usa similitud coseno."""
        session_store.save_session(
            "search-1",
            "Discusión sobre programación en Python",
            3,
        )
        session_store.save_session(
            "search-2",
            "Receta de cocina mediterránea",
            2,
        )

        results = session_store.search_sessions("Python programming", limit=2)
        assert len(results) >= 1
        # Los resultados deben tener search_score
        for r in results:
            assert "search_score" in r

    def test_search_sessions_text_fallback(self, session_store):
        """search_sessions con texto keyword como fallback."""
        # Desactivar embedding
        session_store.embedder.is_available.return_value = False

        session_store.save_session(
            "fallback-1",
            "Discusión sobre programación Python",
            2,
        )
        session_store.save_session(
            "fallback-2",
            "Receta de cocina mediterránea",
            1,
        )

        results = session_store.search_sessions("Python", limit=5)
        assert len(results) >= 1
        # Al menos uno debe contener "Python"
        found_python = any(
            "python" in (r.get("summary") or "").lower() for r in results
        )
        assert found_python

    def test_search_sessions_no_results(self, session_store):
        """search_sessions con query sin matches retorna lista vacía."""
        session_store.embedder.is_available.return_value = False
        results = session_store.search_sessions("xyzabc123 improbable query", limit=5)
        assert isinstance(results, list)

    def test_get_relevant_context_with_sessions(self, session_store):
        """get_relevant_context retorna texto formateado."""
        session_store.save_session(
            "ctx-1",
            "Desarrollo de API con FastAPI y Docker",
            10,
            {"project": "Hermes"},
        )
        session_store.save_session(
            "ctx-2",
            "Optimización de base de datos SQLite",
            5,
        )

        context = session_store.get_relevant_context("API development")
        assert "CONTEXTO DE SESIONES PASADAS" in context

    def test_get_relevant_context_empty(self, session_store):
        """get_relevant_context sin sesiones retorna string vacío."""
        context = session_store.get_relevant_context("query vacío")
        assert context == ""

    def test_get_relevant_context_max_tokens(self, session_store):
        """get_relevant_context respeta max_tokens truncando."""
        # Crear varias sesiones con resúmenes largos
        for i in range(10):
            session_store.save_session(
                f"long-{i}",
                "A" * 500 + f" sesión {i}",
                i + 1,
            )

        # Con max_tokens muy bajo, solo debe incluir parte
        context = session_store.get_relevant_context("A", max_tokens=20)
        assert len(context) < 1000  # Debe estar truncado

    def test_auto_summary_basic(self, session_store):
        """auto_summary genera resumen con TF keyword extraction."""
        episodes = [
            {
                "user_input": "Cómo configurar Python para machine learning",
                "response": "Usa pip install scikit-learn y tensorflow",
                "timestamp": "2025-01-15T10:00:00",
            },
            {
                "user_input": "Qué librerías de Python usar para ML",
                "response": "Python tiene scikit-learn, tensorflow y pytorch",
                "timestamp": "2025-01-15T10:30:00",
            },
        ]
        summary = session_store.auto_summary(episodes)

        assert "episodios" in summary.lower() or "episodio" in summary.lower()
        assert "python" in summary.lower()

    def test_auto_summary_empty(self, session_store):
        """auto_summary con lista vacía retorna string vacío."""
        assert session_store.auto_summary([]) == ""

    def test_auto_summary_no_content(self, session_store):
        """auto_summary con episodios sin contenido genera resumen básico."""
        episodes = [{"id": 1}]  # Sin user_input ni response
        summary = session_store.auto_summary(episodes)
        # Debe producir algo — fallback
        assert isinstance(summary, str)

    def test_auto_summary_timestamps_in_summary(self, session_store):
        """auto_summary incluye rango de fechas en el resumen."""
        episodes = [
            {
                "user_input": "consulta sobre django",
                "response": "respuesta sobre django",
                "timestamp": "2025-03-01T09:00:00",
            },
            {
                "user_input": "otra consulta sobre django",
                "response": "otra respuesta",
                "timestamp": "2025-03-05T15:00:00",
            },
        ]
        summary = session_store.auto_summary(episodes)
        assert "2025-03-01" in summary
        assert "2025-03-05" in summary

    def test_metadata_serialization(self, session_store):
        """Metadata se serializa/deserializa correctamente como JSON."""
        metadata = {
            "project": "Hermes-Lilith",
            "tags": ["dark-fantasy", "memory-rag"],
            "config": {"model": "gpt-4", "temperature": 0.7},
        }
        session_store.save_session(
            "meta-test",
            "Sesión con metadata compleja",
            3,
            metadata=metadata,
        )
        loaded = session_store.load_session("meta-test")

        assert loaded["metadata"]["project"] == "Hermes-Lilith"
        assert loaded["metadata"]["tags"] == ["dark-fantasy", "memory-rag"]
        assert loaded["metadata"]["config"]["temperature"] == 0.7

    def test_save_session_embedding_stored(self, session_store, db_path):
        """Guardar una sesión con embedder disponible almacena el embedding."""
        session_store.save_session(
            "emb-test", "Sesión con embedding", 2,
        )
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT embedding FROM sessions WHERE id = ?",
                ("emb-test",),
            ).fetchone()
            assert row is not None
            assert row[0] is not None  # embedding blob existe

    def test_save_session_without_embedding(self, session_store):
        """Guardar sesión con embedder no disponible funciona igual."""
        session_store.embedder.is_available.return_value = False
        session_store.save_session(
            "no-emb", "Sesión sin embedding", 1,
        )
        loaded = session_store.load_session("no-emb")
        assert loaded is not None
        assert loaded["summary"] == "Sesión sin embedding"


# =====================================================================
# TestBackgroundConsolidator
# =====================================================================

class TestBackgroundConsolidator:
    """Tests para el BackgroundConsolidator — el hilo eterno."""

    def test_init_creates_thread(self, consolidator_db):
        """Al inicializar, el consolidador existe pero no está corriendo."""
        assert not consolidator_db.is_running

    def test_start_and_is_running(self, consolidator_db):
        """start() arranca el thread daemon."""
        consolidator_db.start()
        time.sleep(0.2)
        assert consolidator_db.is_running
        consolidator_db.stop()

    def test_stop_thread(self, consolidator_db):
        """stop() detiene el thread daemon."""
        consolidator_db.start()
        time.sleep(0.2)
        consolidator_db.stop()
        time.sleep(0.2)
        assert not consolidator_db.is_running

    def test_start_idempotent(self, consolidator_db):
        """Llamar start() múltiples veces no crea threads adicionales."""
        consolidator_db.start()
        consolidator_db.start()  # No debe fallar ni duplicar
        time.sleep(0.1)
        assert consolidator_db.is_running
        consolidator_db.stop()

    def test_stop_without_start(self, consolidator_db):
        """Llamar stop() sin start() no debe fallar."""
        consolidator_db.stop()  # No debe lanzar excepción

    def test_run_cycle_returns_dict(self, consolidator_db):
        """run_cycle() retorna dict con las claves esperadas."""
        result = consolidator_db.run_cycle()

        assert "merged" in result
        assert "facts_promoted" in result
        assert "relations_decayed" in result

    def test_run_cycle_tracks_stats(self, consolidator_db):
        """run_cycle() actualiza las estadísticas internas."""
        consolidator_db.run_cycle()
        stats = consolidator_db.stats

        assert stats["cycles_run"] == 1

    def test_run_cycle_multiple_times(self, consolidator_db):
        """Múltiples ciclos incrementan cycles_run."""
        consolidator_db.run_cycle()
        consolidator_db.run_cycle()
        consolidator_db.run_cycle()

        stats = consolidator_db.stats
        assert stats["cycles_run"] == 3

    def test_run_cycle_calls_consolidate_episodes(self, consolidator_db):
        """run_cycle() llama MemoryConsolidation.consolidate_episodes."""
        consolidator_db.run_cycle()
        consolidator_db.consolidation.consolidate_episodes.assert_called()

    def test_run_cycle_calls_decay_strength(self, consolidator_db):
        """run_cycle() llama graph.decay_strength."""
        consolidator_db.run_cycle()
        consolidator_db.graph.decay_strength.assert_called()

    def test_stats_initial_values(self, consolidator_db):
        """Las estadísticas arrancan en cero."""
        stats = consolidator_db.stats
        assert stats["cycles_run"] == 0
        assert stats["episodes_merged"] == 0
        assert stats["facts_promoted"] == 0

    def test_last_run_initial_empty(self, consolidator_db):
        """last_run arranca vacío."""
        assert consolidator_db.last_run == ""

    def test_last_run_updated_after_cycle(self, consolidator_db):
        """last_run se actualiza tras un ciclo."""
        consolidator_db.run_cycle()
        assert len(consolidator_db.last_run) > 0
        # Debe ser ISO format
        assert "T" in consolidator_db.last_run or "-" in consolidator_db.last_run

    def test_promote_frequent_facts_with_entities(self, db_path):
        """_promote_frequent_facts promueve entidades con >=3 menciones."""
        _init_episodes_table(db_path)

        # Insertar entidades con alta frecuencia
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO entities (name, type, mentions, first_seen, last_seen, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("python", "technology", 5, "2025-01-01", "2025-01-10", "Lenguaje de programación"),
            )
            conn.execute(
                "INSERT INTO entities (name, type, mentions, first_seen, last_seen, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("docker", "technology", 3, "2025-01-02", "2025-01-08", "Contenedores"),
            )
            conn.execute(
                "INSERT INTO entities (name, type, mentions, first_seen, last_seen, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("git", "technology", 1, "2025-01-03", "2025-01-03", "Control de versiones"),
            )
            conn.commit()

        with patch("Lilith.memory.background_consolidator.MemoryConsolidation") as MockConsolidation, \
             patch("Lilith.memory.background_consolidator.MemoryGraph") as MockGraph:
            mock_consolidation = MagicMock()
            mock_consolidation.consolidate_episodes.return_value = {
                "merged_groups": 0, "deduplicated": 0, "processed": 0
            }
            MockConsolidation.return_value = mock_consolidation
            MockGraph.return_value = MagicMock()

            from Lilith.memory.background_consolidator import BackgroundConsolidator
            bg = BackgroundConsolidator(db_path=db_path, interval_seconds=1)
            bg.consolidation = mock_consolidation

            promoted = bg._promote_frequent_facts()
            # Solo "python" (5) y "docker" (3) tienen >= 3 menciones
            assert promoted == 2

    def test_promote_facts_no_duplicates(self, db_path):
        """_promote_frequent_facts no inserta facts duplicados."""
        _init_episodes_table(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO entities (name, type, mentions, first_seen, last_seen, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("python", "technology", 4, "2025-01-01", "2025-01-10", "Lenguaje"),
            )
            conn.commit()

        with patch("Lilith.memory.background_consolidator.MemoryConsolidation") as MockConsolidation, \
             patch("Lilith.memory.background_consolidator.MemoryGraph") as MockGraph:
            mock_consolidation = MagicMock()
            MockConsolidation.return_value = mock_consolidation
            MockGraph.return_value = MagicMock()

            from Lilith.memory.background_consolidator import BackgroundConsolidator
            bg = BackgroundConsolidator(db_path=db_path, interval_seconds=1)

            # Primera promoción
            promoted1 = bg._promote_frequent_facts()
            assert promoted1 == 1

            # Segunda llamada — ya existe, no se duplica
            promoted2 = bg._promote_frequent_facts()
            assert promoted2 == 0

    def test_stats_episodes_merged(self, consolidator_db):
        """episodes_merged se incrementa cuando consolidate_episodes reporta merges."""
        consolidator_db.consolidation.consolidate_episodes.return_value = {
            "merged_groups": 3, "deduplicated": 0, "processed": 5
        }
        consolidator_db.run_cycle()

        assert consolidator_db.stats["episodes_merged"] == 3

    def test_stats_facts_promoted_tracking(self, db_path):
        """facts_promoted se acumula correctamente."""
        _init_episodes_table(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO entities (name, type, mentions, first_seen, last_seen, context) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("python", "technology", 4, "2025-01-01", "2025-01-10", "Lenguaje"),
            )
            conn.commit()

        with patch("Lilith.memory.background_consolidator.MemoryConsolidation") as MockConsolidation, \
             patch("Lilith.memory.background_consolidator.MemoryGraph") as MockGraph:
            mock_consolidation = MagicMock()
            MockConsolidation.return_value = mock_consolidation
            MockGraph.return_value = MagicMock()

            from Lilith.memory.background_consolidator import BackgroundConsolidator
            bg = BackgroundConsolidator(db_path=db_path, interval_seconds=1)
            bg.consolidation = mock_consolidation

            bg.run_cycle()
            assert bg.stats["facts_promoted"] == 1

    def test_thread_safety_stats(self, consolidator_db):
        """Las estadísticas son thread-safe (lecturas concurrentes no fallan)."""
        consolidator_db.run_cycle()

        results = []

        def read_stats():
            for _ in range(10):
                s = consolidator_db.stats
                results.append(s["cycles_run"])

        threads = [threading.Thread(target=read_stats) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Todas las lecturas deben ser >= 1 (el ciclo que corrimos)
        assert all(r >= 1 for r in results)

    def test_thread_safety_last_run(self, consolidator_db):
        """last_run es thread-safe."""
        consolidator_db.run_cycle()

        results = []
        threads = [
            threading.Thread(
                target=lambda: results.append(consolidator_db.last_run)
            )
            for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Todas las lecturas deben retornar el mismo string
        assert len(set(results)) == 1

    def test_run_cycle_handles_consolidation_error(self, consolidator_db):
        """run_cycle maneja errores de consolidación sin fallar."""
        consolidator_db.consolidation.consolidate_episodes.side_effect = Exception("Error simulado")
        # No debe lanzar excepción
        result = consolidator_db.run_cycle()
        assert result is not None

    def test_run_cycle_handles_graph_error(self, consolidator_db):
        """run_cycle maneja errores del grafo sin fallar."""
        consolidator_db.graph.decay_strength.side_effect = Exception("Error simulado")
        result = consolidator_db.run_cycle()
        assert result is not None

    def test_background_thread_executes_cycles(self, consolidator_db):
        """El thread daemon ejecuta ciclos periódicamente."""
        consolidator_db.interval = 1  # 1 segundo para test rápido
        consolidator_db.start()
        time.sleep(2.5)
        consolidator_db.stop()

        # Al menos 1 ciclo debe haberse ejecutado
        stats = consolidator_db.stats
        assert stats["cycles_run"] >= 1


# =====================================================================
# TestSessionStore + BackgroundConsolidator Integration
# =====================================================================

class TestMemoryRAGIntegration:
    """Tests de integración entre SessionStore y BackgroundConsolidator."""

    def test_session_store_auto_summary_with_real_episodes(self, db_path):
        """Auto_summary con episodios reales desde DB."""
        _init_episodes_table(db_path)

        # Insertar episodios
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (timestamp, user_input, response, session_id) "
                "VALUES (?, ?, ?, ?)",
                ("2025-01-15T10:00:00", "Cómo usar Python para data science", "Usa pandas y numpy", "s1"),
            )
            conn.execute(
                "INSERT INTO episodes (timestamp, user_input, response, session_id) "
                "VALUES (?, ?, ?, ?)",
                ("2025-01-15T11:00:00", "Instalar Python en Linux", "Usa apt-get install python3", "s1"),
            )
            conn.commit()

        with patch("Lilith.memory.session_store.EmbeddingModel") as MockEmbedder:
            mock_instance = MagicMock()
            mock_instance.is_available.return_value = True
            import numpy as np
            mock_instance.encode.return_value = np.random.rand(1, 384).astype(np.float32)
            MockEmbedder.return_value = mock_instance

            from Lilith.memory.session_store import SessionStore
            store = SessionStore(db_path=db_path)
            store.embedder = mock_instance

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM episodes WHERE session_id = ?", ("s1",)
                ).fetchall()
                episodes = [dict(r) for r in rows]

            summary = store.auto_summary(episodes)
            assert "python" in summary.lower()
            assert "2" in summary  # 2 episodios

    def test_consolidator_stats_immutability(self, consolidator_db):
        """stats retorna una copia, no la referencia interna."""
        consolidator_db.run_cycle()
        stats1 = consolidator_db.stats
        stats2 = consolidator_db.stats

        # Modificar la copia no afecta el original
        stats1["cycles_run"] = 999
        assert consolidator_db.stats["cycles_run"] == 1

    def test_save_and_search_multiple_sessions(self, session_store):
        """Guardar múltiples sesiones y buscar la más relevante."""
        sessions_data = [
            ("dev-python", "Desarrollo de API REST con Python y FastAPI", 8),
            ("dev-react", "Frontend con React y TypeScript", 5),
            ("dev-docker", "Configuración de Docker para despliegue", 4),
            ("cooking", "Recetas de cocina italiana", 3),
        ]

        for sid, summary, count in sessions_data:
            session_store.save_session(sid, summary, count)

        # Buscar sesiones sobre desarrollo
        results = session_store.search_sessions("Python development API", limit=2)
        # Debe priorizar sesiones sobre desarrollo/Python
        assert len(results) >= 1