#!/usr/bin/env python3
"""
🪵 Yggdrasil — Midgard Recipes Database
SQLite storage for the Recipe Manager of the Nine Realms.
"""

import sqlite3
import os
import json
import random
from datetime import datetime
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recipes.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cook_time INTEGER DEFAULT 0,
    difficulty TEXT DEFAULT 'medio',
    servings INTEGER DEFAULT 2,
    tags TEXT DEFAULT '',
    created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    amount TEXT DEFAULT '',
    unit TEXT DEFAULT '',
    name TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    step_num INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meal_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day INTEGER NOT NULL,
    recipe_id INTEGER NOT NULL,
    slot TEXT DEFAULT 'cena',
    created TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
"""


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


class RecipeDB:
    """Database interface for the Midgard Recipe Manager."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(db_path)

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    # ── CREATE ──────────────────────────────────────────────
    def add_recipe(
        self,
        name: str,
        cook_time: int = 0,
        difficulty: str = "medio",
        servings: int = 2,
        tags: Optional[list] = None,
        ingredients: Optional[list] = None,
        instructions: Optional[list] = None,
    ) -> int:
        """Add a new recipe. Returns the recipe id."""
        tags_str = ",".join(tags) if tags else ""
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO recipes (name, cook_time, difficulty, servings, tags) VALUES (?, ?, ?, ?, ?)",
                (name, cook_time, difficulty, servings, tags_str),
            )
            recipe_id = cur.lastrowid

            if ingredients:
                for ing in ingredients:
                    conn.execute(
                        "INSERT INTO ingredients (recipe_id, amount, unit, name) VALUES (?, ?, ?, ?)",
                        (recipe_id, ing.get("amount", ""), ing.get("unit", ""), ing["name"]),
                    )

            if instructions:
                for i, step in enumerate(instructions, 1):
                    conn.execute(
                        "INSERT INTO instructions (recipe_id, step_num, text) VALUES (?, ?, ?)",
                        (recipe_id, i, step),
                    )

            conn.commit()
            return recipe_id
        finally:
            conn.close()

    # ── READ ────────────────────────────────────────────────
    def get_recipe(self, identifier) -> Optional[dict]:
        """Get a recipe by id or name. Returns dict with ingredients and instructions."""
        conn = self._conn()
        try:
            # Try as int (id) first, then as name
            if isinstance(identifier, int) or identifier.isdigit():
                row = conn.execute("SELECT * FROM recipes WHERE id = ?", (int(identifier),)).fetchone()
            else:
                row = conn.execute("SELECT * FROM recipes WHERE name = ?", (identifier,)).fetchone()

            if not row:
                return None

            recipe = dict(row)
            recipe["tags"] = [t.strip() for t in recipe["tags"].split(",") if t.strip()]

            ing_rows = conn.execute("SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY id", (recipe["id"],)).fetchall()
            recipe["ingredients"] = [dict(r) for r in ing_rows]

            inst_rows = conn.execute("SELECT * FROM instructions WHERE recipe_id = ? ORDER BY step_num", (recipe["id"],)).fetchall()
            recipe["instructions"] = [dict(r) for r in inst_rows]

            return recipe
        finally:
            conn.close()

    def list_recipes(
        self,
        tag: Optional[str] = None,
        difficulty: Optional[str] = None,
        time_max: Optional[int] = None,
    ) -> list:
        """List recipes with optional filters."""
        conn = self._conn()
        try:
            query = "SELECT * FROM recipes WHERE 1=1"
            params = []

            if tag:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            if time_max is not None:
                query += " AND cook_time <= ?"
                params.append(time_max)

            query += " ORDER BY name"
            rows = conn.execute(query, params).fetchall()
            recipes = []
            for row in rows:
                r = dict(row)
                r["tags"] = [t.strip() for t in r["tags"].split(",") if t.strip()]
                recipes.append(r)
            return recipes
        finally:
            conn.close()

    # ── SEARCH ──────────────────────────────────────────────
    def search(self, query: str) -> list:
        """Search recipes by name, ingredient, or tag."""
        conn = self._conn()
        try:
            like = f"%{query}%"
            # Search in name
            rows_name = conn.execute("SELECT * FROM recipes WHERE name LIKE ?", (like,)).fetchall()
            # Search in tags
            rows_tags = conn.execute("SELECT * FROM recipes WHERE tags LIKE ?", (like,)).fetchall()
            # Search in ingredients
            rows_ing = conn.execute(
                "SELECT DISTINCT r.* FROM recipes r JOIN ingredients i ON r.id = i.recipe_id WHERE i.name LIKE ?",
                (like,),
            ).fetchall()

            seen = set()
            results = []
            for row in list(rows_name) + list(rows_tags) + list(rows_ing):
                if row["id"] not in seen:
                    seen.add(row["id"])
                    r = dict(row)
                    r["tags"] = [t.strip() for t in r["tags"].split(",") if t.strip()]
                    results.append(r)
            return results
        finally:
            conn.close()

    # ── UPDATE ──────────────────────────────────────────────
    def edit_recipe(
        self,
        identifier,
        name: Optional[str] = None,
        cook_time: Optional[int] = None,
        difficulty: Optional[str] = None,
        servings: Optional[int] = None,
        tags: Optional[list] = None,
    ) -> bool:
        """Edit a recipe's metadata. Returns True if updated."""
        recipe = self.get_recipe(identifier)
        if not recipe:
            return False

        conn = self._conn()
        try:
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if cook_time is not None:
                updates.append("cook_time = ?")
                params.append(cook_time)
            if difficulty is not None:
                updates.append("difficulty = ?")
                params.append(difficulty)
            if servings is not None:
                updates.append("servings = ?")
                params.append(servings)
            if tags is not None:
                updates.append("tags = ?")
                params.append(",".join(tags))

            if not updates:
                return False

            params.append(recipe["id"])
            conn.execute(f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return True
        finally:
            conn.close()

    # ── DELETE ──────────────────────────────────────────────
    def delete_recipe(self, identifier) -> bool:
        """Delete a recipe by id or name."""
        recipe = self.get_recipe(identifier)
        if not recipe:
            return False

        conn = self._conn()
        try:
            conn.execute("DELETE FROM instructions WHERE recipe_id = ?", (recipe["id"],))
            conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe["id"],))
            conn.execute("DELETE FROM meal_plans WHERE recipe_id = ?", (recipe["id"],))
            conn.execute("DELETE FROM recipes WHERE id = ?", (recipe["id"],))
            conn.commit()
            return True
        finally:
            conn.close()

    # ── ADD INGREDIENTS / INSTRUCTIONS ──────────────────────
    def add_ingredient(self, recipe_id: int, amount: str, unit: str, name: str) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO ingredients (recipe_id, amount, unit, name) VALUES (?, ?, ?, ?)",
                (recipe_id, amount, unit, name),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def add_instruction(self, recipe_id: int, step_num: int, text: str) -> int:
        conn = self._conn()
        try:
            cur = conn.execute(
                "INSERT INTO instructions (recipe_id, step_num, text) VALUES (?, ?, ?)",
                (recipe_id, step_num, text),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    # ── MEAL PLANNING ──────────────────────────────────────
    def get_random_recipes(self, count: int) -> list:
        """Get N random recipes for meal planning."""
        conn = self._conn()
        try:
            rows = conn.execute("SELECT * FROM recipes ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def generate_meal_plan(self, days: int = 7) -> list:
        """Generate a random meal plan for N days. Returns list of dicts."""
        conn = self._conn()
        try:
            # Clear existing plan
            conn.execute("DELETE FROM meal_plans")

            all_recipes = conn.execute("SELECT id FROM recipes").fetchall()
            if not all_recipes:
                return []

            ids = [r["id"] for r in all_recipes]
            plan = []
            slots = ["desayuno", "comida", "cena"]

            for day in range(1, days + 1):
                for slot in slots:
                    recipe_id = random.choice(ids)
                    conn.execute(
                        "INSERT INTO meal_plans (day, recipe_id, slot) VALUES (?, ?, ?)",
                        (day, recipe_id, slot),
                    )
                    plan.append({"day": day, "slot": slot, "recipe_id": recipe_id})

            conn.commit()
            return plan
        finally:
            conn.close()

    def get_meal_plan(self) -> list:
        """Get current meal plan."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT mp.day, mp.slot, r.id as recipe_id, r.name as recipe_name, "
                "r.cook_time, r.difficulty FROM meal_plans mp "
                "JOIN recipes r ON mp.recipe_id = r.id "
                "ORDER BY mp.day, mp.slot"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── SHOPPING LIST ───────────────────────────────────────
    def get_shopping_list(self, days: int = 7) -> list:
        """Aggregate ingredients from meal plan into a shopping list."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT i.amount, i.unit, i.name FROM meal_plans mp "
                "JOIN ingredients i ON mp.recipe_id = i.recipe_id "
                "WHERE mp.day <= ? ORDER BY i.name",
                (days,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


if __name__ == "__main__":
    init_db()
    print("⚔️ Database initialized.")