# Historia de construcción — Lilith (inicio → estado actual)

Este documento reconstruye **la construcción de Lilith de inicio a fin** usando como “fuentes primarias” los archivos de `Core/Docs/` y `Discord/Docs/`.  
Para el orden exacto por antigüedad, ver `Core/Docs/CRONOLOGIA_DOCS_LILITH.md`.

---

## 0) Idea base y norte del sistema

Lilith se construye como un **asistente-orquestador**: recibe una intención humana (DM/Discord y luego Telegram para PC), la convierte en un plan, ejecuta herramientas/agentes y consolida memoria para mejorar desempeño futuro.

En el camino se fue endureciendo un principio:

- **Separación de capacidades por canal/rol** (owner/trusted/public).
- **Defensa contra inyección y fuga de secretos**.
- **Ejecución auditable** (logs, episodios, confirmaciones).

Documentos guía:

- `Core/Docs/ESTRUCTURA_PROYECTO.md`
- `Core/Docs/ROADMAP_HACIA_4.0.md`
- `Core/Docs/MISION_LILITH_4.0.md`

---

## 1) Primeras bases y estabilización (V2.3 → V3.0)

### 1.1 Evidencia de arranque: pruebas, reporte raíz e IPC/streaming

Esta etapa concentra “hacer que corra” y que los cimientos no fallen: pruebas básicas, estructura inicial y correcciones de streaming/IPC.

- `Core/Docs/TESTS_SUMMARY.md`
- `Core/Docs/ESTRUCTURA_RAIZ_REPORTE.md`
- `Core/Docs/fix_streaming_ws_ipc.md`
- `Core/Docs/MISION_LILITH_V2.3.md`

### 1.2 Consolidación hacia V3: misión completa y refinamientos

Aquí aparece el enfoque de “misiones” como forma de dirigir implementaciones grandes y cerrar por checklists.

- `Core/Docs/MISION_LILITH_3.0_COMPLETO.md`
- `Core/Docs/MISION_LILITH_V3.0.md`
- `Core/Docs/MISION_LILITH_3.2_REFINAMIENTO.md`
- `Core/Docs/MISION_LILITH_3.3_OPTIMIZACION.md`
- `Core/Docs/MISION_LILITH_3.4.md`
- `Core/Docs/MISION_LILITH_3.5.md`
- `Core/Docs/ESTRUCTURA_PROYECTO.md`

---

## 2) Seguridad y gobernanza (roles, límites, prompt injection)

Con el crecimiento del orquestador y los canales, se formaliza:

- Roles **owner/trusted/public**.
- Capacidades por rol y gating.
- Defensa contra prompt injection (capas, validaciones, “no inventar”, etc.).

Documentos:

- `Core/Docs/ROLES_Y_PERMISOS.md`
- `Core/Docs/DEFENSA_INYECCION_PROMPTS.md`

---

## 3) Orquestación: cómo “piensa” y ejecuta (Planner → PlanExecutor → agentes)

Se define el corazón del sistema: un orquestador que arma planes y ejecuta herramientas, y un “Panteón”/ecosistema de agentes especializados.

Documentos núcleo:

- `Core/Docs/AGENTES_Y_ORQUESTACION_LILITH.md`
- `Core/Docs/ORQUESTACION_Y_ESTRUCTURACION_4_0.md`
- `Core/Docs/DEEP_DIVE_ARQUITECTURA.md`
- `Core/Docs/DEEP_DIVE_IMPLEMENTACION_4_0.md`
- `Core/Docs/FEEDBACK_PROGRESIVO_DAG.md` (feedback incremental / DAG)

---

## 4) Agencia web (BrowserTool/Playwright) y minería/refinería

Se incorporan herramientas para navegar y extraer información de la web (con Playwright) y un pipeline para convertirlo en “hechos” consumibles.

Documentos:

- `Core/Docs/DISEÑO_BROWSER_TOOL_PLAYWRIGHT.md`
- `Core/Docs/VISION_MINERIA_REFINERIA_WEB.md`
- `Core/Docs/CALIBRACION_MINERIA_Y_FUENTES.md`
- `Core/Docs/PRUEBAS_3.7_COPYPASTE.md` (pruebas/edge)

Operación real en Discord:

- `Discord/Docs/INVESTIGA_SSE_CLIENT.md` (contrato SSE /investiga)
- `Discord/Docs/DRY_RUN_WINDOWS.md` (arranque y smoke tests en Windows)

---

## 5) Memoria: refinamiento, consolidación y horizonte 4.0

Se formaliza que Lilith no solo responde: **almacena, recupera y depura**.  
La memoria tiene límites prácticos (ruido/tokens) y se diseñan reglas para consolidar.

Documentos:

- `Core/Docs/REFINAMIENTO_MEMORIA_LILITH.md`
- `Core/Docs/CONSOLIDACION_CONOCIMIENTO.md`
- `Core/Docs/HORIZONTE_LILITH_4.0.md`
- `Core/Docs/PROYECCION_4_0_CASOS_LIMITE.md`

---

## 6) Modos de personalidad (por canal/hilo) y UX de Discord

Se añaden “modos” que alteran estilo/criterio de respuesta por canal/hilo, y se documenta el estado de UX.

Documentos:

- `Core/Docs/DISEÑO_MODOS_PERSONALIDAD.md`
- `Core/Docs/DEEP_DIVE_MODOS_PERSONALIDAD_Y_ORQUESTACION.md`
- `Core/Docs/DISCORD_UX_PANORAMA_ACTUAL.md`
- `Core/Docs/ESQUEMA_DISCORD_ASISTENTE.md`

---

## 7) Auditoría y metacognición (por qué decidí X)

Se empuja observabilidad: justificar decisiones y, cuando hay baja confianza con acciones peligrosas, pedir confirmación.

Documentos:

- `Core/Docs/MISION_AUDITORIA_DECISIONES_A_Z.md`
- `Core/Docs/DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md`

---

## 8) Pre-4.0: MuninnDB y grafo mínimo de relaciones

Se prepara (y luego se integra gradualmente) una memoria tipo “vault” (Muninn) y un grafo mínimo (relaciones `rel:*`) para comenzar a conectar conceptos/eventos/fuentes.

Documentos:

- `Core/Docs/PRE_4.0_MUNINNDB.md`
- `Core/Docs/CONSOLIDACION_CONOCIMIENTO.md` (impacto en recuperación/ruido)

---

## 9) Cierre 4.0: esquema de referencia y ruta hacia 4.1

Se consolida un esquema de referencia de 4.0 para planear 4.1 (auto-delegación, proactividad, etc.).

Documentos:

- `Core/Docs/ESQUEMA_LILITH_4_0_REFERENCIA.md`
- `Core/Docs/LILITH_4_1_AUTO_DELEGACION.md`
- `Core/Docs/PLAN_AUTOMEJORA_LILITH.md`

---

## 10) Operación, fixes y “qué quedó listo”

Documentos que reflejan estabilización final / fixes / organización:

- `Core/Docs/FIXES_Y_MEJORAS.md`
- `Core/Docs/ORGANIZACION_CARPETA.md`
- `Discord/Docs/NAZARICK_BASES.md`

Y cierres puntuales:

- `Core/Docs/CIERRE_SESION_2026-03-18.md`

---

## 11) Expansión operativa: Discord ↔ Telegram (PC control segregado)

Se define el criterio de seguridad operacional: **PC control fuera de Discord**, gestionado por Telegram con confirmación por token y batches, evitando contaminación de memoria/capacidades.

Documento operativo:

- `Core/Docs/CHECKLIST_PLAN_DISCORD_TELEGRAM_PC.md`

---

## 12) Descripción completa del proyecto (documento maestro)

Para una vista “encyclopedia” (arquitectura + componentes + seguridad + operación):

- `Core/Docs/DESCRIPCION_COMPLETA_PROYECTO_LILITH.md`

---

## 13) Qué falta para “historia perfecta” (si quieres 100% literal)

Esta historia está construida desde los docs disponibles en el repo. Si quieres que sea **literal, con cada micro‑paso y cada cambio**, lo ideal es añadir en adelante:

- Un `CHANGELOG.md` (por día o por versión).
- Un “registro de decisiones” (`ADR/`), 1 archivo por decisión.
- Vincular commits/PRs (cuando el repo use git) a los docs.

