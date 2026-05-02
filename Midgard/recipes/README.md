# 📜 Midgard Recipes — Grimorio de Recetas

> *Un gestor de recetas forjado en las fraguas de los enanos de Svartalfheim, donde cada plato cuenta una saga y cada ingrediente tiene su runa.*

## ⚔️ Visión General

Midgard Recipes es un CLI de gestión de recetas con estética dark fantasy nórdica. Almacena recetas en SQLite, permite planificar comidas semanales y generar listas de compras automáticamente.

## 🌳 Estructura

```
recipes/
├── midgard_recipes.py    # CLI principal (argparse + rich)
├── recipes_db.py         # Backend SQLite (CRUD + search)
├── tests/
│   └── test_recipes.py   # Suite de tests (>20 tests)
├── recipes.db            # Base de datos (auto-creada)
└── README.md
```

## 🗡️ Instalación

```bash
pip3 install rich
```

## ⚡ Uso

### Agregar receta (interactivo)
```bash
python3 midgard_recipes.py add "Estofado de Dragón" --time 60 --difficulty dificil --tags carne,fuego --servings 4
```

### Agregar con ingredientes y pasos inline
```bash
python3 midgard_recipes.py add "Pan Rúnico" --time 45 --difficulty facil \
  --ingredient "3 tazas harina" \
  --ingredient "1 taza agua" \
  --ingredient "2 cucharadas manteca" \
  --step "Mezclar harina y agua" \
  --step "Amasar 10 minutos" \
  --step "Hornear a 180°C por 45 min"
```

### Listar recetas
```bash
python3 midgard_recipes.py list
python3 midgard_recipes.py list --tag carne --difficulty dificil --time-max 30
```

### Ver receta completa (formato pergamino)
```bash
python3 midgard_recipes.py show "Estofado de Dragón"
python3 midgard_recipes.py show 1
```

### Buscar recetas
```bash
python3 midgard_recipes.py search dragón
python3 midgard_recipes.py search harina
```

### Editar receta
```bash
python3 midgard_recipes.py edit 1 --name "NuevoNombre" --time 50 --difficulty medio
python3 midgard_recipes.py edit "Pan Rúnico" --tags pan,horno,rapido
```

### Eliminar receta
```bash
python3 midgard_recipes.py delete "Estofado de Dragón"
python3 midgard_recipes.py delete 3
```

### Plan de comidas semanal
```bash
python3 midgard_recipes.py plan --days 7
```

### Lista de compras
```bash
python3 midgard_recipes.py shopping --days 7
```

### Exportar receta
```bash
python3 midgard_recipes.py export 1 --format md
python3 midgard_recipes.py export "Pan Rúnico" --format json
```

## 🔮 Modelos de Datos

### recipes
| Campo      | Tipo   | Descripción                     |
|------------|--------|---------------------------------|
| id         | INT    | Identificador único             |
| name       | TEXT   | Nombre de la receta (único)     |
| cook_time  | INT    | Tiempo de cocción en minutos    |
| difficulty | TEXT   | facil / medio / dificil         |
| servings   | INT    | Porciones                       |
| tags       | TEXT   | Tags separados por coma         |
| created    | TEXT   | Timestamp de creación           |

### ingredients
| Campo     | Tipo | Descripción                    |
|-----------|------|--------------------------------|
| id        | INT  | Identificador único            |
| recipe_id | INT | FK → recipes.id                |
| amount    | TEXT | Cantidad (ej: "2", "1/2")     |
| unit      | TEXT | Unidad (ej: "tazas", "g")      |
| name      | TEXT | Nombre del ingrediente          |

### instructions
| Campo     | Tipo | Descripción             |
|-----------|------|------------------------|
| id        | INT  | Identificador único     |
| recipe_id | INT  | FK → recipes.id         |
| step_num  | INT  | Número de paso           |
| text      | TEXT | Descripción del paso     |

### meal_plans
| Campo     | Tipo | Descripción                        |
|-----------|------|------------------------------------|
| id        | INT  | Identificador único                |
| day       | INT  | Día del plan (1-N)                 |
| recipe_id | INT  | FK → recipes.id                    |
| slot      | TEXT | desayuno / comida / cena           |

## 🪵 Estética Dark Fantasy

- **Pergaminos**: Las recetas se muestran como pergaminos con bordes rúnicos
- **Fuego** 🔥: El tiempo de cocción se indica con iconos de fuego
- **Runas**: Dificultad con runas nórdicas (ᚱ fácil, ᛏᛏ medio, ᛏᛏᛏ difícil)
- **Rich**: Formateado con colores y paneles estilo grimorio

## 🧪 Tests

```bash
python3 -m pytest tests/test_recipes.py -v
```

> *Tests > 20 cubriendo CRUD, búsqueda, filtrado, plan de comidas, lista de compras y CLI parsing.*

## 🌲 Yggdrasil

Este módulo es parte del proyecto **Yggdrasil** — un ecosistema de herramientas con temática de mitología nórdica. Midgard es el reino de las aplicaciones personales.

---

*Construido con fuego de Muspelheim y sabiduría de Odín.*