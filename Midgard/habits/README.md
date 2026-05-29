# ᛭ Midgard Habits — Tracker de Hábitos Personal

> *Las runas iluminan el camino de tu disciplina en el reino de Midgard.*

CLI de hábitos personales con estética dark fantasy nórdica, parte del proyecto Yggdrasil.

---

## Instalación

```bash
# Dependencias
pip install rich

# Sin instalación adicional — usa SQLite estándar de Python
```

## Uso

```bash
# Crear un hábito
python3 midgard_habits.py add "Meditar" --freq diario --icon 🧘
python3 midgard_habits.py add "Gym" --freq semanal --icon 💪
python3 midgard_habits.py add "Correr" --freq 3/semana --icon 🏃

# Marcar hábito como completado
python3 midgard_habits.py check Meditar
python3 midgard_habits.py check Meditar --fecha 2025-05-01
python3 midgard_habits.py check 1 --fecha 2025-05-01

# Desmarcar hábito
python3 midgard_habits.py uncheck Meditar --fecha 2025-05-01

# Listar hábitos con progreso
python3 midgard_habits.py list
python3 midgard_habits.py list --all

# Ver racha de un hábito
python3 midgard_habits.py streak Meditar
python3 midgard_habits.py streak 1

# Estadísticas generales
python3 midgard_habits.py stats --semana
python3 midgard_habits.py stats --mes

# Archivar hábito
python3 midgard_habits.py archive Meditar
```

## Frecuencias Disponibles

| Frecuencia   | Descripción                        |
|--------------|-------------------------------------|
| `diario`     | Cada día (default)                  |
| `semanal`    | Una vez por semana                  |
| `N/semana`   | N veces por semana (1-7)            |

## Comandos

| Comando   | Descripción                            |
|-----------|----------------------------------------|
| `add`     | Crear un nuevo hábito                  |
| `check`   | Marcar hábito como completado          |
| `uncheck` | Desmarcar hábito                       |
| `list`    | Listar hábitos con progreso            |
| `streak`  | Mostrar racha actual y mejor racha     |
| `stats`   | Estadísticas generales                 |
| `archive` | Archivar hábito (enviar a Helheim)     |

## Estructura de Archivos

```
habits/
├── midgard_habits.py   # CLI principal (argparse + rich)
├── habits_db.py        # Capa de persistencia SQLite (singleton)
├── data/
│   └── habits.db       # Base de datos (auto-creada)
├── tests/
│   └── test_habits.py  # Tests (>20 casos)
└── README.md
```

## Tests

```bash
cd Midgard/habits
python3 -m pytest tests/ -v
```

## Estética Dark Fantasy

- Headers con símbolos rúnicos (᛭, ᚠ, ᛁ, ᛦ)
- Racha mostrada con símbolos rúnicos de fuego (ᚠ)
- Verde para hábitos completados ᚹ
- Amarillo para hábitos pendientes ᛁ
- Rojo para hábitos fallidos/archivados ᛦ
- Progreso visual con runas de los últimos 7 días
- Paneles y tablas con bordes estilísticos via Rich
- Archivar envía el hábito "al reino de Helheim"

---

*Midgard Habits — Donde la disciplina forja runas de fuego en el reino de los mortales.*