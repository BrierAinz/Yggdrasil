"""
᛭ Habits DB — SQLite Storage para el Tracker de Hábitos ᛭
Módulo de persistencia en el reino de Midgard.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional


# ─── Rutas ────────────────────────────────────────────────────────────────────

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "habits.db")

FREQUENCIES = ("diario", "semanal")


# ─── Singleton ───────────────────────────────────────────────────────────────

class HabitsDB:
    """Singleton para la conexión SQLite del tracker de hábitos."""

    _instance: Optional["HabitsDB"] = None

    def __new__(cls) -> "HabitsDB":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        os.makedirs(DB_DIR, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ── Esquema ────────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                frequency   TEXT    NOT NULL DEFAULT 'diario',
                icon        TEXT    DEFAULT ']',
                active      INTEGER NOT NULL DEFAULT 1,
                created     TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habit_checks (
                habit_id    INTEGER NOT NULL,
                date        TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                PRIMARY KEY (habit_id, date),
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_habits_name   ON habits(name);
            CREATE INDEX IF NOT EXISTS idx_habits_active ON habits(active);
            CREATE INDEX IF NOT EXISTS idx_checks_date   ON habit_checks(date);
            CREATE INDEX IF NOT EXISTS idx_checks_habit  ON habit_checks(habit_id);
            """
        )
        self.conn.commit()

    # ── Hábitos CRUD ──────────────────────────────────────────────────────

    def add_habit(
        self,
        name: str,
        frequency: str = "diario",
        icon: str = "]",
    ) -> int:
        """Crea un hábito y retorna su id."""
        name = name.strip()
        if not name:
            raise ValueError("El nombre del hábito no puede estar vacío.")
        if "/" in frequency and frequency.endswith("/semana"):
            # Formato N/semana — validar N
            try:
                n = int(frequency.split("/")[0])
                if n < 1 or n > 7:
                    raise ValueError
            except (ValueError, IndexError):
                raise ValueError(f"Frecuencia inválida: {frequency}. Use 'diario', 'semanal', o 'N/semana' (1-7).")
        elif frequency not in FREQUENCIES:
            raise ValueError(f"Frecuencia inválida: {frequency}. Use 'diario', 'semanal', o 'N/semana'.")
        created = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            "INSERT INTO habits (name, frequency, icon, active, created) VALUES (?, ?, ?, 1, ?)",
            (name, frequency, icon, created),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_habit(self, name_or_id: str | int) -> Optional[dict]:
        """Busca un hábito por nombre o id. Retorna dict o None."""
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            row = self.conn.execute(
                "SELECT * FROM habits WHERE id = ?", (int(name_or_id),)
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM habits WHERE name = ?", (name_or_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_habits(self, active_only: bool = True) -> list[dict]:
        """Lista hábitos. Si active_only=True, solo los activos."""
        if active_only:
            rows = self.conn.execute(
                "SELECT * FROM habits WHERE active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM habits ORDER BY active DESC, id"
            ).fetchall()
        return [dict(r) for r in rows]

    def archive_habit(self, name_or_id: str | int) -> bool:
        """Archiva un hábito (lo marca como inactivo). Retorna True si existía."""
        habit = self.get_habit(name_or_id)
        if not habit:
            return False
        self.conn.execute(
            "UPDATE habits SET active = 0 WHERE id = ?", (habit["id"],)
        )
        self.conn.commit()
        return True

    def unarchive_habit(self, name_or_id: str | int) -> bool:
        """Reactiva un hábito archivado. Retorna True si existía."""
        habit = self.get_habit(name_or_id)
        if not habit:
            return False
        self.conn.execute(
            "UPDATE habits SET active = 1 WHERE id = ?", (habit["id"],)
        )
        self.conn.commit()
        return True

    # ── Checks ────────────────────────────────────────────────────────────

    def check_habit(self, name_or_id: str | int, date: Optional[str] = None) -> bool:
        """Marca un hábito como completado en una fecha. Retorna True si se insertó."""
        habit = self.get_habit(name_or_id)
        if not habit:
            raise ValueError(f"Hábito '{name_or_id}' no encontrado.")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        try:
            self.conn.execute(
                "INSERT INTO habit_checks (habit_id, date, timestamp) VALUES (?, ?, ?)",
                (habit["id"], date, datetime.now().isoformat()),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Ya existe para esa fecha — idempotente
            return False

    def uncheck_habit(self, name_or_id: str | int, date: Optional[str] = None) -> bool:
        """Desmarca un hábito en una fecha. Retorna True si existía."""
        habit = self.get_habit(name_or_id)
        if not habit:
            raise ValueError(f"Hábito '{name_or_id}' no encontrado.")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            "DELETE FROM habit_checks WHERE habit_id = ? AND date = ?",
            (habit["id"], date),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_checks(self, habit_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> list[dict]:
        """Obtiene los registros de check de un hábito en un rango de fechas."""
        query = "SELECT * FROM habit_checks WHERE habit_id = ?"
        params: list = [habit_id]
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        query += " ORDER BY date"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ── Streaks ──────────────────────────────────────────────────────────

    def get_streak(self, name_or_id: str | int) -> dict:
        """Calcula la racha actual y la mejor racha de un hábito.
        
        Retorna: {"current_streak": int, "best_streak": int, "last_check": str|None}
        """
        habit = self.get_habit(name_or_id)
        if not habit:
            raise ValueError(f"Hábito '{name_or_id}' no encontrado.")

        habit_id = habit["id"]
        frequency = habit["frequency"]

        # Obtener todas las fechas con check, ordenadas
        rows = self.conn.execute(
            "SELECT date FROM habit_checks WHERE habit_id = ? ORDER BY date",
            (habit_id,),
        ).fetchall()
        dates_checked = [r["date"] for r in rows]

        if not dates_checked:
            return {"current_streak": 0, "best_streak": 0, "last_check": None}

        # Calcular racha según frecuencia
        if frequency == "diario":
            return self._calc_daily_streak(dates_checked)
        elif frequency == "semanal":
            return self._calc_weekly_streak(dates_checked)
        else:
            # N/semana — tratar similar a semanal
            return self._calc_weekly_streak(dates_checked)

    def _calc_daily_streak(self, dates_checked: list[str]) -> dict:
        """Calcula racha para hábitos diarios."""
        best_streak = 1
        current_streak = 0
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Calcular mejor racha
        streak = 1
        for i in range(1, len(dates_checked)):
            prev = datetime.strptime(dates_checked[i - 1], "%Y-%m-%d")
            curr = datetime.strptime(dates_checked[i], "%Y-%m-%d")
            diff = (curr - prev).days
            if diff == 1:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 1

        if len(dates_checked) == 1:
            best_streak = 1

        # Calcular racha actual
        last_check = dates_checked[-1]
        if last_check == today or last_check == yesterday:
            # Contar hacia atrás desde la última fecha
            current_streak = 1
            for i in range(len(dates_checked) - 1, 0, -1):
                prev = datetime.strptime(dates_checked[i - 1], "%Y-%m-%d")
                curr = datetime.strptime(dates_checked[i], "%Y-%m-%d")
                diff = (curr - prev).days
                if diff == 1:
                    current_streak += 1
                else:
                    break
        else:
            current_streak = 0

        return {
            "current_streak": current_streak,
            "best_streak": best_streak,
            "last_check": last_check,
        }

    def _calc_weekly_streak(self, dates_checked: list[str]) -> dict:
        """Calcula racha para hábitos semanales (semana = cualquier check en esa semana)."""
        # Convertir fechas a semanas (ISO week)
        weeks_checked = set()
        for d in dates_checked:
            dt = datetime.strptime(d, "%Y-%m-%d")
            weeks_checked.add((dt.isocalendar()[0], dt.isocalendar()[1]))

        sorted_weeks = sorted(weeks_checked)
        if not sorted_weeks:
            return {"current_streak": 0, "best_streak": 0, "last_check": None}

        best_streak = 1
        streak = 1
        for i in range(1, len(sorted_weeks)):
            prev_year, prev_week = sorted_weeks[i - 1]
            curr_year, curr_week = sorted_weeks[i]
            # Verificar semanas consecutivas
            prev_dt = datetime.strptime(f"{prev_year}-{prev_week}-1", "%G-%V-%u")
            curr_dt = datetime.strptime(f"{curr_year}-{curr_week}-1", "%G-%V-%u")
            diff_weeks = (curr_dt - prev_dt).days // 7
            if diff_weeks == 1:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 1

        if len(sorted_weeks) == 1:
            best_streak = 1

        # Racha actual: si la última semana es esta semana o la pasada
        today = datetime.now()
        current_week = (today.isocalendar()[0], today.isocalendar()[1])
        last_week = (today - timedelta(weeks=1))
        last_week_key = (last_week.isocalendar()[0], last_week.isocalendar()[1])

        if sorted_weeks[-1] == current_week or sorted_weeks[-1] == last_week_key:
            current_streak = 1
            for i in range(len(sorted_weeks) - 1, 0, -1):
                prev_year_w, prev_week_w = sorted_weeks[i - 1]
                curr_year_w, curr_week_w = sorted_weeks[i]
                prev_dt_w = datetime.strptime(f"{prev_year_w}-{prev_week_w}-1", "%G-%V-%u")
                curr_dt_w = datetime.strptime(f"{curr_year_w}-{curr_week_w}-1", "%G-%V-%u")
                diff_w = (curr_dt_w - prev_dt_w).days // 7
                if diff_w == 1:
                    current_streak += 1
                else:
                    break
        else:
            current_streak = 0

        return {
            "current_streak": current_streak,
            "best_streak": best_streak,
            "last_check": dates_checked[-1],
        }

    # ── Stats ────────────────────────────────────────────────────────────

    def get_stats(self, period: str = "semana") -> dict:
        """Estadísticas generales del periodo.
        
        Args:
            period: 'semana' o 'mes'
        
        Retorna: {
            "total_habits": int,
            "active_habits": int,
            "completed_today": int,
            "completion_rate": float,  # porcentaje en el periodo
            "best_streak_habit": dict|None,  # hábito con mejor racha
            "period_checks": int,
            "period_days": int,
        }
        """
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()

        if period == "semana":
            start = (now - timedelta(days=6)).strftime("%Y-%m-%d")
            period_days = 7
        else:  # mes
            start = (now - timedelta(days=29)).strftime("%Y-%m-%d")
            period_days = 30

        active_habits = self.list_habits(active_only=True)
        all_habits = self.list_habits(active_only=False)
        total_habits = len(all_habits)
        active_count = len(active_habits)

        # Completados hoy
        completed_today = len(self.conn.execute(
            "SELECT COUNT(DISTINCT habit_id) FROM habit_checks WHERE date = ?",
            (today,),
        ).fetchone()) if active_count > 0 else 0

        # Checks en el periodo
        period_checks = self.conn.execute(
            "SELECT COUNT(*) FROM habit_checks WHERE date >= ? AND date <= ?",
            (start, today),
        ).fetchone()[0]

        # Total esperado en el periodo
        expected = active_count * period_days
        completion_rate = round((period_checks / expected * 100), 1) if expected > 0 else 0.0

        # Mejor racha
        best_streak_habit = None
        best_streak_val = 0
        for h in active_habits:
            try:
                streak_info = self.get_streak(h["id"])
                if streak_info["best_streak"] > best_streak_val:
                    best_streak_val = streak_info["best_streak"]
                    best_streak_habit = {**h, **streak_info}
            except ValueError:
                continue

        return {
            "total_habits": total_habits,
            "active_habits": active_count,
            "completed_today": completed_today,
            "completion_rate": completion_rate,
            "best_streak_habit": best_streak_habit,
            "period_checks": period_checks,
            "period_days": period_days,
        }

    def get_habit_progress(self, habit_id: int, days: int = 7) -> list[dict]:
        """Progreso de un hábito en los últimos N días.
        
        Retorna: [{"date": str, "checked": bool}, ...]
        """
        today = datetime.now()
        result = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            row = self.conn.execute(
                "SELECT 1 FROM habit_checks WHERE habit_id = ? AND date = ?",
                (habit_id, d),
            ).fetchone()
            result.append({"date": d, "checked": row is not None})
        return result

    # ── Limpieza ──────────────────────────────────────────────────────────

    def close(self) -> None:
        self.conn.close()

    def reset(self) -> None:
        """Elimina todas las tablas y las recrea. Solo para tests."""
        self.conn.execute("DROP TABLE IF EXISTS habit_checks")
        self.conn.execute("DROP TABLE IF EXISTS habits")
        self.conn.commit()
        self._create_tables()


# ─── Helper ────────────────────────────────────────────────────────────────

def get_db() -> HabitsDB:
    """Retorna la instancia singleton de HabitsDB."""
    return HabitsDB()