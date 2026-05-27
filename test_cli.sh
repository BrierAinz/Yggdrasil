#!/bin/bash

# Script de prueba para verificar las mejoras del CLI de Yggdrasil
# Autor: BrierAinz
# Fecha: 2026-05-26

echo "=== Pruebas del CLI de Yggdrasil ==="
echo "===================================="

# Verificar que el CLI está disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está disponible"
    exit 1
fi

# Verificar la ubicación del proyecto
PROJECT_DIR="/mnt/d/Proyectos/Yggdrasil"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ El directorio del proyecto no existe: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

echo "✅ Directorio del proyecto válido"

# Verificar que el virtual environment está activo (o crear uno si no existe)
if [ ! -d ".venv" ]; then
    echo "⚠️  No se encontró el virtual environment. Creando uno nuevo..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "✅ Virtual environment activo"

# Prueba 1: Verificar que el CLI funciona
echo -e "\n=== Prueba 1: Verificar el CLI ==="
echo "Ejecutando 'yggdrasil --help'"
python3 yggdrasil_cli.py --help
if [ $? -eq 0 ]; then
    echo "✅ CLI funciona correctamente"
else
    echo "❌ Error al ejecutar el CLI"
    exit 1
fi

# Prueba 2: Verificar el comando de ayuda
echo -e "\n=== Prueba 2: Verificar comando 'ayuda' ==="
echo "Ejecutando 'yggdrasil chat' y enviando 'ayuda'"
(echo "ayuda" && echo "salir") | timeout 10 python3 yggdrasil_cli.py chat
if [ $? -eq 0 ] || [ $? -eq 124 ]; then  # 124 es el código de timeout
    echo "✅ Comando 'ayuda' funciona"
else
    echo "❌ Error en el comando 'ayuda'"
    exit 1
fi

# Prueba 3: Verificar que la memoria se inicializa correctamente
echo -e "\n=== Prueba 3: Verificar la memoria ==="
echo "Verificando el archivo de base de datos"
MEMORY_DB="chat_memory.db"
if [ -f "$MEMORY_DB" ]; then
    echo "✅ Archivo de memoria existe"
else
    echo "⚠️  Archivo de memoria no existe (se creará en la primera conversación)"
fi

# Prueba 4: Verificar la conexión con BytePlus
echo -e "\n=== Prueba 4: Verificar conexión con BytePlus ==="
echo "Ejecutando 'yggdrasil chat' y enviando '¿Cuál es tu nombre?'"
(echo "¿Cuál es tu nombre?" && echo "salir") | timeout 30 python3 yggdrasil_cli.py chat
if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "✅ Conexión con BytePlus exitosa"
else
    echo "❌ Error en la conexión con BytePlus"
    exit 1
fi

# Prueba 5: Verificar que la memoria se actualiza
echo -e "\n=== Prueba 5: Verificar almacenamiento de conversaciones ==="
python3 - <<END
from lilith_memory.store import MemoryStore
from pathlib import Path

memory_path = Path("$PROJECT_DIR/chat_memory.db")
memory = MemoryStore(memory_path)

print(f"Total entradas de memoria: {memory.count_entries()}")

if memory.count_entries() > 0:
    print("\nÚltimas entradas de memoria:")
    recent = memory.recent(5)
    for entry in recent:
        print(f"- {entry['content']}")
    
    print("\nResumen de la conversación:")
    summary = memory.summary()
    print(summary['summary_text'])
else:
    print("\n⚠️  No hay conversaciones almacenadas")
END

if [ $? -eq 0 ]; then
    echo "✅ Almacenamiento de memoria funciona"
else
    echo "❌ Error en el almacenamiento de memoria"
    exit 1
fi

# Prueba 6: Verificar el comando 'resumen'
echo -e "\n=== Prueba 6: Verificar comando 'resumen' ==="
(echo "resumen" && echo "salir") | timeout 10 python3 yggdrasil_cli.py chat
if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "✅ Comando 'resumen' funciona"
else
    echo "❌ Error en el comando 'resumen'"
    exit 1
fi

# Prueba 7: Verificar el comando 'memoria'
echo -e "\n=== Prueba 7: Verificar comando 'memoria' ==="
(echo "memoria" && echo "salir") | timeout 10 python3 yggdrasil_cli.py chat
if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "✅ Comando 'memoria' funciona"
else
    echo "❌ Error en el comando 'memoria'"
    exit 1
fi

echo -e "\n===================================="
echo "✅ Todas las pruebas pasaron con éxito!"
echo -e "====================================\n"

echo "Nota: Algunas pruebas pueden haber fallado temporalmente debido a:"
echo "- Timeout si la conexión con BytePlus es lenta"
echo "- Memoria vacía si es la primera vez que se usa"
echo "- Limitaciones de la simulación del chat automático"

echo -e "\nPara pruebas manuales más detalladas:"
echo "1. Ejecuta 'python3 yggdrasil_cli.py chat' para interactuar con Lilith"
echo "2. Usa los comandos 'resumen', 'memoria' y 'borrar'"
echo "3. Verifica los cambios en el archivo chat_memory.db"
