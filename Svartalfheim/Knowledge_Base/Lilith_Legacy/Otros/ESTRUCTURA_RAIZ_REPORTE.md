# Reporte: ordenación de la raíz del proyecto Lilith

**Fecha:** 2026-03-15  
**Raíz escaneada:** `D:\Proyectos\Asgard\Lilith\`

---

## 1. Archivos sueltos que deberían estar en subcarpetas

| Archivo | Tipo | Propuesta |
|---------|------|-----------|
| **best_wide_resnet.pth** | Modelo PyTorch (pesado) | → **Models/** o **Artifacts/PyTorch/** (evitar raíz por tamaño y claridad). |
| **test_agents.py** | Script de prueba manual de agentes (Panteón) | → **Scripts/** (ej. `Scripts/test_agents.py`). |
| **test_session_summary.py** | Script de verificación (summarizer vía WS) | → **Scripts/** (ej. `Scripts/test_session_summary.py`). |
| **verify_procedural.py** | Script verificación Fase C (memoria procedural) | → **Scripts/** (ej. `Scripts/verify_procedural.py`). |
| **verify_semantic.py** | Script verificación memoria semántica | → **Scripts/** (ej. `Scripts/verify_semantic.py`). |
| **test_report.txt** | Salida generada por pytest (`pytest ... > test_report.txt`) | → **Eliminar** o **temp/**; añadir a `.gitignore` si se sigue generando. |

**Nota:** `start_server.py` es el launcher del servidor web; es razonable dejarlo en **raíz** (o en **Scripts/** si se unifican todos los launchers ahí).

---

## 2. Carpetas vacías o residuales

| Carpeta | Estado | Propuesta |
|---------|--------|-----------|
| **backups** | Vacía (0 archivos) | Eliminar o dejar documentada como "carpeta para backups manuales". Si no se usa → **eliminar**. |
| **.crush** | Carpeta de herramienta externa (Crush); contiene `logs/crush.log` | Residual. Valorar **eliminar** si no se usa Crush, o dejar y añadir a `.gitignore`. |
| **.pytest_cache** | Cache de pytest (se regenera) | No mover; opcional añadir a `.gitignore` si no está. |

**Resto de carpetas con contenido:** Artifacts (logs, PyTorch), data (cifar-10), docs (fases, .md), Config, memory, Scripts, Tools, temp (screenshots), etc. — no están vacías ni se proponen como residuales para borrar sin criterio.

---

## 3. Archivos .py de utilidad/scripts sueltos en raíz

| Script | Uso | Propuesta |
|--------|-----|-----------|
| **start_server.py** | Arranque del servidor API + frontend | **Raíz** (punto de entrada) o **Scripts/start_server.py** y enlazar desde `launch_lilith.bat`. |
| **test_agents.py** | Prueba manual de Eva/Adán/Lucifer/Router | → **Scripts/test_agents.py**. |
| **test_session_summary.py** | Dispara summarizer vía WebSocket + SIGINT | → **Scripts/test_session_summary.py**. |
| **verify_procedural.py** | Verificación Fase C (error_history) | → **Scripts/verify_procedural.py**. |
| **verify_semantic.py** | Verificación memoria semántica vía WS | → **Scripts/verify_semantic.py**. |

---

## 4. Archivos temporales / cache en raíz

| Elemento | Ubicación | Propuesta |
|----------|-----------|-----------|
| **test_report.txt** | Raíz | Temporal (salida de pytest). **Eliminar** o mover a **temp/**; **.gitignore**: `test_report.txt`. |
| **.pytest_cache/** | Raíz | Cache estándar; no mover. Incluir en **.gitignore** si hace falta. |
| **.crush/logs/** | .crush | Si se mantiene .crush, considerar **.gitignore** para `.crush/`. |

No se han encontrado en raíz: `*.tmp`, `*.log` (el único .log está en `.crush/logs/`), ni `__pycache__` en la raíz.

---

## 5. Estructura limpia propuesta

### 5.1 Scripts de arranque (raíz o raíz + Scripts)

- **launch_lilith.bat** → **Raíz** (entrada principal).
- **gauntlet.bat** → **Raíz** (llama a `Scripts/cifar10_wide_resnet_gauntlet.py`); OK en raíz.
- **start_server.py** → **Raíz** (entrada `python start_server.py`) **o** **Scripts/start_server.py** y que los .bat llamen a `python Scripts/start_server.py`.

### 5.2 Documentación

- **README.md** → **Raíz** (estándar).
- **MISION_LILITH_V2.3.md** → **Raíz** o **Docs/** (ej. `Docs/MISION_LILITH_V2.3.md`).
- **TESTS_SUMMARY.md** → **Raíz** o **Docs/** (ej. `Docs/TESTS_SUMMARY.md`).
- **docs/** (minúscula) → Ya existe con `fases/` y `fix_streaming_ws_ipc.md`. Valorar unificar en **Docs/** (mayúscula) para tener una sola carpeta de documentación.

### 5.3 Scripts de utilidad

- **Scripts/** (ya existe): mover aquí los scripts sueltos de la raíz:
  - `test_agents.py`
  - `test_session_summary.py`
  - `verify_procedural.py`
  - `verify_semantic.py`
- **Tools/** (ya existe): parece estructura paralela (core, ipc, memory, tests). No mezclar con los scripts de utilidad de **Scripts/** salvo que se decida unificar criterio.

### 5.4 Configuración

- **Config/** (ya existe): `secrets.env`, `settings.json` → **Mantener** en Config/.

### 5.5 Modelos y artefactos

- **best_wide_resnet.pth** → **Models/** o **Artifacts/PyTorch/** (no en raíz).
- **requirements.txt** → **Raíz** (estándar).

### 5.6 Temporales y cache

- **test_report.txt** → No versionar; **eliminar** o **temp/** y **.gitignore**.
- **temp/** → Mantener para temporales (ej. screenshots).
- **.pytest_cache**, **.crush** → No mover; gestionar vía .gitignore si procede.

---

## 6. Resumen de acciones propuestas (sin ejecutar)

| Acción | Elementos |
|--------|-----------|
| Mover a **Scripts/** | test_agents.py, test_session_summary.py, verify_procedural.py, verify_semantic.py |
| Mover a **Models/** o **Artifacts/PyTorch/** | best_wide_resnet.pth |
| Mover a **Docs/** (opcional) | MISION_LILITH_V2.3.md, TESTS_SUMMARY.md; unificar con docs/ |
| Eliminar o ignorar | test_report.txt; carpeta backups si se confirma vacía y no usada; .crush si no se usa |
| Dejar en raíz | README.md, requirements.txt, launch_lilith.bat, gauntlet.bat; start_server.py (o mover a Scripts y actualizar .bat) |
| No mover | .gitignore, .vscode, Config/, Tests/, Backend/, Frontend/, memory/, Workspace/, Alma/, Mente/, etc. |

**No se ha movido ni eliminado nada;** este documento solo reporta y propone.
