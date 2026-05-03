# ⚔️ Reglas de Alfheim

> *"La luz eterna no tolera sombras en el código."*

---

## 🌿 Reglas del Reino

1. **dashboard/** es la interfaz web principal y estable (v1.0.0). Toda modificación debe pasar por revisión — es el Bifröst que conecta a los mortales con la inteligencia.

2. **TerminalDashboard/** está en fase experimental (v0.1.0). Se permiten iteraciones rápidas, pero no debe absorber responsabilidades que corresponden a `dashboard/`.

3. **VSCode_Extension_Lilith/** debe mantenerse compatible con la versión más reciente de VSCode. La extensión es el puente entre el editor y el agente.

4. **ui-seed/** es un prototipo experimental (Electron + React). No se mergea a producción sin aprobación explícita.

5. Las dependencias de frontend deben estar lockeadas. Los dioses no perdonan los `package-lock.json` corruptos.

---

## 📂 Directorios Actuales

| Directorio | Descripción |
|---|---|
| `TerminalDashboard/` | TUI Python Textual — v0.1.0, fase de desarrollo |
| `VSCode_Extension_Lilith/` | Extensión VSCode en TypeScript — en desarrollo |
| `dashboard/` | Webapp HTMX+Alpine.js+Jinja2 — v1.0.0, estable |
| `ui-seed/` | Prototipo Electron+React — experimental |

---

## 🔄 Disparadores de Migración

- Si `ui-seed/` alcanza viabilidad para producción → migrar a repositorio propio con nombre definitivo
- Si `TerminalDashboard/` supera v0.5.0 → evaluar integración con `lilith-api` de Asgard
- Si `dashboard/` requiere SPA completa → considerar bifurcación antes de reescribir

---

## 🚫 Ítems Prohibidos

- ❌ Deploys sin lock de dependencias
- ❌ Mezclar lógica de negocio de Lilith dentro de extensiones de UI
- ❌ Commitear `node_modules/` o `__pycache__/`
- ❌ Prototipos en ramas `main` sin revisión

---

*Las runas fueron talladas el 2026-05-02*
