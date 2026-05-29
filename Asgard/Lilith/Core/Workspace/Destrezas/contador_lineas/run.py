"""
Skill: contador_lineas
Cuenta las lineas de codigo Python en un directorio y genera un resumen
Auto-generada por Lilith el 2026-03-03 19:20.
"""
import os
import sys
import time

skill_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(os.path.dirname(skill_dir))
project_root = os.path.dirname(workspace_root)
sys.path.insert(0, project_root)

secrets_path = os.path.join(project_root, "Config", "secrets.env")
if os.path.exists(secrets_path):
    with open(secrets_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def ejecutar(directorio: str = ".", incluir_subdirectorios: bool = False) -> str:
    import glob
    import os

    try:
        workspace_root = os.getcwd()
        output_dir = os.path.join(workspace_root, "Taller")
        os.makedirs(output_dir, exist_ok=True)

        total_lineas = 0
        archivos_analizados = 0
        resultados = {}

        if incluir_subdirectorios:
            patron = os.path.join(directorio, "**", "*.py")
            archivos_python = glob.glob(patron, recursive=True)
        else:
            archivos_python = glob.glob(os.path.join(directorio, "*.py"))

        for archivo in archivos_python:
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    lineas = len(f.readlines())
                    total_lineas += lineas
                    archivos_analizados += 1
                    resultados[archivo] = lineas
            except Exception as e:
                resultados[archivo] = f"ERROR: {str(e)}"

        resumen = f"Se analizaron {archivos_analizados} archivos Python.\n"
        resumen += f"Total de lÃ­neas de cÃ³digo: {total_lineas}.\n"
        resumen += "Detalles por archivo:\n"
        for archivo, lineas in resultados.items():
            resumen += f"- {archivo}: {lineas}\n"

        output_file = os.path.join(output_dir, "conteo_lineas.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(resumen)

        return (
            f"SUCCESS: Conteo de lÃ­neas completado. Resumen guardado en {output_file}"
        )

    except Exception as e:
        return f"ERROR: {str(e)}"


if __name__ == "__main__":
    print(ejecutar())
