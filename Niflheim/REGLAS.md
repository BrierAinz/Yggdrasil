# ⚖️ REGLAS — Niflheim

Leyes del reino glacial. La niebla no perdona al que las rompe.

## 📜 Reglas del Reino

1. **NADA DE CÓDIGO EJECUTABLE.** Niflheim almacena datos, modelos y recursos estáticos. Cualquier código ejecutable —sea script, aplicación o servicio— será desterrado a Muspelheim. Sin excepciones.
2. **Los datasets se almacenan, no se procesan.** Los datos viven aquí en reposo. Si necesitas procesarlos, llévalos al reino del fuego.
3. **Los modelos sonAssets inmutables.** Una vez almacenados, los modelos no se modifican in situ. Se versionan o se reemplazan. El hielo no se reescribe — se forma de nuevo.
4. **ForgeMaster fue migrado a Muspelheim.** La violación ha sido resuelta. `scripts/model_manager.py` permanece como utilidad de infraestructura del realm (excepción documentada).
5. **Cada modelo en su subcarpeta bajo `Models/`.** No se dejan archivos sueltos en la raíz de `Models/`.
6. **Cada dataset en su subcarpeta bajo `Datasets/`.** Igual que los modelos, cada colección de datos tiene su propia morada helada.

## 📂 Directorios

| Directorio | Descripción |
|---|---|
| `Datasets/cifar-10-batches-py/` | Dataset CIFAR-10. Datos de entrenamiento congelados. |
| `ForgeMaster/` | ✅ **MIGRADO A MUSPELHEIM.** Ya no reside en Niflheim. Ver `Muspelheim/ForgeMaster/`. |
| `Models/Lilith_v5_models/` | Modelos preentrenados de Lilith v5. Los pensamientos congelados de la criatura. |
| `scripts/model_manager.py` | Utilidad de infraestructura del realm. Gestiona modelos localmente. Excepción documentada a la regla #1. |

## 🔄 Triggers de Migración

| Si un artefacto… | Entonces muévelo a… |
|---|---|
| Es código ejecutable (scripts, apps, herramientas CLI) | **Muspelheim** — el reino del fuego donde el código corre |
| Es un modelo que ya no se usa ni se entrenará | **Helheim** — archivo comprimido |
| Es documentación de un modelo o dataset | **Svartalfheim** — Knowledge Base o wiki |
| Es un dataset procesado que alimenta una app mortal | **Midgard** — solo si la app lo requiere directamente |

## 🚫 Prohibiciones

- ❌ **Código ejecutable** — Muspelheim. Esta es la regla suprema de Niflheim.
- ❌ Archivos de configuración de despliegue (Dockerfiles, CI/CD) — Muspelheim
- ❌ Notebooks de Jupyter o cualquier artefacto ejecutable — Muspelheim
- ❌ Proyectos abandonados de models/datasets — Helheim (comprimidos)
- ❌ Modificar modelos in situ — versionar o reemplazar

---

*El hielo es paciente. El hielo es silencioso. Pero el hielo no ejecuta código. Ese es el fuego de Muspelheim.*
