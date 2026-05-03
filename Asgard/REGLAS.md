# ⚔️ Reglas de Asgard

> *"Las leyes del trono no se rompen; se graban en runas de fuego."*

---

## 🏛️ Reglas del Reino

1. **Hermes-Lilith/** es un **nombre de directorio legado** heredado del repositorio git original. **NO debe renombrarse** bajo ninguna circunstancia. El history de git depende de este nombre. El agente se llama **Lilith** — el prefijo "Hermes" es vestigio muerto.

2. Los paquetes `lilith-*` son los pilares de la arquitectura moderna:
   - `lilith-core/` — Motor central (v2.0.0)
   - `lilith-api/` — API REST (v2.2.0)
   - `lilith-cli/` — Interfaz CLI (v2.1.0)
   - `lilith-memory/` — Memoria persistente (v1.0.0)
   - `lilith-orchestrator/` — Orquestación de tareas (v1.0.0)
   - `lilith-tools/` — Utilidades (v1.0.0)

3. **Dashboards/web/** está deprecado. No se añaden funcionalidades. Solo correcciones críticas de seguridad si fuese necesario.

4. El archivo `Lilith_backup_pre_refactor_20260403_145209.tar.gz` (~4.4 GB) debe estar incluido en `.gitignore`. Su peso corrompería el repositorio y la paciencia de los dioses.

5. `Lilith_Launcher.bat` es un script auxiliar para entornos Windows. No forma parte del build.

---

## 📂 Directorios Actuales

| Directorio | Descripción |
|---|---|
| `Dashboards/web/` | Panel React — ☠️ DEPRECADO |
| `Hermes-Lilith/` | Monolito legado v4.0 — NO RENOMBRAR |
| `Lilith/` | Núcleo refactorizado v5 del agente Lilith |
| `lilith-api/` | API REST v2.2.0 |
| `lilith-cli/` | CLI v2.1.0 |
| `lilith-core/` | Motor central v2.0.0 |
| `lilith-memory/` | Memoria v1.0.0 |
| `lilith-orchestrator/` | Orquestador v1.0.0 |
| `lilith-tools/` | Herramientas v1.0.0 |

---

## 🔄 Disparadores de Migración

- Si `Hermes-Lilith/` alcanza **0 referencias activas** en producción → considerar archival definitivo
- Si `Dashboards/web/` presenta vulnerabilidades → eliminar rama de despliegue
- Los paquetes `lilith-*` siguen versionado semántico estricto

---

## 🚫 Ítems Prohibidos

- ❌ Renombrar `Hermes-Lilith/` — rompería el history de git
- ❌ Commitear `*.tar.gz` de backup — están gitignored
- ❌ Añadir features a `Dashboards/web/` — está muerto
- ❌ Ejecutar `Lilith_Launcher.bat` sin entorno Windows configurado

---

*Las runas fueron talladas el 2026-05-02*
