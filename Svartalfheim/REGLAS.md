# ⚖️ REGLAS — Svartalfheim

Leyes de la forja oscura. Los enanos no toleran el desorden en sus talleres.

## 📜 Reglas del Reino

1. **Documentación y scripts, nada más.** Svartalfheim aloja conocimiento, planes, scripts de automatización y documentación. No es repositorio de aplicaciones ni modelos.
2. **Los scripts residen en `Scripts/`.** Todo script de Python u otro lenguaje interpretado vive bajo `Scripts/`. No se admiten scripts sueltos en la raíz sin carpeta own — salvo los archivos de instrucciones maestras existentes.
3. **Los planes siguen el formato `plan-NN-*.md`.** Todo plan de implementación se archiva en `plans/` con numeración secuencial. Sin excepciones.
4. **La wiki es sagrada.** ADRs, runbooks, features y templates viven en `wiki/`. Quien modifique un ADR debe justificar la decisión como los enanos justifican sus runas.
5. **Lilith_Docs es la fuente viva.** La documentación activa está en `Knowledge_Base/Lilith_Docs/`. `Lilith_Legacy/` es de solo consulta — no se modifica sin autorización del Arquitecto.
6. **Los archivos raíz son excepciones controladas.** `INSTANCIAS_BUILD_INSTRUCTIONS.md` y `ecosystem-research-findings.md` son los únicos archivos sueltos permitidos en la raíz. Nuevos archivos raíz requieren aprobación explícita.

## 📂 Directorios

| Directorio | Descripción |
|---|---|
| `Archives_Lilith_Monolith/docs/` | Archivos del monolito original de Lilith. Solo lectura. |
| `Docs/` | Documentación miscelánea del reino. |
| `Knowledge_Base/Lilith_Docs/` | Documentación activa y vigente de Lilith. Fuente primaria. |
| `Knowledge_Base/Lilith_Legacy/` | Conocimiento heredado del monolito. Solo consulta. |
| `Scripts/` | Scripts de Python: Muninn y otros artefactos de automatización. |
| `plans/` | Planes de implementación con formato `plan-NN-*.md`. |
| `wiki/` | ADRs, features, runbooks, templates. La biblioteca de runas. |

## 🔄 Triggers de Migración

| Si un artefacto… | Entonces muévelo a… |
|---|---|
| Es un script que evoluciona a aplicación completa | **Muspelheim** (si tiene infraestructura) o **Midgard** (si es herramienta mortal) |
| Es documentación de un modelo de IA | **Niflheim** (junto al modelo que documenta) |
| Es un plan ejecutado y archivado | **Helheim** (si está muerto) o `wiki/` (si su lección perdura como ADR) |
| Es legacy confirmado sin uso futuro | **Helheim** (comprimido como tar.gz) |

## 🚫 Prohibiciones

- ❌ Aplicaciones completas con su propio despliegue — Muspelheim o Midgard
- ❌ Modelos de IA y datasets — Niflheim
- ❌ Archivos binarios grandes (>10MB) — usar Git LFS o mover a Niflheim
- ❌ Proyectos abandonados — Helheim
- ❌ Más archivos sueltos en la raíz sin aprobación del Arquitecto

---

*Los enanos forjan en la oscuridad para que la luz del conocimiento nunca se apague. Pero incluso la forja tiene sus reglas.*
