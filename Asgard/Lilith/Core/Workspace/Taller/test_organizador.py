"""Test automatizado del script generado por Lilith"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Importamos las funciones del organizador directamente
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import json

from organizador_tareas import (
    agregar_tarea,
    cargar_tareas,
    eliminar_tarea,
    guardar_tareas,
    listar_tareas,
    marcar_completada,
)

# Limpiamos cualquier archivo previo
if os.path.exists("tareas.json"):
    os.remove("tareas.json")

print("=== TEST DEL CODIGO DE Lilith ===\n")

tareas = []

# Test 1: Agregar tareas
print("[Test 1] Agregar tareas:")
agregar_tarea(tareas, "Comprar cafe")
agregar_tarea(tareas, "Estudiar Python")
agregar_tarea(tareas, "Dominar el mundo")
assert len(tareas) == 3, f"ERROR: Se esperaban 3 tareas, hay {len(tareas)}"
print("  PASS: 3 tareas agregadas\n")

# Test 2: Listar tareas
print("[Test 2] Listar tareas:")
listar_tareas(tareas)
print("  PASS: listado correcto\n")

# Test 3: Marcar completada
print("[Test 3] Marcar tarea como completada:")
marcar_completada(tareas, "1")
assert tareas[0]["completada"] == True, "ERROR: La tarea 1 deberia estar completada"
print("  PASS: tarea 1 marcada\n")

# Test 4: Eliminar tarea
print("[Test 4] Eliminar tarea:")
eliminar_tarea(tareas, "3")
assert len(tareas) == 2, f"ERROR: Se esperaban 2 tareas, hay {len(tareas)}"
print("  PASS: tarea eliminada, quedan 2\n")

# Test 5: Guardar y cargar JSON
print("[Test 5] Persistencia JSON:")
guardar_tareas(tareas)
tareas_cargadas = cargar_tareas()
assert len(tareas_cargadas) == 2, "ERROR: No se cargaron las tareas correctamente"
assert tareas_cargadas[0]["completada"] == True, "ERROR: El estado no se persiste"
print("  PASS: JSON guardado y cargado correctamente\n")

# Mostrar el JSON final
print("[JSON Final]:")
print(json.dumps(tareas_cargadas, indent=2, ensure_ascii=False))

# Limpiar
os.remove("tareas.json")

print("\n=== TODOS LOS TESTS PASARON ===")
