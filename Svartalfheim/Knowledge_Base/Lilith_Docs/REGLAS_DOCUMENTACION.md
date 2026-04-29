# Reglas de Documentación - Lilith

> **Versión:** 1.0  
> **Fecha:** 2026-03-21  
> **Aplicable a:** Todo el ecosistema Lilith + Yggdrasil

---

## 1. Principios Fundamentales

### 1.1 Documentación Viva
- La documentación es código: se mantiene, actualiza y versiona
- Si el código cambia, la documentación debe cambiar
- Documentación desactualizada es peor que ninguna documentación

### 1.2 Audiencia
- **Primaria**: IA asistentes (tú mismo en el futuro, otras IAs)
- **Secundaria**: Desarrolladores humanos
- **Terciaria**: Usuarios finales

### 1.3 Ubicación Central
- Toda documentación técnica va en `Lilith/Core/Docs/`
- Documentación de proyecto va en `README.md` o `RESUMEN.md` en raíz
- No dispersar documentos sin estructura

---

## 2. Estructura de Archivos de Documentación

### 2.1 Numeración y Orden

```
Lilith/Core/Docs/
├── 00_INDICE_DOCUMENTACION.md      # Índice maestro (SIEMPRE actualizado)
├── 01_VISION_GENERAL_ECOSISTEMA.md # Visión de alto nivel
├── 02_BACKEND_API_ORQUESTADOR.md   # Backend
├── 03_SISTEMA_MEMORIA.md           # Memoria
├── 04_SISTEMA_TOOLS_V3.md          # Tools
├── 05_PANTEON_AGENTES.md           # Agentes
├── 06_BOTS_DISCORD_TELEGRAM.md     # Bots
├── 07_FRONTEND_SPA.md              # Frontend
├── 08_VSCODE_EXTENSION.md          # VSCode
├── 09_YGGDRASIL_REINOS.md          # Yggdrasil
├── REGLAS_DOCUMENTACION.md         # Este archivo
└── [otros temáticos].md            # Documentación adicional
```

**REGLA DE ORO:** Si creas un documento nuevo, actualiza el `00_INDICE`.

### 2.2 Convención de Nombres

| Tipo | Formato | Ejemplo |
|------|---------|---------|
| Documentos numerados | `XX_NOMBRE_EN_MAYUSCULAS.md` | `01_VISION_GENERAL.md` |
| Guías y reglas | `NOMBRE_DESCRIPTIVO.md` | `REGLAS_DOCUMENTACION.md` |
| Misiones | `MISION_LILITH_X.X.md` | `MISION_LILITH_3.9.md` |
| Checklists | `CHECKLIST_*.md` | `CHECKLIST_VALIDACION.md` |

---

## 3. Formato de Documentos

### 3.1 Header Obligatorio

Todo documento DEBE comenzar con:

```markdown
# XX - Título del Documento

> **Versión:** X.X  
> **Fecha:** YYYY-MM-DD  
> **Ubicación:** `ruta/al/archivo`
> **Autor:** [opcional]
> **Estado:** [borrador | revisado | final]

---
```

### 3.2 Estructura de Secciones

```markdown
## XX.1 Nombre de Sección Principal

Texto introductorio...

### XX.1.1 Subsección

Contenido detallado...

#### XX.1.1.1 Sub-subsección (si es necesaria)

Más detalle...
```

**Numeración:**
- Documento: `XX`
- Sección: `XX.1`, `XX.2`, etc.
- Subsección: `XX.1.1`, `XX.1.2`, etc.
- Sub-subsección: `XX.1.1.1`, etc.

### 3.3 Elementos Visuales

#### Tablas
Usar para comparaciones, configuraciones, referencias rápidas:

```markdown
| Columna 1 | Columna 2 | Columna 3 |
|-----------|-----------|-----------|
| Valor 1   | Valor 2   | Valor 3   |
```

#### Diagramas ASCII
Usar para arquitecturas, flujos, estructuras:

```markdown
```
┌─────────┐
│  Nodo A │
└────┬────┘
     │
     ▼
┌─────────┐
│  Nodo B │
└─────────┘
```
```

#### Bloques de Código
- Siempre especificar el lenguaje
- Comentar qué hace el código si no es obvio

```markdown
```python
# Esto hace X porque Y
def funcion():
    pass
```
```

---

## 4. Documentación de Código

### 4.1 Python (Backend)

#### Docstrings obligatorios para:
- Módulos
- Clases
- Funciones públicas
- Métodos complejos

#### Formato (Google style):

```python
"""
Breve descripción de una línea.

Descripción más larga si es necesario. Explica el propósito,
contexto y cualquier consideración importante.

Args:
    param1 (tipo): Descripción del parámetro
    param2 (tipo): Descripción del parámetro

Returns:
    tipo: Descripción del retorno

Raises:
    Excepcion: Cuándo se lanza

Example:
    >>> resultado = funcion(1, 2)
    >>> print(resultado)
    3
"""
```

#### Type Hints
- OBLIGATORIO en funciones públicas
- Recomendado en funciones privadas

```python
def procesar_datos(
    datos: List[Dict[str, Any]], 
    opciones: Optional[Config] = None
) -> Resultado:
    pass
```

### 4.2 TypeScript/JavaScript (Frontend/VSCode)

#### JSDoc para funciones públicas:

```typescript
/**
 * Descripción de la función
 * @param param1 - Descripción
 * @param param2 - Descripción
 * @returns Descripción del retorno
 */
function funcion(param1: string, param2: number): boolean {
    return true;
}
```

#### Interfaces documentadas:

```typescript
/**
 * Representa la configuración del sistema
 */
interface Config {
    /** URL del servidor */
    serverUrl: string;
    /** Timeout en segundos */
    timeout: number;
}
```

### 4.3 React Components

```typescript
/**
 * Componente que muestra el panel de chat
 * 
 * @example
 * <ChatPanel 
 *   sessionId="123" 
 *   onMessageSend={handleMessage}
 * />
 */
interface ChatPanelProps {
    /** ID de la sesión activa */
    sessionId: string;
    /** Callback cuando se envía un mensaje */
    onMessageSend: (msg: string) => void;
}
```

---

## 5. Documentación de APIs

### 5.1 Endpoints REST

Cada endpoint debe documentarse con:

```markdown
### POST /api/ejemplo/accion

**Descripción:** Qué hace este endpoint

**Autenticación:** [Sí/No] - Tipo

**Request:**
```json
{
    "campo1": "string (requerido) - Descripción",
    "campo2": "number (opcional) - Descripción"
}
```

**Response (200):**
```json
{
    "exito": true,
    "datos": {...}
}
```

**Response (Error):**
```json
{
    "error": "código_error",
    "mensaje": "Descripción del error"
}
```

**Códigos de estado:**
- `200` - Éxito
- `400` - Bad Request
- `401` - No autorizado
- `500` - Error interno
```

### 5.2 WebSocket Events

```markdown
### Evento: `nombre_evento`

**Dirección:** Server → Client / Client → Server / Bidireccional

**Payload:**
```json
{
    "campo": "tipo - descripción"
}
```

**Descripción:** Qué significa y cuándo se dispara
```

---

## 6. Documentación de Agentes (Panteón)

### 6.1 Plantilla de Agente

Cada agente nuevo debe documentarse:

```markdown
### Nombre del Agente

| Atributo | Valor |
|----------|-------|
| **Nombre** | Nombre |
| **Rol** | Descripción del rol |
| **Backend** | Modelo LLM |
| **Color** | Código hex |
| **Trigger** | Cuándo se activa |

**Personalidad:**
Descripción de cómo se comporta, tono, estilo.

**Prompt System:**
```
Eres [Nombre], [rol].
[Instrucciones específicas de comportamiento]
```

**Capabilities:**
- Lista de cosas que puede hacer
- Limitaciones conocidas

**Ejemplo de uso:**
```python
code_example
```
```

---

## 7. Checklist de Calidad

### 7.1 Antes de Commitear Documentación

- [ ] Header con versión, fecha y ubicación
- [ ] Índice actualizado (00_INDICE_DOCUMENTACION.md)
- [ ] Sin errores de Markdown
- [ ] Tablas bien formateadas
- [ ] Código con syntax highlighting
- [ ] Links funcionan (si los hay)
- [ ] Sin información sensible (tokens, contraseñas)

### 7.2 Revisión de Código

- [ ] Docstrings en funciones públicas
- [ ] Type hints en Python
- [ ] JSDoc en TypeScript
- [ ] Comentarios explican el "por qué", no el "qué"
- [ ] TODOs con contexto suficiente

---

## 8. Documentación de Proyectos (Yggdrasil)

### 8.1 REGLA DE ORO de Yggdrasil

**TODO proyecto debe tener en su raíz:**
- `README.md` o `RESUMEN.md`

### 8.2 Estructura de RESUMEN.md

```markdown
# Nombre del Proyecto

**Ruta:** `Yggdrasil/Reino/NombreProyecto`

---

## ¿Qué es?

Breve descripción (2-3 líneas) de qué hace este proyecto.

## ¿Para qué sirve?

- Objetivo principal
- Problema que resuelve
- Beneficios clave

## Cómo arrancarlo

```bash
# Comandos para iniciar
```

## Stack Tecnológico

- Lenguaje:
- Framework:
- Base de datos:
- Otros:

## Estructura

```
Proyecto/
├── carpeta1/    # Descripción
├── carpeta2/    # Descripción
└── archivo.ext  # Descripción
```

## Estado

- [ ] En desarrollo
- [ ] En producción
- [ ] En pausa
- [ ] Archivado

## Notas

Información adicional relevante.
```

---

## 9. Consejos Prácticos

### 9.1 Manténlo Conciso
- Menos es más
- Usa bullet points
- Evita párrafos largos

### 9.2 Sé Específico
- Mal: "Esto hace cosas"
- Bien: "Esta función procesa archivos CSV y devuelve un DataFrame"

### 9.3 Ejemplos Son Oro
- Siempre incluye ejemplos de uso
- Muestra input y output esperado

### 9.4 Actualiza Proactivamente
- Cuando cambias código, actualiza docs
- Cuando encuentras algo mal documentado, arréglalo
- Si te confunde a ti, confundirá a otros

---

## 10. Ejemplos de Buena Documentación

### Ejemplo 1: Función bien documentada

```python
async def delegate_to_agent(
    task: str,
    agent_name: str,
    context: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> AgentResult:
    """
    Delega una tarea a un agente específico del Panteón.
    
    Esta función enruta la tarea al agente apropiado, maneja
    la comunicación con el LLM backend y procesa la respuesta.
    
    Args:
        task: Descripción de la tarea a realizar
        agent_name: Nombre del agente ("eva", "adan", "odin", etc.)
        context: Contexto adicional (archivos, historial, etc.)
        timeout: Tiempo máximo de espera en segundos
        
    Returns:
        AgentResult con la respuesta y metadata
        
    Raises:
        AgentNotFoundError: Si el agente no existe
        AgentTimeoutError: Si el agente no responde a tiempo
        
    Example:
        >>> result = await delegate_to_agent(
        ...     task="Refactoriza esta función",
        ...     agent_name="adan",
        ...     context={"file_path": "main.py"}
        ... )
        >>> print(result.response)
    """
```

### Ejemplo 2: Sección de documentación técnica

```markdown
## 3.5 MuninnDB (Memoria Cognitiva)

MuninnDB es un **servicio externo** de memoria cognitiva que proporciona:
- Almacenamiento vectorial persistente
- Grafo de relaciones entre conceptos
- Sistema de triggers proactivos

### Vaults por Agente

Cada agente tiene su propio vault aislado:

| Agente | Vault | Propósito |
|--------|-------|-----------|
| lilith | lilith | Memoria general |
| eva | eva | Contexto de análisis |
| adan | adan | Patrones de código |

### Operaciones Principales

#### write()
Almacena un engrama (unidad de memoria) con metadata.

```python
await muninn.write(
    vault="lilith",
    content="Asyncio es importante para...",
    metadata={"topic": "python", "source": "conversation"}
)
```

#### activate()
Recupera memorias relevantes por similitud semántica.

```python
memories = await muninn.activate(
    vault="lilith", 
    query="cómo manejar concurrencia",
    limit=5
)
```
```

---

## 11. Herramientas Útiles

### VS Code Extensions Recomendadas
- **markdownlint** - Linting de Markdown
- **Markdown Preview Enhanced** - Preview avanzado
- **Markdown All in One** - Atajos y utilidades
- **Todo Tree** - Visualizar TODOs en el código

### Comandos de utilidad

```bash
# Buscar TODOs sin resolver
grep -r "TODO" Lilith/Core/Backend/

# Verificar links rotos en Markdown
# [requiere herramienta como markdown-link-check]

# Formatear Markdown
# [requiere prettier o similar]
```

---

## 12. Contacto y Mejoras

Si encuentras inconsistencias en la documentación o tienes sugerencias:
1. Actualiza el documento relevante
2. Incrementa la versión en el header
3. Actualiza la fecha
4. Añade una nota en el changelog si aplica

---

*Estas reglas son un contrato contigo mismo. Cumplirlas ahorra horas de trabajo futuro.*

**Documentar es actuar con empatía hacia tu yo futuro.**
