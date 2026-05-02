# ᛭ Midgard Finanzas — Tracker de Finanzas Personales

> *Las runas iluminan el camino de tus riquezas en el reino de Midgard.*

CLI de finanzas personales con estética dark fantasy nórdica, parte del proyecto Yggdrasil.

---

## Instalación

```bash
# Dependencias
pip install rich

# Sin instalación adicional — usa SQLite estándar de Python
```

## Uso

```bash
# Agregar un gasto
python3 midgard_finanzas.py add 150 comida --desc "Almuerzo en Valhalla" --fecha 2025-05-01

# Agregar un ingreso
python3 midgard_finanzas.py income 5000 ahorro --desc "Salario mensual"

# Ver balance del mes
python3 midgard_finanzas.py balance --mes 2025-05

# Reporte por categoría
python3 midgard_finanzas.py report --mes 2025-05 --format table
python3 midgard_finanzas.py report --mes 2025-05 --format csv

# Presupuestos
python3 midgard_finanzas.py budget set comida 3000
python3 midgard_finanzas.py budget check --mes 2025-05

# Exportar datos
python3 midgard_finanzas.py export --mes 2025-05 --format json
python3 midgard_finanzas.py export --mes 2025-05 --format csv
```

## Categorías Predefinidas

| Categoría      | Descripción              |
|----------------|--------------------------|
| `comida`       | Alimentación             |
| `transporte`   | Movilidad y transporte   |
| `vivienda`     | Renta, servicios, hogar  |
| `entretenimiento` | Ocio y diversión      |
| `salud`        | Médico, farmacia         |
| `educacion`    | Cursos, libros           |
| `ahorro`       | Ahorro e inversiones     |
| `otros`        | Lo que no encaja abajo   |

> Se pueden usar categorías libres, pero las predefinidas tienen color mnemónico.

## Estructura de Archivos

```
finanzas/
├── midgard_finanzas.py   # CLI principal (argparse + rich)
├── finanzas_db.py        # Capa de persistencia SQLite (singleton)
├── data/
│   └── finanzas.db       # Base de datos (auto-creada)
├── tests/
│   └── test_finanzas.py  # Tests (>20 casos)
└── README.md
```

## Tests

```bash
cd Midgard/finanzas
python3 -m pytest tests/ -v
```

## Estética Dark Fantasy

- Headers con símbolos rúnicos (᛭, ᛉ)
- Verde para ingresos ⬆
- Rojo para gastos ⬇
- Ámbar/Yellow para warnings ⚠
- Paneles y tablas con bordes estilísticos via Rich

---

*Midgard Finanzas — Donde cada moneda cuenta en el reino de los mortales.*