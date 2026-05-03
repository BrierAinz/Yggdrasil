# ⚔️ Reglas de Muspelheim

> *"El fuego no negocia; consume y transforma. Igual debe ser tu código."*

---

## 🔥 Reglas del Reino

1. **AI-Influencer/** es el proyecto Eir, actualmente en **FASE 0** (v0.1.0). Solo se almacenan configuraciones de entrenamiento LoRA y datasets provisionales. No se ejecutan pipelines de inferencia aquí.

2. **AutoSub/** está marcado como **COMPLETE** (v0.1.0). Solo se aceptan correcciones de bugs críticos. No se añaden nuevas funcionalidades sin crear un issue previo.

3. **AutoMode/** contiene plantillas. Las plantillas nuevas deben seguir el esquema de nombres establecido y ser validadas antes del merge.

4. **ForgeMaster/** fue migrado desde Niflheim. Es una herramienta CLI de gestión de modelos LLM (Typer, Rich, SQLite). Pertenece a Muspelheim como todo código ejecutable. Su ubicación anterior en Niflheim violaba la regla de "solo recursos" de ese realm.

5. **Docs/** es la fuente de verdad de la documentación de Muspelheim. Toda guía técnica, runbook y README de proyectos reside aquí o enlaza aquí.

6. **Máximo 4 proyectos activos.** Muspelheim es una fragua, no un almacén. Si un proyecto entra, otro sale (hacia Midgard si está completo, hacia Helheim si se archiva).

---

## 📂 Directorios Actuales

| Directorio | Descripción |
|---|---|
| `AI-Influencer/` | Proyecto Eir — LoRA training, v0.1.0, FASE 0 |
| `AutoSub/` | Generador de subtítulos — v0.1.0, COMPLETO |
| `AutoMode/` | Plantillas y modos automáticos — en curso |
| `ForgeMaster/` | Gestión de modelos LLM, VRAM, disk — CLI tool |
| `Docs/` | Documentación del reino de Muspelheim |

---

## 🔄 Disparadores de Migración

- **AI-Influencer** → Cuando alcance FASE 1:
  - Integrar con `lilith-orchestrator` de Asgard para pipelines automáticos
  - Evaluar repositorio propio si el tamaño de modelos lo requiere

- **AutoSub** → Si se reactiva desarrollo:
  - Considerar graduación a Midgard como herramienta estable

- **ForgeMaster** → Cuando alcance v1.0 estable:
  - Considerar graduación a Midgard como herramienta de producción

---

## 🚫 Ítems Prohibidos

- ❌ Commitear modelos LoRA entrenados (`.safetensors`, `.bin` grandes) — usar git-lfs o almacenamiento externo
- ❌ Añadir funcionalidades a AutoSub sin issue aprobado — está COMPLETO
- ❌ Ejecutar entrenamientos directamente en este repositorio sin configuración de GPU adecuada
- ❌ Almacenar más de 4 proyectos activos simultáneamente

---

*Las runas fueron talladas el 2026-05-02*
