# RecipeAlchemist — Generador de Recetas por Ingredientes Disponibles

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Ingresa lo que tienes en la nevera, encuentra recetas, ajusta porciones, genera lista de compras, y aprende tus preferencias con el tiempo.

**Architecture:** CLI para input de ingredientes → búsqueda en DB local de recetas → ranking por match → ajuste de porciones → learning de preferencias en SQLite → lista de compras.

**Tech Stack:** Python 3.11+, Typer, Rich, SQLite, httpx (spoonacular API optional), fuzzy matching (thefuzz), fractions (stdlib).

**Realm:** Midgard/RecipeAlchemist/

---

## Task 1: Scaffold del proyecto

**Files:**
- Create: `Midgard/RecipeAlchemist/pyproject.toml`
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/__init__.py`
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/cli.py`
- Create: `Midgard/RecipeAlchemist/tests/__init__.py`

Dependencies: typer, rich, thefuzz, httpx, python-Levenshtein.

**Commit:** `feat(recipealchemist): scaffold project`

---

## Task 2: Modelo de datos y DB

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/models.py`
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/db.py`
- Create: `Midgard/RecipeAlchemist/tests/test_db.py`

```python
@dataclass
class Ingredient:
    id: int | None
    name: str
    category: str = ""  # vegetable, protein, grain, spice, dairy...
    unit: str = ""  # g, ml, piece, cup...
    pantry_staple: bool = False  # salt, oil, pepper

@dataclass
class Recipe:
    id: int | None
    name: str
    description: str = ""
    servings: int = 4
    prep_time: int = 0  # minutes
    cook_time: int = 0  # minutes
    difficulty: str = "medium"  # easy, medium, hard
    tags: list[str] = field(default_factory=list)
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

@dataclass
class RecipeIngredient:
    ingredient_id: int
    amount: float
    unit: str
    optional: bool = False
    substitute: str = ""

@dataclass
class Preference:
    ingredient_id: int
    liked: bool = True
    frequency: int = 1  # times cooked
```

SQLite tablas: `ingredients`, `recipes`, `recipe_ingredients`, `preferences`, `pantry`. Seed con 200+ recetas iniciales.

**Commit:** `feat(recipealchemist): data models and DB`

---

## Task 3: Semilla de recetas iniciales

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/seed.py`
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/data/recipes.json`

JSON con 200+ recetas categorizadas: desayunos, almuerzos, cenas, snacks, postres. Cada una con ingredientes, pasos, tiempo, dificultad.

**Commit:** `feat(recipealchemist): seed recipe database`

---

## Task 4: Matching de ingredientes con fuzzy search

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/matcher.py`
- Create: `Midgard/RecipeAlchemist/tests/test_matcher.py`

```python
class IngredientMatcher:
    def match_recipes(self, available: list[str], pantry: list[str] = None) -> list[ScoredRecipe]:
        """Find recipes that best match available ingredients."""
        ...

    def ingredient_match_score(self, recipe_ingredients, available) -> float:
        """Score: how well available ingredients cover recipe needs."""
        ...

    def fuzzy_match(self, query: str, ingredients: list[Ingredient]) -> Ingredient:
        """Handle typos and variations: 'tomatos' → 'tomatoes'."""
        ...
```

Score = (matched_ingredients / total_ingredients) * (1 - missing_critical * 0.5). Fuzzy matching con thefuzz para tolerar typos.

**Commit:** `feat(recipealchemist): ingredient matching with fuzzy search`

---

## Task 5: CLI de búsqueda

**Files:**
- Modify: `Midgard/RecipeAlchemist/recipe_alchemist/cli.py`

```bash
recipe search "chicken rice tomato"          # busca por ingredientes
recipe search "chicken rice" --diet keto      # filtra por dieta
recipe search "eggs bacon" --diff easy        # solo fáciles
recipe search "pasta" --time 30               # menos de 30 min
recipe show 42                                # ver receta completa
```

Rich output con lista coloreada: ingredientes disponibles en verde, faltantes en rojo, opcionales en amarillo.

**Commit:** `feat(recipealchemist): search CLI`

---

## Task 6: Ajuste de porciones

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/scaler.py`

```python
class RecipeScaler:
    def scale(self, recipe: Recipe, target_servings: int) -> Recipe:
        """Scale recipe to target servings."""
        ...

    def convert_units(self, amount: float, from_unit: str, to_unit: str) -> float:
        """Convert between measurement units."""
        ...
```

Maneja fracciones (1/2 cup → 3/2 cup = 1.5 cup), unidades métricas/imperiales.

**Commit:** `feat(recipealchemist): recipe scaling`

---

## Task 7: Gestión de despensa (pantry)

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/pantry.py`

```bash
recipe pantry add "eggs" --amount 12 --unit piece
recipe pantry add "milk" --amount 1 --unit liter
recipe pantry list                    # mostrar inventario
recipe pantry remove "eggs" --amount 4
```

La despensa persistente en SQLite. Al buscar recetas, se cross-reference con pantry para marcar qué ya tienes.

**Commit:** `feat(recipealchemist): pantry management`

---

## Task 8: Lista de compras

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/shopping.py`

```bash
recipe shopping 42          # lista para receta #42
recipe shopping 42 43 45    # lista combinada para múltiples recetas
recipe shopping --week       # lista para el plan semanal
```

Genera lista agrupada por categoría (produce, dairy, meat...) con cantidades agregadas.

**Commit:** `feat(recipealchemist): shopping list generation`

---

## Task 9: Learning de preferencias

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/learner.py`

Cuando cocinas una receta (`recipe cook 42`), te pregunta: "¿Te gustó? (y/n/skip)". Almacena preferencias y boostea recetas similares en búsquedas futuras.

```python
class PreferenceLearner:
    def record(self, recipe_id: int, liked: bool) -> None:
        ...

    def boost_score(self, scored_recipes: list[ScoredRecipe]) -> list[ScoredRecipe]:
        """Boost recipes with ingredients the user likes."""
        ...
```

**Commit:** `feat(recipealchemist): preference learning`

---

## Task 10: Integración con API externa (opcional)

**Files:**
- Create: `Midgard/RecipeAlchemist/recipe_alchemist/api.py`

Spoonacular API como fuente adicional. Búsqueda por ingredientes, nutri info. Fallback a DB local si sin API key.

**Commit:** `feat(recipealchemist): Spoonacular API integration`

---

## Task 11: Tests + CI

**Commit:** `ci(recipealchemist): add test workflow`

---

## Resumen de Stack

| Componente | Tecnología |
|---|---|
| Storage | SQLite |
| Fuzzy matching | thefuzz + Levenshtein |
| CLI | Typer + Rich |
| Scaling | fractions (stdlib) |
| External API | Spoonacular (optional) |
| Data | Seed JSON (200+ recipes) |
