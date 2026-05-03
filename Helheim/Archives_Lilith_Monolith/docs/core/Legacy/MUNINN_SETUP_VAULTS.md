# Setup: Vaults de MuninnDB para Agentes

**Fecha**: 2026-03-19  
**Estado**: ✅ CONFIGURADO — Todos los vaults y tokens están en `muninn.json`

---

## Vaults Configurados

| Vault | Token | Agente |
|-------|-------|--------|
| `default` | `mk_RkQ48F...` | Vault legacy/fallback |
| `lilith` | `mk_ClydCq...` | Lilith (global) |
| `odin` | `mk_zTWCSj...` | Odín (análisis masivo) |
| `eva` | `mk_f_PZGO...` | Eva (documentación) |
| `adan` | `mk_qDLCLY...` | Adán (código/tests) |
| `crystal` | `mk_wcpdqj...` | Crystal (público) |

---

## Verificación

Para verificar que todo funciona, reinicia Lilith y busca en los logs:

```
INFO: lilith.muninn: MuninnDB activate: token=SET, url=http://127.0.0.1:8475, vault=odin (mapped=odin)
INFO: lilith.muninn: MuninnDB activate: token=SET, url=http://127.0.0.1:8475, vault=eva (mapped=eva)
```

Si ves `token=EMPTY` o errores 401/403, verifica que los vaults existan en MuninnDB.

---

## Notas de Arquitectura

- **Aislamiento cognitivo**: Cada agente lee/escribe solo en su vault
- **Proactividad**: `proactive_engine.py` sondea todos los vaults configurados
- **Confirmaciones**: Solo el vault `lilith` recibe las confirmaciones del owner
- **Dashboard**: Muestra métricas de todos los vaults en tiempo real
