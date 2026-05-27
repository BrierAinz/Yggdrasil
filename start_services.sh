#!/bin/bash
# Script para iniciar los servicios de Yggdrasil
# Inicia: API Gateway, Model Orchestrator, Memory Service

echo "🚀 Iniciando servicios de Yggdrasil..."
echo "=============================================="

# Verificar si el entorno virtual está activado
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No se detecta entorno virtual activado"
    echo "Iniciando entorno virtual..."
    
    # Intentar activar uv venv
    if [ -f "./.venv/bin/activate" ]; then
        source "./.venv/bin/activate"
        echo "✅ Entorno virtual activado"
    elif [ -f "./venv/bin/activate" ]; then
        source "./venv/bin/activate"
        echo "✅ Entorno virtual activado"
    else
        echo "❌ No se encontró entorno virtual"
        echo "Por favor, ejecuta 'uv venv' para crear uno"
        exit 1
    fi
else
    echo "✅ Entorno virtual activado: $VIRTUAL_ENV"
fi

echo
echo "📦 Iniciando servicios en segundo plano..."

# Iniciar API Gateway
echo "🚀 API Gateway (port 8000)..."
cd /mnt/d/Proyectos/Yggdrasil/Asgard/lilith-api && uv run python run.py > /mnt/d/Proyectos/Yggdrasil/api_gateway.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"
echo "   Log: api_gateway.log"

# Esperar un momento para que el API Gateway inicie
sleep 2

# Iniciar Model Orchestrator
echo "🚀 Model Orchestrator (port 8001)..."
cd /mnt/d/Proyectos/Yggdrasil/Asgard/lilith-orchestrator && uv run python -m lilith_orchestrator > /mnt/d/Proyectos/Yggdrasil/model_orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
echo "   PID: $ORCHESTRATOR_PID"
echo "   Log: model_orchestrator.log"

# Iniciar Memory Service
echo "🚀 Memory Service (port 8002)..."
cd /mnt/d/Proyectos/Yggdrasil/Asgard/lilith-memory && uv run python -m lilith_memory > /mnt/d/Proyectos/Yggdrasil/memory_service.log 2>&1 &
MEMORY_PID=$!
echo "   PID: $MEMORY_PID"
echo "   Log: memory_service.log"

cd /mnt/d/Proyectos/Yggdrasil

echo
echo "=============================================="
echo "✅ Servicios iniciados correctamente!"
echo "=============================================="
echo
echo "📊 Estado de servicios:"
echo "   - API Gateway: http://localhost:8000"
echo "   - Model Orchestrator: http://localhost:8001"
echo "   - Memory Service: http://localhost:8002"
echo
echo "📋 Comandos útiles:"
echo "   Ver logs: tail -f api_gateway.log model_orchestrator.log memory_service.log"
echo "   Matar procesos: pkill -f \"python.*run.py|lilith_orchestrator|lilith_memory\""
echo
echo "🔍 Prueba la conectividad:"
echo "   curl http://localhost:8000/health"
echo "   curl http://localhost:8001/health"
echo "   curl http://localhost:8002/health"