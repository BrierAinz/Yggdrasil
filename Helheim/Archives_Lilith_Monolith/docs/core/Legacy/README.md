# Legacy - Documentación Histórica

> **Versión:** 1.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/Legacy/`

---

## ¿Qué es esta carpeta?

Esta carpeta contiene **documentación histórica** del proyecto Lilith. Son documentos antiguos, misiones completadas, análisis profundos de sesiones pasadas y guías específicas que ya no son el foco principal pero que conservan valor histórico y de referencia.

---

## Estructura

```
Legacy/
├── README.md                           # Este archivo
├── fases/                              # Documentación por fases
│   └── README.md
├── Misiones/                           # Misiones específicas completadas
│   ├── MISION_IDENTIDAD_PANTEON_PERSONAS.md
│   ├── MISION_PC_AGENT_TELEGRAM_E2E.md
│   └── MISION_SHALLTEAR_AGENTE_TACTICO.md
│
└── [Documentos sueltos organizados por categoría]
```

---

## Categorías de Documentos

### 1. Misiones (MISION_*.md)
Documentos de misión de las eras 3.x y 4.x. Contienen:
- Objetivos específicos de desarrollo
- Análisis de implementación
- Lecciones aprendidas

**Ejemplos:**
- `MISION_LILITH_3.0_COMPLETO.md` - Inicio del sistema
- `MISION_LILITH_3.9.md` - Era pre-4.0
- `MISION_LILITH_4.0.md` - Era 4.0
- `MISION_LILITH_4.1.md` - Últimas mejoras

### 2. Cierres de Sesión (CIERRE_SESION_*.md)
Resúmenes de sesiones de trabajo concretas:
- Qué se hizo ese día
- Decisiones tomadas
- Estado al finalizar

### 3. Deep Dives (DEEP_DIVE_*.md)
Análisis profundos de componentes específicos:
- `DEEP_DIVE_ARQUITECTURA.md`
- `DEEP_DIVE_AUDITORIA_DECISIONES_METACOGNICION.md`
- `DEEP_DIVE_IMPLEMENTACION_4_0.md`
- `DEEP_DIVE_MODOS_PERSONALIDAD_Y_ORQUESTACION.md`

### 4. Diseños (DISEÑO_*.md)
Documentos de diseño de features específicas:
- `DISEÑO_BROWSER_TOOL_PLAYWRIGHT.md`
- `DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md`
- `DISEÑO_MODOS_PERSONALIDAD.md`

### 5. Guías ( *_GUIDE.md)
Guías específicas para desarrolladores:
- `PLUGIN_SYSTEM_GUIDE.md`
- `SLASH_COMMANDS_GUIDE.md`
- `TELEGRAM_SESSIONS_GUIDE.md`
- `WEB_UI_GUIDE.md`

### 6. Contexto y Calibración
- `CONTEXTO_CLAUDE_CODE.md`
- `CALIBRACION_MINERIA_Y_FUENTES.md`
- `CONSOLIDACION_CONOCIMIENTO.md`

### 7. Esquemas y Arquitectura
- `ESQUEMA_DISCORD_ASISTENTE.md`
- `ESQUEMA_LILITH_4_0_REFERENCIA.md`
- `ORQUESTACION_Y_ESTRUCTURACION_4_0.md`

---

## Cuándo Consultar Legacy

### ✅ Usar documentación actual (raíz de Docs/)
- Para entender el sistema como está ahora
- Para implementar nuevas features
- Para configurar el sistema
- Para entender la arquitectura actual

### 📚 Usar Legacy
- Para entender la evolución histórica
- Para ver cómo se tomaron ciertas decisiones
- Para encontrar análisis profundos de features específicas
- Para revisar lecciones aprendidas de misiones pasadas
- Para investigar el origen de ciertas características

---

## Estado de los Documentos

| Estado | Significado |
|--------|-------------|
| ✅ Completado | Misión/feature implementada |
| 📝 Histórico | Documentación de referencia |
| ⚠️ Parcialmente obsoleto | Algunas partes pueden estar desactualizadas |
| 🗂️ Archivado | Conservado por valor histórico |

---

## Notas Importantes

1. **No todo está actualizado:** Algunos documentos pueden describir implementaciones que han evolucionado.

2. **El contexto es clave:** Cuando leas un documento de Legacy, ten en cuenta la fecha y la versión del sistema a la que se refiere.

3. **Para la verdad actual:** Siempre consulta primero la documentación numerada (00-09) en la raíz de `Docs/`.

4. **Las decisiones son eternas:** Aunque el código cambie, las decisiones de arquitectura documentadas aquí suelen seguir siendo relevantes.

---

## Documentos Destacados de Legacy

Si vas a explorar Legacy, empieza por estos:

| Documento | Por qué es importante |
|-----------|----------------------|
| `MISION_LILITH_4.0.md` | Visión de la era 4.0 |
| `DEEP_DIVE_ARQUITECTURA.md` | Análisis profundo del sistema |
| `HISTORIA_CONSTRUCCION_LILITH.md` | Evolución del proyecto |
| `DEFENSA_INYECCION_PROMPTS.md` | Seguridad (sigue siendo relevante) |

---

*Esta carpeta es el archivo histórico del proyecto. Contiene la memoria de cómo llegamos aquí.*
