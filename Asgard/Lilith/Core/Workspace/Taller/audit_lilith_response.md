# Auditoria de Lilith

## Test 1: Idioma
Entendido, Ainz. A partir de ahora, todas mis comunicaciones serÃ¡n en espaÃ±ol. Â¿Algo mÃ¡s que necesites?


## Test 2: Generacion de Codigo
Â¡Entendido, Ainz! AquÃ­ tienes un script de Python para un organizador de tareas por consola, que guarda la informaciÃ³n en un archivo JSON. He aÃ±adido comentarios para que entiendas mejor cada parte del cÃ³digo.

```python
import json
import os

# Nombre del archivo JSON donde se guardarÃ¡n las tareas
ARCHIVO_TAREAS = "tareas.json"

def cargar_tareas():
    """Carga las tareas desde el archivo JSON si existe."""
    try:
        with open(ARCHIVO_TAREAS, "r") as f:
            tareas = json.load(f)
    except FileNotFoundError:
        tareas = []
    return tareas

def guardar_tareas(tareas):
    """Guarda las tareas en el archivo JSON."""
    with open(ARCHIVO_TAREAS, "w") as f:
        json.dump(tareas, f, indent=4)

def agregar_tarea(tareas, descripcion):
    """Agrega una nueva tarea a la lista."""
    tarea = {"descripcion": descripcion, "completada": False}
    tareas.append(tarea)
    print(f"Tarea '{descripcion}' agregada.")

def listar_tareas(tareas):
    """Lista todas las tareas con su estado."""
    if not tareas:
        print("No hay tareas pendientes.")
        return

    print("Lista de tareas:")
    for i, tarea in enumerate(tareas):
        estado = "[X]" if tarea["completada"] else "[ ]"
        print(f"{i+1}. {estado} {tarea['descripcion']}")

def marcar_completada(tareas, indice):
    """Marca una tarea como completada."""
    try:
        indice = int(indice) - 1
        if 0 <= indice < len(tareas):
            tareas[indice]["completada"] = True
            print(f"Tarea '{tareas[indice]['descripcion']}' marcada como completada.")
        else:
            print("Ãndice de tarea invÃ¡lido.")
    except ValueError:
        print("Por favor, introduce un nÃºmero vÃ¡lido.")

def eliminar_tarea(tareas, indice):
    """Elimina una tarea de la lista."""
    try:
        indice = int(indice) - 1
        if 0 <= indice < len(tareas):
            descripcion = tareas[indice]["descripcion"]
            del tareas[indice]
            print(f"Tarea '{descripcion}' eliminada.")
        else:
            print("Ãndice de tarea invÃ¡lido.")
    except ValueError:
        print("Por favor, introduce un nÃºmero vÃ¡lido.")

def mostrar_menu():
    """Muestra el menÃº de opciones."""
    print("\n--- Organizador de Tareas ---")
    print("1. Agregar tarea")
    print("2. Listar tareas")
    print("3. Marcar tarea como completada")
    print("4. Eliminar tarea")
    print("5. Salir")

def main():
    """FunciÃ³n principal del programa."""
    tareas = cargar_tareas()

    while True:
        mostrar_menu()
        opcion = input("Elige una opciÃ³n: ")

        if opcion == "1":
            descripcion = input("Introduce la descripciÃ³n de la tarea: ")
            agregar_tarea(tareas, descripcion)
        elif opcion == "2":
            listar_tareas(tareas)
        elif opcion == "3":
            listar_tareas(tareas)
            indice = input("Introduce el nÃºmero de la tarea a marcar como completada: ")
            marcar_completada(tareas, indice)
        elif opcion == "4":
            listar_tareas(tareas)
            indice = input("Introduce el nÃºmero de la tarea a eliminar: ")
            eliminar_tarea(tareas, indice)
        elif opcion == "5":
            print("Â¡Hasta luego!")
            break
        else:
            print("OpciÃ³n invÃ¡lida. Por favor, elige una opciÃ³n del menÃº.")

        guardar_tareas(tareas)

if __name__ == "__main__":
    main()
```

**Â¿CÃ³mo usarlo?**

1.  **Guarda el cÃ³digo:** Guarda el cÃ³digo como un archivo `.py` (por ejemplo, `organizador.py`).
2.  **Ejecuta el script:** Abre una terminal o lÃ­nea de comandos, navega al directorio donde guardaste el archivo y ejecuta `python organizador.py`.

El programa te mostrarÃ¡ un menÃº con opciones para agregar, listar, marcar como completadas y eliminar tareas. Los datos se guardan en un archivo JSON llamado `tareas.json` en el mismo directorio.

**Â¿QuÃ© te parece, Ainz? Â¿Necesitas alguna modificaciÃ³n o mejora?**
