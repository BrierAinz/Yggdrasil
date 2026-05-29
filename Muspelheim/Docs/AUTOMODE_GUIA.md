# Auto-Mode - Guía de Uso

> **Versión:** 1.0
> **Fecha:** 2026-03-21
> **Ubicación:** `Muspelheim/`

---

## ¿Qué es Auto-Mode?

**Auto-Mode** es el sistema de ejecución autónoma de Lilith. Permite ejecutar tareas complejas sin supervisión constante.

## Comandos Discord

```
/automode "objetivo" checkpoint_cada:5 reportar_cada:4
/automode_status [task_id]
/automode_control task_id accion:pausar|reanudar|detener|aprobar
```

## Arquitectura

- **DelegationDetector:** Decide auto-delegación
- **CheckpointManager:** Guarda estado cada N pasos
- **ProgressReporter:** Reportes automáticos
- **AutoExecutor:** Motor de ejecución

## Seguridad

Archivos protegidos, operaciones prohibidas, requiere aprobación.

---

*Auto-Mode en Muspelheim*
