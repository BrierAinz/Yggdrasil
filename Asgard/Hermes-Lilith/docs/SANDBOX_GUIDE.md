# Windows Sandbox - Recomendaciones de Uso

## ¿Qué es Windows Sandbox?

Windows Sandbox es un entorno Windows aislado y ligero que permite ejecutar aplicaciones en un entorno seguro y efímero. Se crea una máquina virtual limpia que se elimina al cerrar.

## ¿Es Recomendable Usar Sandbox?

### ✅ **SÍ, Recomendable Para:**

| Escenario | Beneficio |
|-----------|-----------|
| **Desarrollo y pruebas** | Aislar cambios que podrían afectar el sistema host |
| **Tareas de código no verificado** | Ejecutar scripts sin riesgo para el sistema principal |
| **Evaluación de nueva IA** | Probar capacidades en entorno seguro |
| **Tareas destructivas potenciales** | Proteger archivos importantes de borrado accidental |

### ⚠️ **NO Recomendable Para:**

| Escenario | Problema |
|-----------|-----------|
| **Uso diario productivo** | Rendimiento reducido (~20-30% más lento) |
| **Acceso a archivos frecuentes** | Necesidad de copiar archivos entre host/sandbox |
| **Tareas en tiempo real** | Latencia adicional |
| **Integración con hardware** | Limitado acceso a periféricos |

## Análisis: Sandbox vs Sistema Principal

### Comparación

| Aspecto | Sandbox | Sistema Principal |
|---------|---------|-------------------|
| **Seguridad** | ✅ Máxima | ⚠️ Variable |
| **Rendimiento** | ⚠️ ~70-80% | ✅ 100% |
| **Persistencia** | ❌ Efímero | ✅ Permanente |
| **Configuración** | ❌ Requiere setup | ✅ Listo |
| **Integración** | ⚠️ Limitada | ✅ Completa |
| **Costo recurso** | ⚠️ Alto | ✅ Eficiente |

### Recomendación por Tipo de Tarea

```yaml
tareas_sandbox:
  - tipo: "Desarrollo de nuevas features"
    usar_sandbox: false  # Productividad > seguridad

  - tipo: "Testing de scripts desconocidos"
    usar_sandbox: true   # Seguridad primero

  - tipo: "Operaciones de archivo destructivas"
    usar_sandbox: true   # Proteger datos importantes

  - tipo: "Tareas de coding simples"
    usar_sandbox: false  # VS Code directo es más rápido

  - tipo: "Experimentos con nueva IA"
    usar_sandbox: true   # Evaluar primero en aislado
```

## Implementación Recomendada

### Estrategia Híbrida

```
┌─────────────────────────────────────────────────────────┐
│                    SISTEMA PRINCIPAL                     │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  Zona Confiable  │  │  Zona Riesgo    │               │
│  │  - Coding normal │  │  - Scripts nuevos│              │
│  │  - Documentación │  │  - Testing        │              │
│  │  - VS Code       │  │  - Experimentos   │              │
│  └─────────────────┘  └─────────────────┘               │
│           ↓                       ↓                      │
│           ↓                       ↓                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │              SANDBOX (cuando sea necesario)      │    │
│  │  - Scripts no verificados                          │    │
│  │  - Testing destructivo                             │    │
│  │  - Evaluación de nueva IA                         │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Configuración en config.yaml

```yaml
sandbox:
  enabled: true

  # Política de uso
  policy:
    auto_use_for:
      - "scripts without verification"
      - "file deletion operations"
      - "disk formatting"
      - "registry modifications"
      - "unknown executables"

    never_use:
      - "simple coding tasks"
      - "documentation"
      - "file reading"

  # Paths compartidos (copia manual)
  shared_paths:
    - "D:\\Proyectos\\Midgard\\workspace"
    - "D:\\Proyectos\\Midgard\\skills"

  # Bloqueo de comandos peligrosos
  blocked_commands:
    - "rm -rf /"
    - "rm -rf C:\\"
    - "format"
    - "diskpart"
    - "del /f /s /q C:\\"
```

## Cómo Activar Windows Sandbox

### Prerrequisitos
- Windows 10/11 Pro, Enterprise o Education
- CPU con virtualización (VT-x/AMD-V)
- Mínimo 4GB RAM disponible
- 1GB espacio en disco

### Pasos de Activación

```powershell
# 1. Verificar requisitos
systeminfo

# 2. Habilitar virtualización en BIOS/UEFI

# 3. Abrir PowerShell como Admin
Enable-WindowsOptionalFeature -Online -FeatureName Containers
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

# 4. Verificar que sandbox está disponible
Get-WindowsOptionalFeature -Online -FeatureName Sandbox

# 5. Si está deshabilitado, habilitar:
Enable-WindowsOptionalFeature -Online -FeatureName Sandbox -All
```

### Alternativa: Hyper-V Aislado

Si no tienes Windows Sandbox disponible:

```powershell
# Crear VM con Hyper-V
New-VM -Name "Midgard-Sandbox" -MemoryStartupBytes 4GB -SwitchName "Default Switch"
Set-VMMemory -VMName "Midgard-Sandbox" -DynamicMemoryEnabled $true
```

## Recomendación Final

### Configuración Óptima para Midgard Agent

```yaml
# config.yaml - Sección recomendada
security:
  sandbox_mode: "adaptive"  # Usa sandbox automáticamente según política

  # Tasks que siempre van a sandbox
  sandbox_required:
    - "script_execution:unverified"
    - "file_operation:delete_multiple"
    - "system_change:registry"
    - "network:new_connection"

  # Tasks que nunca van a sandbox
  sandbox_excluded:
    - "coding:simple"
    - "documentation"
    - "file_read"
    - "memory_operations"
```

### Resumen de Recomendación

| Decisión | Razón |
|----------|-------|
| **Sistema Principal** para coding diario | Mejor rendimiento y productividad |
| **Sandbox** para testing/evaluación | Máxima seguridad |
| **Estrategia híbrida** como default | Balance óptimo |

---

**Documento**: Guía de Sandbox para Midgard Agent
**Fecha**: 2026-04-20
**Versión**: 1.0.0
