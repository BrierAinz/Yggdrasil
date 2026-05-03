# Lilith Launcher
# ===============
# Launcher en PowerShell para Lilith

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\Proyectos\Midgard"  # IMPORTANTE: Ejecutar desde aca!
$LilithDir = "$ProjectRoot\Lilith"

Write-Host ""
Write-Host "  [LILITH] Iniciando Asistente Personal..." -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "  [1/4] Verificando Python..." -ForegroundColor Gray
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "  [ERROR] Python no encontrado" -ForegroundColor Red
    Write-Host "         Instalar desde: https://python.org/downloads" -ForegroundColor Yellow
    Read-Host "  Presiona Enter para salir"
    exit 1
}
Write-Host "  [OK] Python $($pythonCmd.Version)" -ForegroundColor Green

# IR AL DIRECTORIO RAIZ (esto es clave!)
Write-Host "  [2/4] Configurando entorno..." -ForegroundColor Gray
Set-Location $ProjectRoot
Write-Host "  [OK] Working directory: $ProjectRoot" -ForegroundColor Green

# Crear carpetas necesarias en Lilith
@("$LilithDir\logs", "$LilithDir\screenshots", "$LilithDir\memory") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ | Out-Null }
}

# Instalar dependencias
Write-Host "  [3/4] Verificando dependencias..." -ForegroundColor Gray
$httpx = pip show httpx 2>$null
if (-not $httpx) {
    Write-Host "  [INFO] Instalando httpx..." -ForegroundColor Yellow
    pip install httpx
}
Write-Host "  [OK] Dependencias listas" -ForegroundColor Green

# Verificar LM Studio
Write-Host "  [4/4] Verificando LM Studio..." -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -Method GET -TimeoutSec 5
    Write-Host "  [OK] LM Studio API conectada" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] LM Studio no responde en puerto 1234" -ForegroundColor Yellow
    Write-Host "         Asegurate de tener el servidor Local Server activo" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  =======================================" -ForegroundColor Cyan
Write-Host "  Lilith esta lista! Escribe 'help' para" -ForegroundColor Cyan
Write-Host "  comandos o simplemente chatea!" -ForegroundColor Cyan
Write-Host "  =======================================" -ForegroundColor Cyan
Write-Host ""

# Ejecutar Lilith desde el directorio raiz
python "$LilithDir\main.py"

Write-Host ""
Write-Host "  [LILITH] Sesion terminada" -ForegroundColor Cyan
