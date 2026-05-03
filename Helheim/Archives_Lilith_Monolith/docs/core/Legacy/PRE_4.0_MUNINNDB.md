# Pre-4.0: MuninnDB como memoria cognitiva

**Propósito:** Integrar [MuninnDB](https://muninndb.com) como capa de memoria cognitiva **antes** del salto a la 4.0 (ecosistema de agentes autónomos). Así Lilith gana prioridad temporal, asociaciones Hebbianas y activación explicable sin depender de un LLM en el pipeline de memoria.

**Secuencia:** 3.9 (fixes) → **MuninnDB (opcional)** → 4.0.

---

## Qué es MuninnDB

MuninnDB es una **base de datos cognitiva para IA**: pensada para memoria persistente con prioridad temporal (ACT-R), aprendizaje Hebbiano (asociaciones por co-activación) y triggers semánticos (push). No usa LLM en el pipeline de memoria: scoring y activación son matemáticos y deterministas.

- **Write:** guardar “engramas” (concepto, contenido, tags).
- **Activate:** recuperar las memorias más relevantes para un contexto; devuelve un campo **Why** con el desglose del score (BM25, Hebbian, temporal).
- **Una sola binaria:** despliegue local sin Redis, Pinecone ni embeddings externos; SDK Python (`pip install muninndb`) y MCP para Cursor/Claude.

Documentación y quickstart: [muninndb.com](https://muninndb.com).

---

## Por qué usarlo antes de 4.0

| Hoy (memoria Lilith) | Con MuninnDB |
|----------------------|--------------|
| Hechos + perfil en JSON/vector; peso manual o por `recent_facts_weight`. | Prioridad temporal (ACT-R) y Hebbiano: lo reciente y lo co-activado sube solo. |
| Sin explicación de por qué se eligió un hecho. | Campo **Why** en cada activación (auditable, sin LLM). |
| Sin aprendizaje por uso. | Cada `Activate` actualiza pesos Hebbianos. |
| Opcional: triggers/proactividad. | Triggers semánticos (push cuando algo es relevante). |

Encaja con la visión 4.0: cuando cada agente tenga memoria propia, MuninnDB puede ser el backend de cada “vault” por agente o el vault global de Lilith.

---

## Cómo integrarlo

1. **Despliegue:** Ejecutar MuninnDB en local (por ejemplo `curl -fsSL https://muninndb.com/install.sh | sh` y `muninn init` / `muninn start`). API REST en `http://localhost:8475`, token de autenticación opcional.
2. **Adapter en Lilith:** El módulo `Backend/core/memory/muninn_adapter.py` usa el SDK (`from muninn import MuninnClient`) si está disponible; **si el SDK no se puede importar**, usa la **API REST** (POST `/api/activate`, POST `/api/engrams`) vía `httpx`. No es obligatorio instalar `muninndb`; con el servidor MuninnDB corriendo, el adapter funciona por REST.
   - Exponga `write(vault, concept, content, tags)` para guardar hechos/preferencias.
   - Exponga `activate(vault, context, top_k)` para recuperar memorias relevantes.
   - Opcional: devolver el **Why** para logs o para inyectar “por qué se eligió esto” en contexto de depuración.
3. **Config:** Añadir en `Config/memory.json` (o un `Config/muninn.json`) algo como:
   - `muninn_enabled`: true/false.
   - `muninn_url`, `muninn_token`, `muninn_vault` (ej. `"default"` o `"lilith"`).
4. **Integración con MemoryManager / get_context_for_prompt:** Si `muninn_enabled` es true, usar MuninnDB como fuente (o complemento) de hechos para el prompt: llamar `activate` con el mensaje del usuario (o una versión resumida) y formatear los resultados en el bloque de contexto. Las escrituras pueden hacerse desde el flujo de resumen de sesión, feedback o desde una tool `store_interaction` mejorada.
5. **Opcional — MCP:** Si se usa Cursor/Claude con MCP, MuninnDB puede configurarse como servidor MCP (`muninn init` lo hace); Lilith podría seguir usando el SDK desde el backend y el MCP quedar para uso directo del IDE.

---

## Criterios de cierre (Pre-4.0)

- [ ] MuninnDB instalado y corriendo en local (o en un entorno de desarrollo).
- [x] Adapter Python que llame `write` y `activate` con la config del proyecto (`Backend/core/memory/muninn_adapter.py`).
- [x] Config `Config/muninn.json` con `muninn_enabled`, `muninn_url`, `muninn_token`, `muninn_vault`, `muninn_activate_top_k`.
- [x] Flujo de contexto para chat: `MemoryManager.search_context()` usa MuninnDB como complemento cuando `muninn_enabled=true`; bloque "[Memoria MuninnDB]" inyectado en el prompt.
- [x] Documentado en Config/README.md y en este doc.

---

## Cómo conseguir el token para Lilith

La API REST de Muninn (puerto 8475) exige `Authorization: Bearer <token>`. Para que Lilith use MuninnDB:

### 1. Token por defecto (mcp.token)

Al ejecutar **`muninn init`**, se genera un token y se guarda en:

- **Windows:** `%USERPROFILE%\.muninn\mcp.token`
- **Linux/macOS:** `~/.muninn/mcp.token`

Lilith lee ese archivo automáticamente si en `Config/muninn.json` dejas `muninn_token` vacío (`""`).

### 2. Comprobar que el token funciona

Desde la raíz del proyecto Lilith (o desde `Core`):

```bash
python Core/Scripts/test_muninn_token.py
```

El script prueba `/api/health` y `/api/activate`. Si ves **200** en activate, el token es válido. Si ves **401**, el servidor no está aceptando ese token (sigue el apartado siguiente).

### 3. Si da 401: mismo token que el servidor

El servidor Muninn debe haber arrancado usando **el mismo** token que está en `mcp.token`. Si iniciaste el servidor con otro token o sin leer ese archivo, la REST devolverá 401.

- **Reiniciar Muninn** para que use el token actual de `mcp.token`:
  - `muninn stop`
  - `muninn start`  
  (En muchas instalaciones, `muninn start` sin argumentos usa el token generado por `muninn init`.)
- Si usas un token distinto (p. ej. uno que te hayan dado), ponlo en `Config/muninn.json` en `muninn_token` y en el servidor (por ejemplo `muninn start --mcp-token "tu_token"`).

### 4. Token explícito en Lilith

Si quieres usar un token que **no** está en `mcp.token` (por ejemplo uno creado desde la UI o por otro medio):

1. Abre `Core/Config/muninn.json`.
2. Asigna el valor a `muninn_token`: `"muninn_token": "mk_tu_token_aqui"` (o el formato que te indique Muninn).
3. Activa Muninn: `"muninn_enabled": true`.
4. Reinicia la API de Lilith.

### 5. UI y documentación

- **Panel web:** http://127.0.0.1:8476 — entra (por defecto `root` / `password`) y revisa si hay una sección de API keys o tokens para la REST.
- **Documentación oficial:** [REST API Reference](https://muninndb.com/docs/api/rest) y [Troubleshooting](https://muninndb.com/docs/troubleshooting).
- Si el token de `mcp.token` sigue dando 401 tras reiniciar Muninn, puede que la REST use un tipo de token distinto (p. ej. formato `mk_...`); en ese caso habría que obtenerlo desde la UI, la documentación o el equipo de Muninn (p. ej. [GitHub Issues](https://github.com/scrypster/muninndb/issues)).

---

## Solución de problemas: 401 Unauthorized

Si Lilith muestra **`MuninnAdapter REST activate failed: 401 Unauthorized`** al llamar a `http://localhost:8475/api/activate`:

1. **Token correcto:** La API REST de MuninnDB exige `Authorization: Bearer <token>`. El token lo genera `muninn init` y suele estar en:
   - **Windows:** `%USERPROFILE%\.muninn\mcp.token`
   - **Linux/macOS:** `~/.muninn/mcp.token`  
   El adapter usa por defecto ese archivo si en `Config/muninn.json` no pones `muninn_token`. Si lo pones, debe ser **exactamente** el mismo valor que en ese archivo.

2. **Servidor en marcha:** Comprueba que MuninnDB esté corriendo (`muninn start` o que el proceso esté activo). La REST API escucha en el puerto **8475**.

3. **Mismo token que MCP:** Si Cursor/MCP ya se conecta a Muninn (puerto 8750), el mismo token de `mcp.token` debe valer para la REST (8475). Si aun así da 401, consulta la [documentación REST de MuninnDB](https://muninndb.com/docs/api/rest) por si hubiera un token adicional para la API (p. ej. formato `mk_...`).

4. **Config en Lilith:** En `Core/Config/muninn.json` puedes dejar `muninn_token` vacío (`""`) para que el adapter tome el token desde `~/.muninn/mcp.token` automáticamente.

---

## Referencias

- [MuninnDB](https://muninndb.com) — sitio oficial, documentación, SDK y quickstart.
- `HORIZONTE_LILITH_4.0.md` — visión 4.0 (agentes autónomos, memoria por agente).
- `ROADMAP_HACIA_4.0.md` — memoria y pre-4.0.
