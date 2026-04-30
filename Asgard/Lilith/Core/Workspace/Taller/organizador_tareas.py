"""
Script generado por Lilith (Gemini-2.0-flash)
Organizador de Tareas por Consola
Generado automaticamente durante la auditoria del 2026-03-02
"""
import json
import os

# Nombre del archivo JSON donde se guardaran las tareas
ARCHIVO_TAREAS = "tareas.json"


def cargar_tareas():
    """Carga las tareas desde el archivo JSON."""
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

    print("\n--- Lista de Tareas ---")
    for i, tarea in enumerate(tareas):
        estado = "[X]" if tarea["completada"] else "[ ]"
        print(f"{i+1}. {estado} {tarea['descripcion']}")
    print("-----------------------\n")


def marcar_completada(tareas, indice):
    """Marca una tarea como completada."""
    try:
        indice = int(indice) - 1
        if 0 <= indice < len(tareas):
            tareas[indice]["completada"] = True
            print(f"Tarea '{tareas[indice]['descripcion']}' marcada como completada.")
        else:
            print("Indice de tarea invalido.")
    except ValueError:
        print("Por favor, introduce un numero valido para el indice.")


def eliminar_tarea(tareas, indice):
    """Elimina una tarea de la lista."""
    try:
        indice = int(indice) - 1
        if 0 <= indice < len(tareas):
            descripcion = tareas[indice]["descripcion"]
            del tareas[indice]
            print(f"Tarea '{descripcion}' eliminada.")
        else:
            print("Indice de tarea invalido.")
    except ValueError:
        print("Por favor, introduce un numero valido para el indice.")


def mostrar_menu():
    """Muestra el menu de opciones."""
    print("\n--- Organizador de Tareas ---")
    print("1. Agregar tarea")
    print("2. Listar tareas")
    print("3. Marcar tarea como completada")
    print("4. Eliminar tarea")
    print("5. Salir")
    print("-----------------------------\n")


def main():
    """Funcion principal del programa."""
    tareas = cargar_tareas()

    while True:
        mostrar_menu()
        opcion = input("Selecciona una opcion: ")

        if opcion == "1":
            descripcion = input("Introduce la descripcion de la tarea: ")
            agregar_tarea(tareas, descripcion)
        elif opcion == "2":
            listar_tareas(tareas)
        elif opcion == "3":
            listar_tareas(tareas)
            indice = input("Introduce el numero de la tarea a marcar como completada: ")
            marcar_completada(tareas, indice)
        elif opcion == "4":
            listar_tareas(tareas)
            indice = input("Introduce el numero de la tarea a eliminar: ")
            eliminar_tarea(tareas, indice)
        elif opcion == "5":
            print("Saliendo del organizador de tareas. Hasta luego!")
            break
        else:
            print("Opcion invalida. Por favor, selecciona una opcion valida.")

        guardar_tareas(tareas)


if __name__ == "__main__":
    main()
