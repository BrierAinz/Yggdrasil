# Plan 19 — YggdrasilStudio v0.4: Refactor & Hardening

> **Estado:** ACTIVO  
> **Reino:** Alfheim  
> **Prioridad:** P1 — Deuda técnica + features críticas  
> **Dependencias:** Ninguna (puede ejecutarse en paralelo con LoRA training)

## Objetivo

Llevar YggdrasilStudio de v0.3.0 funcional a v0.4.0 robusto, refactorizando componentes monolíticos del frontend, añadiendo tests al backend, sincronizando versionado, completando features incompletas (img2img, upscale), y mejorando la experiencia del desarrollador.

## Métricas Actuales

| Métrica | Valor |
|---------|-------|
| Backend LOC | 3023 líneas (6 route files, 6 core files) |
| Frontend LOC | 4231 líneas (5 pages, 8 components, 5 hooks) |
| PromptBuilder | 809 líneas (component más grande) |
| Settings page | 530 líneas |
| Tests | **0** (cero tests en todo el proyecto) |
| Versión main.py | 0.1.0 (debería ser 0.3.0+) |
| TODOs conocidos | 1: "wire PromptBuilder's img2img input" |

---

## Fase 1: Sincronización & Cleanup (30 min)

### T1. Version sync
- [ ] Actualizar `"version": "0.4.0"` en `main.py`, `package.json`, `README.md`
- [ ] Añadir `CHANGELOG.md` con sección v0.4.0

### T2. Cleanup de código muerto
- [ ] Eliminar imports no usados en backend (`Python` → `ruff check`)
- [ ] Eliminar console.log forgotten en frontend
- [ ] Unificar el TODO `img2img input` de Studio.jsx — wirear el flujo completo

---

## Fase 2: Backend Hardening (2-3 horas)

### T3. Tests backend (pytest + httpx AsyncClient)
- [ ] Crear `backend/tests/conftest.py` con fixtures (TestClient, mock ComfyUI)
- [ ] `test_routes_generation.py` — submit, status, batch, interrupt
- [ ] `test_routes_history.py` — list, search, stats, favorites, delete, bulk_delete
- [ ] `test_routes_assets.py` — checkpoints, loras, vaes, samplers, schedulers
- [ ] `test_routes_workflows.py` — list, get
- [ ] `test_routes_presets.py` — CRUD
- [ ] `test_models.py` — GenerationRequest validation, WorkflowType enum
- [ ] `test_database.py` — history CRUD, favorites, search
- [ ] Meta: 40+ tests, 80%+ coverage en routes/

### T4. Nuevos endpoints
- [ ] `DELETE /api/history/{entry_id}` — ya existe en database.py, verificar wiring
- [ ] `POST /api/generate/cancel` — cancelar generación en curso (usando ComfyUI interrupt)
- [ ] `GET /api/system/gpu` — info de GPU (nvidia-smi o ComfyUI proxy)

### T5. Retry logic en ComfyUI client
- [ ] Añadir `tenacity` o retry manual (3 retries, exponential backoff) en `queue_workflow()`
- [ ] Timeout configurable para polling (`COMFYUI_POLL_TIMEOUT`, default 300s)
- [ ] Reconexión WebSocket automática con exponential backoff

### T6. LokArni bridge mejoras
- [ ] Timeout en requests (httpx timeout=10s)
- [ ] Graceful degradation si LokArni no responde (ya parcial con cache TTL)
- [ ] Logger dedicado para bridge events

---

## Fase 3: Frontend Refactor (3-4 horas)

### T7. Refactor PromptBuilder (809 → ~5 sub-componentes)
Dividir `PromptBuilder.jsx` en:
- [ ] `PromptTabs.jsx` — Tabs container (txt2img, img2img, upscale, face_swap, txt2video)
- [ ] `PromptInput.jsx` — Textarea + negative prompt
- [ ] `GenerationSettings.jsx` — Steps, CFG, sampler, scheduler, seed, batch
- [ ] `ImageUpload.jsx` — Drag-drop + WASM preprocess (img2img/face_swap/upscale source)
- [ ] `PromptBuilder.jsx` — Orquestador que compone los sub-componentes

Meta: PromptBuilder < 200 líneas, cada sub-componente < 200 líneas.

### T8. Refactor Settings (530 → ~3 sub-componentes)
Dividir `Settings.jsx` en:
- [ ] `SettingsGeneration.jsx` — Defaults de generación
- [ ] `SettingsServer.jsx` — ComfyUI connection, server info
- [ ] `SettingsUI.jsx` — UI preferences, notifications
- [ ] `Settings.jsx` — Tabs container + state management

Meta: Settings < 150 líneas, cada sub-componente < 200 líneas.

### T9. Gallery mejoras
- [ ] Añadir búsqueda por texto (prompt filter, ya existe parcialmente en frontend)
- [ ] Filtros por tipo (txt2img, img2img, txt2video, face_swap)
- [ ] Filtro por fecha (today, week, month, all)
- [ ] Vista detallada (info expandible con parámetros de generación)
- [ ] Descarga con nombre semántico (ehyra_style_001.png)

### T10. History mejoras
- [ ] Virtual list ya implementada (react-window), verificar que funciona con 1000+ entries
- [ ] Añadir delete individual con confirmación
- [ ] Añadir re-generate (re-usar misma configuración)
- [ ] Bulk select + delete mejorado

---

## Fase 4: Features Completas (2-3 horas)

### T11. img2img UI completa
- [ ] Wire PromptBuilder's img2img tab a Studio.jsx (actualizar TODO)
- [ ] Upload image → WASM preprocess → preview → enviar a ComfyUI
- [ ] Denoising strength slider (0.0-1.0)
- [ ] Source image preview con crop/resize visual

### T12. Upscale workflow UI
- [ ] Añadir tab "Upscale" en PromptBuilder
- [ ] Upscale model selector (desde `/api/assets/upscale-models`)
- [ ] Scale factor slider (2x, 4x)
- [ ] Source image upload requerido

### T13. IPAdapter FaceID UI
- [ ] Tab "Face Swap" ya tiene elemento en WorkflowType
- [ ] Source image upload + target description
- [ ] Face similarity threshold

---

## Fase 5: DevEx & Documentación (1-2 horas)

### T14. Development setup simplificado
- [ ] `backend/requirements.txt` auto-generado (o pyproject.toml)
- [ ] Frontend `npm run dev` config proxy actualizado
- [ ] `start.sh` mejora: detectar puerto ocupado, better error messages
- [ ] Añadir `.vscode/settings.json` con launch configs

### T15. README actualizado
- [ ] Sección de arquitectura con diagrama actualizado
- [ ] API endpoints documentados con curl examples
- [ ] Desarrollo local (backend + frontend + ComfyUI)
- [ ] Troubleshooting section (comúnmente: ComfyUI no corre, WASM no carga)

### T16. Changelog
- [ ] `CHANGELOG.md` con secciones por versión
- [ ] v0.4.0 entry listando todos los cambios

---

## Convenciones

- **Commits:** `[ALFHEIM] feat(studio): description` o `[ALFHEIM] refactor(studio): description`
- **Tests:** pytest en `backend/tests/`, nombres descriptivos
- **Frontend:** Componentes en PascalCase, hooks en camelCase, CSS classes con tema nórdico
- **Python:** ruff format, type hints, async/await, Pydantic v2 models
- **TypeScript:** Strict mode, Zod schemas para runtime validation

## Orden de Ejecución Sugerido

1. **T1-T2** (sync + cleanup) → commit base
2. **T3** (tests backend) → commit con tests
3. **T4-T6** (backend hardening) → commit features
4. **T7-T8** (refactor PromptBuilder + Settings) → commit refactor
5. **T9-T10** (Gallery + History mejoras) → commit features UI
6. **T11-T13** (img2img, upscale, face swap UI) → commit features completas
7. **T14-T16** (DevEx + docs) → commit final v0.4.0

## Notas

- El Go gateway (T-Go) queda pendiente — requiere instalar Go
- El WASM processor ya está integrado pero puede mejorar error handling
- Los 5 workflows ya tienen templates JSON en `backend/workflows/`
- ComfyUI no necesita correr para los tests (mockear con httpx)