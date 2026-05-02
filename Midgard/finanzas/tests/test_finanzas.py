"""
᛭ Tests para Midgard Finanzas — Tracker de Finanzas Personales ᛭
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest

# Asegurar que el módulo es importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finanzas_db import FinanzasDB, CATEGORIAS_PREDEFINIDAS, DB_PATH


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada test usa una DB temporal independiente."""
    db_file = tmp_path / "test_finanzas.db"
    monkeypatch.setattr("finanzas_db.DB_PATH", str(db_file))
    # Resetear singleton para crear nueva instancia
    FinanzasDB._instance = None
    db = FinanzasDB()
    yield db
    db.close()
    FinanzasDB._instance = None


# ─── Tests: FinanzasDB — Creación y esquema ────────────────────────────────────

class TestDBCreation:
    def test_singleton_returns_same_instance(self, isolated_db):
        db2 = FinanzasDB()
        assert db2 is isolated_db

    def test_tables_created(self, isolated_db):
        cursor = isolated_db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "transactions" in tables
        assert "budgets" in tables

    def test_predefined_categories_list(self):
        assert len(CATEGORIAS_PREDEFINIDAS) == 8
        assert "comida" in CATEGORIAS_PREDEFINIDAS
        assert "transporte" in CATEGORIAS_PREDEFINIDAS
        assert "vivienda" in CATEGORIAS_PREDEFINIDAS
        assert "entretenimiento" in CATEGORIAS_PREDEFINIDAS
        assert "salud" in CATEGORIAS_PREDEFINIDAS
        assert "educacion" in CATEGORIAS_PREDEFINIDAS
        assert "ahorro" in CATEGORIAS_PREDEFINIDAS
        assert "otros" in CATEGORIAS_PREDEFINIDAS


# ─── Tests: FinanzasDB — Transacciones ──────────────────────────────────────────

class TestTransactions:
    def test_add_gasto(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 150.0, "comida", "Almuerzo", "2025-05-01")
        assert tx_id > 0

    def test_add_ingreso(self, isolated_db):
        tx_id = isolated_db.add_transaction("ingreso", 5000.0, "ahorro", "Salario", "2025-05-01")
        assert tx_id > 0

    def test_add_gasto_default_date(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 50.0, "transporte")
        today = datetime.now().strftime("%Y-%m-%d")
        rows = isolated_db.get_transactions()
        assert rows[0]["date"] == today

    def test_add_transaction_invalid_type(self, isolated_db):
        with pytest.raises(ValueError, match="Tipo inválido"):
            isolated_db.add_transaction("invalido", 100.0, "comida")

    def test_add_transaction_negative_amount(self, isolated_db):
        with pytest.raises(ValueError, match="positivo"):
            isolated_db.add_transaction("gasto", -10.0, "comida")

    def test_add_transaction_zero_amount(self, isolated_db):
        with pytest.raises(ValueError, match="positivo"):
            isolated_db.add_transaction("gasto", 0, "comida")

    def test_get_transactions_all(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.add_transaction("ingreso", 3000.0, "ahorro", "", "2025-05-02")
        rows = isolated_db.get_transactions()
        assert len(rows) == 2

    def test_get_transactions_filter_type(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.add_transaction("ingreso", 3000.0, "ahorro", "", "2025-05-02")
        rows = isolated_db.get_transactions(tx_type="gasto")
        assert len(rows) == 1
        assert rows[0]["type"] == "gasto"

    def test_get_transactions_filter_category(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.add_transaction("gasto", 50.0, "transporte", "", "2025-05-02")
        rows = isolated_db.get_transactions(category="comida")
        assert len(rows) == 1
        assert rows[0]["category"] == "comida"

    def test_get_transactions_filter_month(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.add_transaction("gasto", 200.0, "transporte", "", "2025-06-01")
        rows = isolated_db.get_transactions(month="2025-05")
        assert len(rows) == 1


# ─── Tests: FinanzasDB — Balance ────────────────────────────────────────────────

class TestBalance:
    def test_balance_empty_month(self, isolated_db):
        bal = isolated_db.get_balance("2025-01")
        assert bal["ingresos"] == 0.0
        assert bal["gastos"] == 0.0
        assert bal["balance"] == 0.0

    def test_balance_with_transactions(self, isolated_db):
        isolated_db.add_transaction("ingreso", 5000.0, "ahorro", "", "2025-05-01")
        isolated_db.add_transaction("gasto", 1500.0, "vivienda", "", "2025-05-05")
        isolated_db.add_transaction("gasto", 500.0, "comida", "", "2025-05-10")
        bal = isolated_db.get_balance("2025-05")
        assert bal["ingresos"] == 5000.0
        assert bal["gastos"] == 2000.0
        assert bal["balance"] == 3000.0

    def test_balance_negative(self, isolated_db):
        isolated_db.add_transaction("ingreso", 1000.0, "ahorro", "", "2025-05-01")
        isolated_db.add_transaction("gasto", 1500.0, "vivienda", "", "2025-05-05")
        bal = isolated_db.get_balance("2025-05")
        assert bal["balance"] == -500.0


# ─── Tests: FinanzasDB — Reporte ───────────────────────────────────────────────

class TestReport:
    def test_report_by_category(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.add_transaction("gasto", 200.0, "comida", "", "2025-05-02")
        isolated_db.add_transaction("ingreso", 5000.0, "ahorro", "", "2025-05-01")
        rows = isolated_db.get_report_by_category("2025-05")
        assert len(rows) >= 2
        comida_row = [r for r in rows if r["category"] == "comida" and r["type"] == "gasto"][0]
        assert comida_row["total"] == 300.0
        assert comida_row["count"] == 2

    def test_report_empty_month(self, isolated_db):
        rows = isolated_db.get_report_by_category("2025-01")
        assert len(rows) == 0


# ─── Tests: FinanzasDB — Presupuestos ──────────────────────────────────────────

class TestBudgets:
    def test_set_and_get_budget(self, isolated_db):
        isolated_db.set_budget("comida", 3000.0)
        limit = isolated_db.get_budget("comida")
        assert limit == 3000.0

    def test_update_budget(self, isolated_db):
        isolated_db.set_budget("comida", 3000.0)
        isolated_db.set_budget("comida", 4000.0)
        limit = isolated_db.get_budget("comida")
        assert limit == 4000.0

    def test_get_nonexistent_budget(self, isolated_db):
        result = isolated_db.get_budget("nonexistent")
        assert result is None

    def test_get_all_budgets(self, isolated_db):
        isolated_db.set_budget("comida", 3000.0)
        isolated_db.set_budget("transporte", 1500.0)
        budgets = isolated_db.get_all_budgets()
        assert len(budgets) == 2

    def test_check_budget_within_limit(self, isolated_db):
        isolated_db.set_budget("comida", 3000.0)
        isolated_db.add_transaction("gasto", 1500.0, "comida", "", "2025-05-01")
        results = isolated_db.check_budget("2025-05")
        assert len(results) == 1
        assert results[0]["spent"] == 1500.0
        assert results[0]["remaining"] == 1500.0
        assert results[0]["over"] is False

    def test_check_budget_over_limit(self, isolated_db):
        isolated_db.set_budget("comida", 1000.0)
        isolated_db.add_transaction("gasto", 1500.0, "comida", "", "2025-05-01")
        results = isolated_db.check_budget("2025-05")
        assert results[0]["over"] is True
        assert results[0]["pct"] > 100.0


# ─── Tests: FinanzasDB — Delete & Update ────────────────────────────────────────

class TestCRUD:
    def test_delete_transaction(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        assert isolated_db.delete_transaction(tx_id) is True
        assert isolated_db.delete_transaction(9999) is False

    def test_update_transaction_amount(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.update_transaction(tx_id, amount=200.0)
        rows = isolated_db.get_transactions()
        assert rows[0]["amount"] == 200.0

    def test_update_transaction_category(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.update_transaction(tx_id, category="transporte")
        rows = isolated_db.get_transactions()
        assert rows[0]["category"] == "transporte"

    def test_update_transaction_nothing(self, isolated_db):
        tx_id = isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        assert isolated_db.update_transaction(tx_id) is False


# ─── Tests: FinanzasDB — Reset ──────────────────────────────────────────────────

class TestReset:
    def test_reset_clears_all(self, isolated_db):
        isolated_db.add_transaction("gasto", 100.0, "comida", "", "2025-05-01")
        isolated_db.set_budget("comida", 3000.0)
        isolated_db.reset()
        assert len(isolated_db.get_transactions()) == 0
        assert len(isolated_db.get_all_budgets()) == 0