"""
᛭ Finanzas DB — SQLite Storage para el Tracker de Finanzas Personales ᛭
Módulo de persistencia en el reino de Midgard.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional


# ─── Rutas ────────────────────────────────────────────────────────────────────

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "finanzas.db")

CATEGORIAS_PREDEFINIDAS = [
    "comida",
    "transporte",
    "vivienda",
    "entretenimiento",
    "salud",
    "educacion",
    "ahorro",
    "otros",
]


# ─── Singleton ─────────────────────────────────────────────────────────────────

class FinanzasDB:
    """Singleton para la conexión SQLite del tracker de finanzas."""

    _instance: Optional["FinanzasDB"] = None

    def __new__(cls) -> "FinanzasDB":
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
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT    NOT NULL CHECK(type IN ('gasto','ingreso')),
                amount      REAL    NOT NULL CHECK(amount > 0),
                category    TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                date        TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS budgets (
                category      TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL CHECK(monthly_limit > 0)
            );

            CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_trans_cat  ON transactions(category);
            CREATE INDEX IF NOT EXISTS idx_trans_type ON transactions(type);
            """
        )
        self.conn.commit()

    # ── Transacciones ──────────────────────────────────────────────────────

    def add_transaction(
        self,
        tx_type: str,
        amount: float,
        category: str,
        description: str = "",
        date: str | None = None,
    ) -> int:
        """Agrega una transacción y retorna su id."""
        if tx_type not in ("gasto", "ingreso"):
            raise ValueError(f"Tipo inválido: {tx_type}. Debe ser 'gasto' o 'ingreso'.")
        if amount <= 0:
            raise ValueError("El monto debe ser positivo.")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.execute(
            "INSERT INTO transactions (type, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (tx_type, amount, category, description, date),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_transactions(
        self,
        tx_type: str | None = None,
        category: str | None = None,
        month: str | None = None,
    ) -> list[dict]:
        """Consulta transacciones con filtros opcionales."""
        query = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if tx_type:
            query += " AND type = ?"
            params.append(tx_type)
        if category:
            query += " AND category = ?"
            params.append(category)
        if month:
            query += " AND date LIKE ?"
            params.append(f"{month}%")
        query += " ORDER BY date DESC, id DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def delete_transaction(self, tx_id: int) -> bool:
        """Elimina una transacción por id. Retorna True si existía."""
        cursor = self.conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_transaction(
        self,
        tx_id: int,
        amount: float | None = None,
        category: str | None = None,
        description: str | None = None,
        date: str | None = None,
    ) -> bool:
        """Actualiza campos de una transacción existente."""
        fields = []
        params: list = []
        if amount is not None:
            fields.append("amount = ?")
            params.append(amount)
        if category is not None:
            fields.append("category = ?")
            params.append(category)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if date is not None:
            fields.append("date = ?")
            params.append(date)
        if not fields:
            return False
        params.append(tx_id)
        cursor = self.conn.execute(
            f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?", params
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ── Agregaciones ───────────────────────────────────────────────────────

    def get_balance(self, month: str) -> dict:
        """Retorna {ingresos, gastos, balance} para un mes YYYY-MM."""
        rows = self.conn.execute(
            "SELECT type, SUM(amount) as total FROM transactions WHERE date LIKE ? GROUP BY type",
            (f"{month}%",),
        ).fetchall()
        ingresos = 0.0
        gastos = 0.0
        for r in rows:
            if r["type"] == "ingreso":
                ingresos = r["total"]
            elif r["type"] == "gasto":
                gastos = r["total"]
        return {
            "ingresos": ingresos,
            "gastos": gastos,
            "balance": ingresos - gastos,
        }

    def get_report_by_category(self, month: str, tx_type: str | None = None) -> list[dict]:
        """Reporte agrupado por categoría para un mes."""
        query = """
            SELECT category, type, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE date LIKE ?
        """
        params: list = [f"{month}%"]
        if tx_type:
            query += " AND type = ?"
            params.append(tx_type)
        query += " GROUP BY category, type ORDER BY total DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ── Presupuestos ────────────────────────────────────────────────────────

    def set_budget(self, category: str, monthly_limit: float) -> None:
        """Establece o actualiza el presupuesto mensual de una categoría."""
        self.conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (category, monthly_limit),
        )
        self.conn.commit()

    def get_budget(self, category: str) -> float | None:
        """Retorna el límite mensual de una categoría, o None."""
        row = self.conn.execute(
            "SELECT monthly_limit FROM budgets WHERE category = ?", (category,)
        ).fetchone()
        return row["monthly_limit"] if row else None

    def get_all_budgets(self) -> list[dict]:
        """Retorna todos los presupuestos configurados."""
        rows = self.conn.execute(
            "SELECT category, monthly_limit FROM budgets ORDER BY category"
        ).fetchall()
        return [dict(r) for r in rows]

    def check_budget(self, month: str) -> list[dict]:
        """Compara presupuestos vs gastos reales del mes."""
        budgets = self.get_all_budgets()
        result = []
        for b in budgets:
            cat = b["category"]
            limit = b["monthly_limit"]
            row = self.conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as spent FROM transactions "
                "WHERE category = ? AND type = 'gasto' AND date LIKE ?",
                (cat, f"{month}%"),
            ).fetchone()
            spent = row["spent"] if row else 0.0
            remaining = limit - spent
            result.append(
                {
                    "category": cat,
                    "limit": limit,
                    "spent": spent,
                    "remaining": remaining,
                    "pct": round(spent / limit * 100, 1) if limit > 0 else 0.0,
                    "over": spent > limit,
                }
            )
        return result

    # ── Limpieza ────────────────────────────────────────────────────────────

    def close(self) -> None:
        self.conn.close()

    def reset(self) -> None:
        """Elimina todas las tablas y las recrea. Solo para tests."""
        self.conn.execute("DROP TABLE IF EXISTS transactions")
        self.conn.execute("DROP TABLE IF EXISTS budgets")
        self.conn.commit()
        self._create_tables()


# ─── Helper ────────────────────────────────────────────────────────────────

def get_db() -> FinanzasDB:
    """Retorna la instancia singleton de FinanzasDB."""
    return FinanzasDB()