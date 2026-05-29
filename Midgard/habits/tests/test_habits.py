"""
᛭ Tests para Midgard Habits — Tracker de Hábitos Personal ᛭
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# Asegurar que el módulo es importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from habits_db import HabitsDB, DB_PATH


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada test usa una DB temporal independiente."""
    db_file = tmp_path / "test_habits.db"
    monkeypatch.setattr("habits_db.DB_PATH", str(db_file))
    # Resetear singleton para crear nueva instancia
    HabitsDB._instance = None
    db = HabitsDB()
    yield db
    db.close()
    HabitsDB._instance = None


# ─── Tests: HabitsDB — Creación y esquema ─────────────────────────────────────

class TestDBCreation:
    def test_singleton_returns_same_instance(self, isolated_db):
        db2 = HabitsDB()
        assert db2 is isolated_db

    def test_tables_created(self, isolated_db):
        cursor = isolated_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "habits" in tables
        assert "habit_checks" in tables

    def test_habits_table_schema(self, isolated_db):
        cursor = isolated_db.conn.cursor()
        cursor.execute("PRAGMA table_info(habits)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "id" in columns
        assert "name" in columns
        assert "frequency" in columns
        assert "icon" in columns
        assert "active" in columns
        assert "created" in columns

    def test_checks_table_schema(self, isolated_db):
        cursor = isolated_db.conn.cursor()
        cursor.execute("PRAGMA table_info(habit_checks)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "habit_id" in columns
        assert "date" in columns
        assert "timestamp" in columns


# ─── Tests: HabitsDB — Add Habit ──────────────────────────────────────────────

class TestAddHabit:
    def test_add_habit_basic(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar", "diario", "🧘")
        assert habit_id > 0

    def test_add_habit_default_frequency(self, isolated_db):
        habit_id = isolated_db.add_habit("Leer")
        habit = isolated_db.get_habit(habit_id)
        assert habit["frequency"] == "diario"

    def test_add_habit_default_icon(self, isolated_db):
        habit_id = isolated_db.add_habit("Ejercicio")
        habit = isolated_db.get_habit(habit_id)
        assert habit["icon"] == "]"

    def test_add_habit_semanal(self, isolated_db):
        habit_id = isolated_db.add_habit("Gym", "semanal", "💪")
        habit = isolated_db.get_habit(habit_id)
        assert habit["frequency"] == "semanal"

    def test_add_habit_n_por_semana(self, isolated_db):
        habit_id = isolated_db.add_habit("Correr", "3/semana", "🏃")
        habit = isolated_db.get_habit(habit_id)
        assert habit["frequency"] == "3/semana"

    def test_add_habit_empty_name_raises(self, isolated_db):
        with pytest.raises(ValueError, match="vacío"):
            isolated_db.add_habit("  ")

    def test_add_habit_invalid_frequency_raises(self, isolated_db):
        with pytest.raises(ValueError, match="Frecuencia inválida"):
            isolated_db.add_habit("Test", "anual")

    def test_add_habit_duplicate_name_raises(self, isolated_db):
        isolated_db.add_habit("Meditar")
        with pytest.raises(Exception):  # UNIQUE constraint
            isolated_db.add_habit("Meditar")


# ─── Tests: HabitsDB — Get Habit ───────────────────────────────────────────────

class TestGetHabit:
    def test_get_habit_by_id(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar", "diario", "🧘")
        habit = isolated_db.get_habit(habit_id)
        assert habit is not None
        assert habit["name"] == "Meditar"
        assert habit["id"] == habit_id

    def test_get_habit_by_name(self, isolated_db):
        isolated_db.add_habit("Meditar", "diario", "🧘")
        habit = isolated_db.get_habit("Meditar")
        assert habit is not None
        assert habit["name"] == "Meditar"

    def test_get_habit_by_id_string(self, isolated_db):
        habit_id = isolated_db.add_habit("Leer", "diario", "📖")
        habit = isolated_db.get_habit(str(habit_id))
        assert habit is not None
        assert habit["name"] == "Leer"

    def test_get_habit_nonexistent(self, isolated_db):
        habit = isolated_db.get_habit("NoExiste")
        assert habit is None

    def test_get_habit_nonexistent_id(self, isolated_db):
        habit = isolated_db.get_habit(9999)
        assert habit is None


# ─── Tests: HabitsDB — List Habits ────────────────────────────────────────────

class TestListHabits:
    def test_list_habits_active_only(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.add_habit("Leer")
        habits = isolated_db.list_habits(active_only=True)
        assert len(habits) == 2

    def test_list_habits_includes_archived(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.add_habit("Leer")
        isolated_db.archive_habit("Meditar")
        habits = isolated_db.list_habits(active_only=False)
        assert len(habits) == 2

    def test_list_habits_excludes_archived_by_default(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.add_habit("Leer")
        isolated_db.archive_habit("Meditar")
        habits = isolated_db.list_habits(active_only=True)
        assert len(habits) == 1
        assert habits[0]["name"] == "Leer"


# ─── Tests: HabitsDB — Archive/Unarchive ──────────────────────────────────────

class TestArchive:
    def test_archive_habit(self, isolated_db):
        isolated_db.add_habit("Meditar")
        result = isolated_db.archive_habit("Meditar")
        assert result is True
        habit = isolated_db.get_habit("Meditar")
        assert habit["active"] == 0

    def test_archive_nonexistent(self, isolated_db):
        result = isolated_db.archive_habit("NoExiste")
        assert result is False

    def test_unarchive_habit(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.archive_habit("Meditar")
        result = isolated_db.unarchive_habit("Meditar")
        assert result is True
        habit = isolated_db.get_habit("Meditar")
        assert habit["active"] == 1

    def test_unarchive_nonexistent(self, isolated_db):
        result = isolated_db.unarchive_habit("NoExiste")
        assert result is False


# ─── Tests: HabitsDB — Check/Uncheck ────────────────────────────────────────

class TestCheckUncheck:
    def test_check_habit_today(self, isolated_db):
        isolated_db.add_habit("Meditar")
        result = isolated_db.check_habit("Meditar")
        assert result is True

    def test_check_habit_specific_date(self, isolated_db):
        isolated_db.add_habit("Meditar")
        result = isolated_db.check_habit("Meditar", "2025-05-01")
        assert result is True

    def test_check_habit_idempotent(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.check_habit("Meditar", "2025-05-01")
        result = isolated_db.check_habit("Meditar", "2025-05-01")
        assert result is False  # Ya existía

    def test_check_habit_by_id(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        result = isolated_db.check_habit(habit_id)
        assert result is True

    def test_check_habit_nonexistent_raises(self, isolated_db):
        with pytest.raises(ValueError, match="no encontrado"):
            isolated_db.check_habit("NoExiste")

    def test_uncheck_habit(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.check_habit("Meditar", "2025-05-01")
        result = isolated_db.uncheck_habit("Meditar", "2025-05-01")
        assert result is True

    def test_uncheck_habit_not_checked(self, isolated_db):
        isolated_db.add_habit("Meditar")
        result = isolated_db.uncheck_habit("Meditar", "2025-05-01")
        assert result is False

    def test_uncheck_habit_nonexistent_raises(self, isolated_db):
        with pytest.raises(ValueError, match="no encontrado"):
            isolated_db.uncheck_habit("NoExiste")


# ─── Tests: HabitsDB — Streaks ──────────────────────────────────────────────

class TestStreaks:
    def test_streak_no_checks(self, isolated_db):
        isolated_db.add_habit("Meditar")
        streak = isolated_db.get_streak("Meditar")
        assert streak["current_streak"] == 0
        assert streak["best_streak"] == 0
        assert streak["last_check"] is None

    def test_streak_single_check_today(self, isolated_db):
        isolated_db.add_habit("Meditar")
        today = datetime.now().strftime("%Y-%m-%d")
        isolated_db.check_habit("Meditar", today)
        streak = isolated_db.get_streak("Meditar")
        assert streak["current_streak"] >= 1
        assert streak["best_streak"] >= 1

    def test_streak_daily_consecutive(self, isolated_db):
        isolated_db.add_habit("Meditar")
        today = datetime.now()
        for i in range(5):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            isolated_db.check_habit("Meditar", d)
        streak = isolated_db.get_streak("Meditar")
        assert streak["current_streak"] == 5
        assert streak["best_streak"] == 5

    def test_streak_daily_broken(self, isolated_db):
        isolated_db.add_habit("Meditar")
        today = datetime.now()
        # 3 días consecutivos, gap, 1 día
        for i in range(3):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            isolated_db.check_habit("Meditar", d)
        isolated_db.check_habit("Meditar", (today - timedelta(days=5)).strftime("%Y-%m-%d"))
        streak = isolated_db.get_streak("Meditar")
        assert streak["current_streak"] == 3
        assert streak["best_streak"] == 3

    def test_streak_nonexistent_habit_raises(self, isolated_db):
        with pytest.raises(ValueError, match="no encontrado"):
            isolated_db.get_streak("NoExiste")


# ─── Tests: HabitsDB — Progress ──────────────────────────────────────────────

class TestProgress:
    def test_progress_empty(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        progress = isolated_db.get_habit_progress(habit_id, 7)
        assert len(progress) == 7
        assert all(not d["checked"] for d in progress)

    def test_progress_with_checks(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        today = datetime.now()
        isolated_db.check_habit(habit_id, today.strftime("%Y-%m-%d"))
        isolated_db.check_habit(habit_id, (today - timedelta(days=1)).strftime("%Y-%m-%d"))
        progress = isolated_db.get_habit_progress(habit_id, 7)
        checked_days = [d for d in progress if d["checked"]]
        assert len(checked_days) == 2


# ─── Tests: HabitsDB — Stats ───────────────────────────────────────────────

class TestStats:
    def test_stats_empty(self, isolated_db):
        stats = isolated_db.get_stats("semana")
        assert stats["total_habits"] == 0
        assert stats["active_habits"] == 0
        assert stats["completed_today"] == 0
        assert stats["completion_rate"] == 0.0
        assert stats["best_streak_habit"] is None

    def test_stats_with_habits(self, isolated_db):
        isolated_db.add_habit("Meditar")
        isolated_db.add_habit("Leer")
        today = datetime.now().strftime("%Y-%m-%d")
        isolated_db.check_habit("Meditar", today)
        
        stats = isolated_db.get_stats("semana")
        assert stats["active_habits"] == 2
        assert stats["completed_today"] >= 1

    def test_stats_month_period(self, isolated_db):
        isolated_db.add_habit("Meditar")
        stats = isolated_db.get_stats("mes")
        assert stats["period_days"] == 30


# ─── Tests: HabitsDB — Get Checks ─────────────────────────────────────────────

class TestGetChecks:
    def test_get_checks_with_date_range(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        isolated_db.check_habit(habit_id, "2025-05-01")
        isolated_db.check_habit(habit_id, "2025-05-03")
        isolated_db.check_habit(habit_id, "2025-05-05")
        
        checks = isolated_db.get_checks(habit_id, start_date="2025-05-02", end_date="2025-05-04")
        assert len(checks) == 1
        assert checks[0]["date"] == "2025-05-03"

    def test_get_checks_all(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        isolated_db.check_habit(habit_id, "2025-05-01")
        isolated_db.check_habit(habit_id, "2025-05-03")
        
        checks = isolated_db.get_checks(habit_id)
        assert len(checks) == 2


# ─── Tests: HabitsDB — Reset ──────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_all(self, isolated_db):
        habit_id = isolated_db.add_habit("Meditar")
        isolated_db.check_habit(habit_id, "2025-05-01")
        isolated_db.reset()
        habits = isolated_db.list_habits(active_only=False)
        assert len(habits) == 0