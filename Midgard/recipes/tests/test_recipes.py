#!/usr/bin/env python3
"""
🪵 Yggdrasil — Tests for Midgard Recipe Manager
"""

import os
import sys
import json
import tempfile
import unittest

# Ensure module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recipes_db import RecipeDB


class TestRecipeDB(unittest.TestCase):
    """Tests for the RecipeDB SQLite backend."""

    def setUp(self):
        """Create a fresh in-memory-ish DB for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db = RecipeDB(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # ── ADD ──────────────────────────────────────────────────
    def test_add_recipe_basic(self):
        """Add a recipe with all fields."""
        rid = self.db.add_recipe(
            name="Estofado de Dragón",
            cook_time=60,
            difficulty="dificil",
            servings=4,
            tags=["carne", "fuego"],
            ingredients=[
                {"amount": "500", "unit": "g", "name": "carne de dragón"},
                {"amount": "2", "unit": "tazas", "name": "caldo"},
            ],
            instructions=["Cortar la carne", "Hervir en caldo por 60 min"],
        )
        self.assertEqual(rid, 1)

    def test_add_recipe_minimal(self):
        """Add a recipe with just a name."""
        rid = self.db.add_recipe(name="Pan Rúnico")
        self.assertEqual(rid, 1)
        recipe = self.db.get_recipe(1)
        self.assertEqual(recipe["name"], "Pan Rúnico")
        self.assertEqual(recipe["cook_time"], 0)
        self.assertEqual(recipe["difficulty"], "medio")

    def test_add_multiple_recipes(self):
        """Add several recipes and verify IDs."""
        id1 = self.db.add_recipe(name="Primera")
        id2 = self.db.add_recipe(name="Segunda")
        id3 = self.db.add_recipe(name="Tercera")
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 3)

    # ── GET ──────────────────────────────────────────────────
    def test_get_recipe_by_id(self):
        self.db.add_recipe(name="Sopa de Valquiria", cook_time=30)
        recipe = self.db.get_recipe(1)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Sopa de Valquiria")
        self.assertEqual(recipe["cook_time"], 30)

    def test_get_recipe_by_name(self):
        self.db.add_recipe(name="Sopa de Valquiria", cook_time=30)
        recipe = self.db.get_recipe("Sopa de Valquiria")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["id"], 1)

    def test_get_recipe_not_found(self):
        recipe = self.db.get_recipe(999)
        self.assertIsNone(recipe)
        recipe = self.db.get_recipe("Inexistente")
        self.assertIsNone(recipe)

    def test_get_recipe_with_ingredients_and_steps(self):
        rid = self.db.add_recipe(
            name="Tarta Nórdica",
            ingredients=[
                {"amount": "3", "unit": "tazas", "name": "harina"},
                {"amount": "1", "unit": "taza", "name": "azúcar"},
            ],
            instructions=["Mezclar harina y azúcar", "Hornear 30 min"],
        )
        recipe = self.db.get_recipe(rid)
        self.assertEqual(len(recipe["ingredients"]), 2)
        self.assertEqual(len(recipe["instructions"]), 2)
        self.assertEqual(recipe["ingredients"][0]["name"], "harina")

    # ── LIST ─────────────────────────────────────────────────
    def test_list_all_recipes(self):
        self.db.add_recipe(name="A")
        self.db.add_recipe(name="B")
        recipes = self.db.list_recipes()
        self.assertEqual(len(recipes), 2)

    def test_list_filter_by_difficulty(self):
        self.db.add_recipe(name="Fácil", difficulty="facil")
        self.db.add_recipe(name="Difícil", difficulty="dificil")
        recipes = self.db.list_recipes(difficulty="facil")
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0]["name"], "Fácil")

    def test_list_filter_by_time(self):
        self.db.add_recipe(name="Rápida", cook_time=15)
        self.db.add_recipe(name="Lenta", cook_time=120)
        recipes = self.db.list_recipes(time_max=30)
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0]["name"], "Rápida")

    def test_list_filter_by_tag(self):
        self.db.add_recipe(name="Pescado Asado", tags=["pescado", "fuego"])
        self.db.add_recipe(name="Ensalada Rúnica", tags=["ensalada", "saludable"])
        recipes = self.db.list_recipes(tag="pescado")
        self.assertEqual(len(recipes), 1)

    # ── SEARCH ───────────────────────────────────────────────
    def test_search_by_name(self):
        self.db.add_recipe(name="Estofado de Dragón")
        results = self.db.search("Dragón")
        self.assertEqual(len(results), 1)

    def test_search_by_ingredient(self):
        self.db.add_recipe(
            name="Postre de Helheim",
            ingredients=[{"amount": "1", "unit": "taza", "name": "bayas del inframundo"}],
        )
        results = self.db.search("bayas")
        self.assertEqual(len(results), 1)

    def test_search_by_tag(self):
        self.db.add_recipe(name="Comida Rúnica", tags=["rúnico", "mágico"])
        results = self.db.search("mágico")
        self.assertEqual(len(results), 1)

    def test_search_no_results(self):
        self.db.add_recipe(name="Pocado")
        results = self.db.search("xyz123inexistente")
        self.assertEqual(len(results), 0)

    # ── EDIT ──────────────────────────────────────────────────
    def test_edit_recipe_name(self):
        self.db.add_recipe(name="Viejo Nombre")
        result = self.db.edit_recipe(1, name="Nuevo Nombre")
        self.assertTrue(result)
        recipe = self.db.get_recipe(1)
        self.assertEqual(recipe["name"], "Nuevo Nombre")

    def test_edit_recipe_cook_time(self):
        self.db.add_recipe(name="Estofado", cook_time=30)
        self.db.edit_recipe(1, cook_time=45)
        recipe = self.db.get_recipe(1)
        self.assertEqual(recipe["cook_time"], 45)

    def test_edit_recipe_tags(self):
        self.db.add_recipe(name="Estofado", tags=["carne"])
        self.db.edit_recipe(1, tags=["carne", "fuego"])
        recipe = self.db.get_recipe(1)
        self.assertIn("fuego", recipe["tags"])

    def test_edit_nonexistent_recipe(self):
        result = self.db.edit_recipe(999, name="Nada")
        self.assertFalse(result)

    # ── DELETE ────────────────────────────────────────────────
    def test_delete_recipe(self):
        self.db.add_recipe(name="A eliminar")
        result = self.db.delete_recipe(1)
        self.assertTrue(result)
        recipe = self.db.get_recipe(1)
        self.assertIsNone(recipe)

    def test_delete_nonexistent(self):
        result = self.db.delete_recipe(999)
        self.assertFalse(result)

    def test_delete_cascades_ingredients(self):
        rid = self.db.add_recipe(
            name="Temporal",
            ingredients=[{"amount": "1", "unit": "kg", "name": "algo"}],
        )
        self.db.delete_recipe(rid)
        recipe = self.db.get_recipe(rid)
        self.assertIsNone(recipe)

    # ── MEAL PLAN ─────────────────────────────────────────────
    def test_generate_meal_plan(self):
        for i in range(5):
            self.db.add_recipe(name=f"Receta {i+1}", cook_time=15 * (i + 1))
        plan = self.db.generate_meal_plan(days=2)
        self.assertGreater(len(plan), 0)
        # 2 days x 3 slots = 6 entries
        self.assertEqual(len(plan), 6)

    def test_generate_meal_plan_empty_db(self):
        plan = self.db.generate_meal_plan(days=3)
        self.assertEqual(len(plan), 0)

    def test_get_meal_plan(self):
        for i in range(3):
            self.db.add_recipe(name=f"Receta {i+1}")
        self.db.generate_meal_plan(days=1)
        plan = self.db.get_meal_plan()
        self.assertEqual(len(plan), 3)  # 1 day x 3 slots

    # ── SHOPPING LIST ─────────────────────────────────────────
    def test_shopping_list(self):
        self.db.add_recipe(
            name="Poción de Fuerza",
            ingredients=[
                {"amount": "2", "unit": "tazas", "name": "leche de cabra"},
                {"amount": "1", "unit": "cucharada", "name": "mirra"},
            ],
        )
        self.db.add_recipe(
            name="Pan de Batalla",
            ingredients=[
                {"amount": "3", "unit": "tazas", "name": "harina"},
            ],
        )
        self.db.generate_meal_plan(days=1)
        items = self.db.get_shopping_list(days=1)
        self.assertGreater(len(items), 0)

    # ── ADD INGREDIENT / INSTRUCTION ───────────────────────────
    def test_add_ingredient_to_existing(self):
        rid = self.db.add_recipe(name="Sopa")
        iid = self.db.add_ingredient(rid, "1", "taza", "agua")
        self.assertIsNotNone(iid)
        recipe = self.db.get_recipe(rid)
        self.assertEqual(len(recipe["ingredients"]), 1)
        self.assertEqual(recipe["ingredients"][0]["name"], "agua")

    def test_add_instruction_to_existing(self):
        rid = self.db.add_recipe(name="Caldo Místico")
        sid = self.db.add_instruction(rid, 1, "Hervir el agua")
        self.assertIsNotNone(sid)
        recipe = self.db.get_recipe(rid)
        self.assertEqual(len(recipe["instructions"]), 1)
        self.assertEqual(recipe["instructions"][0]["text"], "Hervir el agua")


class TestRecipeCLI(unittest.TestCase):
    """Tests for CLI argument parsing."""

    def test_parser_add_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["add", "Mi Receta", "--time", "30", "--difficulty", "dificil", "--tags", "carne,fuego", "--servings", "4"])
        self.assertEqual(args.nombre, "Mi Receta")
        self.assertEqual(args.time, 30)
        self.assertEqual(args.difficulty, "dificil")
        self.assertEqual(args.tags, "carne,fuego")
        self.assertEqual(args.servings, 4)

    def test_parser_list_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["list", "--tag", "postre", "--difficulty", "facil", "--time-max", "20"])
        self.assertEqual(args.tag, "postre")
        self.assertEqual(args.difficulty, "facil")
        self.assertEqual(args.time_max, 20)

    def test_parser_show_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["show", "Estofado"])
        self.assertEqual(args.nombre_or_id, "Estofado")

    def test_parser_search_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["search", "dragón"])
        self.assertEqual(args.query, "dragón")

    def test_parser_edit_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["edit", "1", "--name", "Nuevo", "--time", "45"])
        self.assertEqual(args.nombre_or_id, "1")
        self.assertEqual(args.name, "Nuevo")
        self.assertEqual(args.time, 45)

    def test_parser_export_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["export", "Mi Receta", "--format", "json"])
        self.assertEqual(args.nombre_or_id, "Mi Receta")
        self.assertEqual(args.format, "json")

    def test_parser_plan_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["plan", "--days", "5"])
        self.assertEqual(args.days, 5)

    def test_parser_shopping_args(self):
        from midgard_recipes import build_parser
        parser = build_parser()
        args = parser.parse_args(["shopping", "--days", "3"])
        self.assertEqual(args.days, 3)


class TestRecipeExport(unittest.TestCase):
    """Test export functionality end-to-end."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db = RecipeDB(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_export_json_contains_all_fields(self):
        rid = self.db.add_recipe(
            name="Pastel de Odín",
            cook_time=45,
            difficulty="dificil",
            servings=8,
            tags=["dulce", "festivo"],
            ingredients=[
                {"amount": "3", "unit": "tazas", "name": "harina"},
                {"amount": "2", "unit": "tazas", "name": "miel"},
            ],
            instructions=["Mezclar harina y miel", "Hornear 45 minutos"],
        )
        recipe = self.db.get_recipe(rid)
        json_str = json.dumps(recipe, ensure_ascii=False)
        data = json.loads(json_str)
        self.assertEqual(data["name"], "Pastel de Odín")
        self.assertEqual(data["cook_time"], 45)
        self.assertEqual(data["difficulty"], "dificil")
        self.assertEqual(len(data["ingredients"]), 2)
        self.assertEqual(len(data["instructions"]), 2)

    def test_export_markdown_contains_headers(self):
        rid = self.db.add_recipe(
            name="Sopa de Freya",
            cook_time=20,
            difficulty="facil",
            ingredients=[{"amount": "1", "unit": "litro", "name": "caldo"}],
            instructions=["Calentar caldo", "Servir"],
        )
        recipe = self.db.get_recipe(rid)
        # Simulate what cmd_export does for md format
        lines = [f"# 📜 {recipe['name']}"]
        markdown = "\n".join(lines)
        self.assertIn("# 📜 Sopa de Freya", markdown)


if __name__ == "__main__":
    unittest.main()