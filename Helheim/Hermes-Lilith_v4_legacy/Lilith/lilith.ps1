# Lilith - PowerShell Launcher
# ============================
# Usar: .\lilith.ps1
# O con alias: Set-Alias lilith "D:\Proyectos\Yggdrasil\Asgard\Hermes-Lilith\Lilith\lilith.ps1"

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

# UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Verificar Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[ERROR] Python no encontrado" -ForegroundColor Red
    exit 1
}

# Ejecutar
Set-Location $projectRoot
& python "$scriptDir\main.py" @args
