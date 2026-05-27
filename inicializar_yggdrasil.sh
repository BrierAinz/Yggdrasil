#!/bin/bash
# Script de inicialización de Yggdrasil para la primera sesión

set -e

echo "⚔ Inicializando Yggdrasil... ⚔"

# Verificar que uv este disponible
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv (uvicorn) no está instalado. Por favor, instálalo con: npm install -g uv"
    exit 1
fi

# Verificar el directorio de Yggdrasil
YGGDRASIL_DIR="/mnt/d/Proyectos/Yggdrasil"
if [ ! -d "$YGGDRASIL_DIR" ]; then
    echo "❌ Error: Directorio de Yggdrasil no encontrado en $YGGDRASIL_DIR"
    exit 1
fi

# Crear enlaces simbólicos para acceso rápido
if [ ! -L "$HOME/.lilith" ]; then
    echo "📁 Creando enlace simbólico para Lilith..."
    ln -sf "$YGGDRASIL_DIR/Asgard/lilith-core" "$HOME/.lilith"
fi

# Verificar la configuración de .env
if [ ! -f "$YGGDRASIL_DIR/.env" ]; then
    echo "❌ Error: Archivo .env no encontrado en $YGGDRASIL_DIR"
    exit 1
fi

# Cargar variables de entorno
source "$YGGDRASIL_DIR/.env"

# Verificar la configuración de providers.yaml
if [ ! -f "$YGGDRASIL_DIR/Asgard/lilith-core/lilith_core/providers/providers.yaml" ]; then
    echo "❌ Error: Archivo providers.yaml no encontrado"
    exit 1
fi

# Crear directorio para la memoria de Lilith
LILITH_MEMORY_DIR="$YGGDRASIL_DIR/chat_memory"
mkdir -p "$LILITH_MEMORY_DIR"

# Verificar la base de datos de chat
if [ ! -f "$YGGDRASIL_DIR/chat_memory.db" ]; then
    echo "🗄️ Creando base de datos de chat..."
    touch "$YGGDRASIL_DIR/chat_memory.db"
fi

echo ""
echo "✅ Yggdrasil está listo para usar!"
echo ""
echo "📋 Comandos disponibles:"
echo "  - yggdrasil chat      # Chat interactivo con Lilith"
echo "  - yggdrasil status    # Ver estado del ecosistema"
echo "  - yggdrasil api       # Levantar la API de Lilith"
echo ""
echo "🌐 Para acceder a la terminal web: http://localhost:3000"
echo "🤖 Para acceder a la API de Lilith: http://localhost:8000"
echo ""
echo "⚔ ¡Bienvenido al mundo de Yggdrasil!"