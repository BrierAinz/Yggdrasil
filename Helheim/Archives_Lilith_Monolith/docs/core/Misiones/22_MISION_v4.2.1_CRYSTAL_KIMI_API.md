# Misión Crystal v4.2 - Migración a Kimi API

> **Versión:** 4.2
> **Fecha:** 2026-03-23
> **Ubicación:** `Lilith/Core/Docs/MISION_CRYSTAL_v4.2_KIMI_API.md`
> **Estado:** Completado

---

## 1. Resumen Ejecutivo

Migración completa del agente **Crystal** desde **OpenRouter** a **API de Kimi directa**.

Crystal es la cara pública de Lilith en Discord (usuarios PUBLIC). Esta migración elimina el proxy intermedio de OpenRouter, reduciendo latencia y simplificando la infraestructura.

| Aspecto | Antes (v4.1) | Después (v4.2) |
|---------|--------------|----------------|
| **Backend** | OpenRouter (proxy) | Kimi API directa |
| **Variable** | `OPENROUTER_API_KEY` | `CRYSTAL_KIMI_API_KEY` |
| **Modelos** | Haiku, GPT-4o-mini | `kimi-for-coding` |
| **Fallback** | Ollama local | Ollama local (sin cambios) |

---

## 2. Cambios Implementados

### 2.1 Código - Agente Crystal

**Archivo:** `Core/Backend/core/agents/crystal_agent.py`

```python
def _init_kimi_client(self):
    """Inicializar cliente Kimi con API key de Crystal"""
    from ...llm.kimi_client import KimiClient

    # Intentar obtener API key específica de Crystal
    api_key = os.environ.get("CRYSTAL_KIMI_API_KEY")

    # Fallback a KIMI_API_KEY general si no hay específica
    if not api_key:
        api_key = os.environ.get("KIMI_API_KEY")

    if api_key:
        self.kimi_client = KimiClient(api_key=api_key)
```

**Cambios realizados:**
- Nuevo método `_init_kimi_client()` para inicializar `KimiClient`
- Modificado `process_message()` para usar `_chat_with_kimi()` en lugar de OpenRouter
- Agregado método `_chat_with_kimi()` para llamada síncrona a Kimi
- Parámetro `openrouter_client` marcado como deprecated (mantenido para compatibilidad)
- Fallback a Ollama local preservado

### 2.2 Código - Discord Handler

**Archivo:** `Discord/handlers/chat_handler.py`

```python
# Antes:
from Backend.api.openrouter_client import get_openrouter_client
openrouter = get_openrouter_client()
result = await crystal.process_message(
    message=text,
    openrouter_client=openrouter,
    ...
)

# Ahora:
result = await crystal.process_message(
    message=text,
    ollama_client=None
)
```

**Cambios realizados:**
- Eliminado import de `get_openrouter_client`
- Eliminada dependencia de OpenRouter en llamada a Crystal
- Crystal maneja su propio cliente internamente

### 2.3 Configuración - Variables de Entorno

**Archivo:** `.env`

```bash
# Variable nueva (v4.2)
CRYSTAL_KIMI_API_KEY=sk-kimi-...

# Variable anterior (obsoleta para Crystal)
# OPENROUTER_API_KEY ya no se usa para Crystal
```

---

## 3. Arquitectura Resultante

```
Usuario Público (Discord)
    ↓
[Discord Bot] → Detecta rol "public"
    ↓
[DiscordRouter] → Decide usar Crystal
    ↓
[Crystal Agent] → Aplica restricciones
    ├── [Input Sanitizer] → Bloquea inyecciones
    ├── [Rate Limiter] → 10 msg/hr
    ├── [Ephemeral Memory] → TTL 1h
    ↓
[KimiClient] → API directa a Kimi
    ├── Retry con backoff
    ├── Headers x-api-key
    └── Modelo: kimi-for-coding
    ↓
[Fallback Ollama] → Si Kimi falla
    └── Modelo: llama3.2:latest
    ↓
[Output Sanitizer] → Redacta secretos
    ↓
Respuesta al usuario
```

---

## 4. Documentación Actualizada

### 4.1 Documentos Principales

| Documento | Sección Actualizada |
|-----------|---------------------|
| `05_PANTEON_AGENTES.md` | Tabla de atributos Crystal, backend Kimi |
| `02_BACKEND_API_ORQUESTADOR.md` | Clientes LLM, tabla Panteón |
| `12_TESTING.md` | Referencia a `test_crystal_kimi.py` |

### 4.2 Documentos Legacy

| Documento | Cambios Realizados |
|-----------|-------------------|
| `Legacy/CRYSTAL_PUBLIC_MODE.md` | Arquitectura v4.2, historial de cambios, troubleshooting |
| `Legacy/CAMBIOS_CRYSTAL_DISCORD_TELEGRAM.md` | Sección 2.1 (cascada), sección 4 (config) |
| `Legacy/CHECKLIST_PLAN_DISCORD_TELEGRAM_PC.md` | Objetivo Discord actualizado |
| `Legacy/ESTADO_ACTUAL_LILITH.md` | Tabla de agentes del Panteón |
| `Legacy/DESCRIPCION_COMPLETA_PROYECTO_LILITH.md` | Roadmap: Crystal implementado |

---

## 5. Referencia Rápida

### 5.1 Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `CRYSTAL_KIMI_API_KEY` | Sí | API key dedicada para Crystal |
| `KIMI_API_KEY` | No | Fallback si no hay CRYSTAL_KIMI_API_KEY |

### 5.2 Configuración (crystal.json)

```json
{
  "enabled": true,
  "kimi_model": "kimi-for-coding",
  "allowed_tools": ["web_search", "charla", "chiste", "meme"],
  "memory_isolation": {
    "vault": "discord_public",
    "excluded_tags": ["telegram", "pc_ops", "owner", "sensitive"]
  }
}
```

### 5.3 Rate Limits Crystal

| Métrica | Valor |
|---------|-------|
| Mensajes/hora | 10 |
| Tokens/día | 50,000 |
| Cooldown | 60 segundos |

---

## 6. Verificación (Smoke Tests)

```bash
# 1. Verificar variable de entorno
echo $CRYSTAL_KIMI_API_KEY

# 2. Probar conexión a Kimi
curl -H "x-api-key: $CRYSTAL_KIMI_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     https://api.kimi.com/coding/v1/models

# 3. Enviar mensaje de prueba en Discord (canal público)
# El bot debe responder como Crystal vía Kimi
```

---

## 7. Notas de Implementación

### 7.1 Decisiones Tomadas

1. **API key dedicada:** Crystal usa `CRYSTAL_KIMI_API_KEY` separada de `KIMI_API_KEY` para:
   - Permitir rate limiting independiente
   - Facilitar tracking de costos por canal
   - Posibilidad de desactivar Crystal sin afectar a Lilith

2. **Mantenimiento de Ollama fallback:** Se conserva Ollama local para:
   - Operación offline
   - Fallback si Kimi API falla
   - Reducción de costos en testing

3. **Compatibilidad hacia atrás:** Parámetro `openrouter_client` mantenido pero ignorado:
   - Evita breaking changes en llamadores existentes
   - Permite rollback rápido si es necesario

### 7.2 Limitaciones Conocidas

- **No hay streaming:** Crystal v4.2 usa `generate_text()` síncrono
- **Memoria efímera:** TTL 1h, no persiste en disco
- **Sin acceso a filesystem:** Limitación intencional de seguridad

---

## 8. Changelog

### v4.2 (2026-03-23)

- [x] Migración de OpenRouter a Kimi API directa
- [x] Nueva variable `CRYSTAL_KIMI_API_KEY`
- [x] Actualización de documentación (11 archivos)
- [x] Eliminación de dependencia OpenRouter en Discord handler
- [x] Preservación de fallback Ollama

---

## 9. Referencias

- `Core/Backend/core/agents/crystal_agent.py` - Implementación del agente
- `Core/Backend/llm/kimi_client.py` - Cliente Kimi
- `Core/Config/crystal.json` - Configuración de Crystal
- `Discord/handlers/chat_handler.py` - Handler de Discord

---

*Misión completada el 2026-03-23*
