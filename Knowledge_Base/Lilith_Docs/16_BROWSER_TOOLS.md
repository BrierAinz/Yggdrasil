# 16 - Browser Tools (Playwright)

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Backend/core/tools_v3/browser_tool.py`

---

## 16.1 Visión General

El subsistema **Browser Tools** proporciona a Lilith capacidades de navegación web automatizada mediante un navegador headless (Chromium + Playwright). Permite interactuar con sitios web de forma programática: navegar, hacer clic, rellenar formularios y extraer contenido.

### Casos de Uso

| Caso | Descripción |
|------|-------------|
| **Investigación web** | Navegar a URLs y extraer contenido para análisis |
| **Formularios** | Rellenar campos y enviar datos |
| **Automatización** | Clics en elementos específicos por ID |
| **Screenshots** | Capturar estado visual de páginas (futuro) |

---

## 16.2 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Lifespan                              │
│  → BrowserEngine().start()  (Playwright + Chromium)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BrowserEngine (Singleton)                     │
│  - _page (Playwright Page)                                       │
│  - _loop (asyncio event loop)                                    │
│  - goto(url) → navega y extrae estado                           │
│  - click(action_id) → clic en elemento                          │
│  - fill(action_id, text) → rellena campo                        │
│  - scroll() → desplaza viewport                                 │
│  - _get_current_state() → BrowserState                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │ dom_tagger   │     │  distiller   │     │ browser_tool │
  │ .js          │     │  .py         │     │ .py          │
  │              │     │              │     │              │
  │ Inyectado en │     │ Readability  │     │ 5 tools V3:  │
  │ página para  │     │ +            │     │ - goto       │
  │ etiquetar    │     │ markdownify  │     │ - click      │
  │ elementos    │     │ → markdown   │     │ - fill       │
  │ interactivos │     │              │     │ - scroll     │
  │              │     │              │     │ - snapshot   │
  └──────────────┘     └──────────────┘     └──────────────┘
```

---

## 16.3 Componentes

### 16.3.1 BrowserEngine

Motor central que gestiona la instancia del navegador:

```python
# Backend/core/browser/engine.py

class BrowserEngine:
    """
    Singleton que gestiona el navegador Playwright.
    Iniciado en el lifespan de FastAPI, detenido al cerrar.
    """
    
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None
        self._loop = None
        self._initialized = False
    
    async def start(self):
        """Inicia Playwright + Chromium."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self._page = await self._browser.new_page()
        self._loop = asyncio.get_event_loop()
        self._initialized = True
        logger.info("BrowserEngine iniciado")
    
    async def stop(self):
        """Detiene el navegador."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("BrowserEngine detenido")
    
    async def goto(self, url: str, include_markdown: bool = True) -> BrowserState:
        """
        Navega a URL y retorna estado de la página.
        """
        if not self._initialized:
            raise BrowserNotInitializedError()
        
        # Navegar con timeout
        await self._page.goto(url, timeout=20000, wait_until='domcontentloaded')
        
        # Inyectar dom_tagger.js para etiquetar elementos
        await self._page.evaluate(DOM_TAGGER_SCRIPT)
        
        # Esperar un momento para que JS ejecute
        await asyncio.sleep(0.5)
        
        # Extraer estado
        return await self._get_current_state(include_markdown)
```

### 16.3.2 DOM Tagger (JavaScript)

Script inyectado en cada página para etiquetar elementos interactivos:

```javascript
// Backend/core/browser/dom_tagger.js

(function() {
    // Encontrar elementos interactivos visibles
    const interactive = [
        'a', 'button', 'input', 'textarea', 'select',
        '[role="button"]', '[role="link"]', '[onclick]'
    ];
    
    const elements = document.querySelectorAll(interactive.join(','));
    const actions = [];
    let id = 0;
    
    elements.forEach(el => {
        // Solo elementos visibles
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        if (rect.top < 0 || rect.top > window.innerHeight) return;
        
        // Asignar ID único
        el.setAttribute('lilith-id', id);
        
        // Extraer texto descriptivo
        let text = el.textContent || el.value || el.placeholder || '';
        text = text.trim().substring(0, 80);
        if (!text) text = '[Icono/Vacío]';
        
        actions.push({
            id: id,
            role: el.tagName.toLowerCase(),
            type: el.type,
            text: text
        });
        
        id++;
    });
    
    // Retornar metadata
    return {
        actions_tree: actions,
        meta: {
            viewport_position: getViewportPosition(),
            can_scroll_down: canScrollDown(),
            can_scroll_up: canScrollUp()
        }
    };
})();
```

### 16.3.3 Distiller

Convierte HTML limpio a markdown usando Readability:

```python
# Backend/core/browser/distiller.py

from readability import Document
from markdownify import markdownify as md

def distill_page(html: str, url: str) -> str:
    """
    Extrae contenido principal y convierte a markdown.
    """
    # Usar Mozilla Readability para extraer contenido principal
    doc = Document(html, url=url)
    clean_html = doc.summary()
    title = doc.title()
    
    # Convertir a markdown
    markdown = md(clean_html, heading_style='ATX')
    
    return f"# {title}\n\n{markdown}"
```

---

## 16.4 Herramientas (ToolV3)

### 16.4.1 browser_goto

```python
class BrowserGotoTool(LilithTool):
    """
    Navega a una URL y retorna estado de la página.
    """
    name = "browser_goto"
    description = "Navega a una URL y extrae contenido y elementos interactivos"
    
    parameters = {
        "url": {
            "type": "string",
            "description": "URL a navegar",
            "required": True
        }
    }
    
    async def execute(self, url: str) -> ToolResult:
        engine = get_browser_engine()
        
        try:
            state = await engine.goto(url, include_markdown=True)
            
            return ToolResult(
                success=True,
                data={
                    "url": state.current_url,
                    "title": state.title,
                    "content_markdown": state.content_markdown,
                    "actions": state.actions_tree,
                    "can_scroll": state.meta.can_scroll_down
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Navigation failed: {str(e)}"
            )
```

### 16.4.2 browser_click

```python
class BrowserClickTool(LilithTool):
    """
    Hace clic en un elemento usando su action_id.
    """
    name = "browser_click"
    description = "Hace clic en un elemento identificado por action_id"
    
    parameters = {
        "action_id": {
            "type": "integer",
            "description": "ID del elemento (de browser_goto)",
            "required": True
        }
    }
    
    async def execute(self, action_id: int) -> ToolResult:
        engine = get_browser_engine()
        
        try:
            # Hacer clic usando selector lilith-id
            await engine.click(f'[lilith-id="{action_id}"]')
            
            # Retornar nuevo estado
            state = await engine.get_current_state()
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Clicked element {action_id}",
                    "new_url": state.current_url,
                    "actions": state.actions_tree
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Click failed: {str(e)}"
            )
```

### 16.4.3 browser_fill

```python
class BrowserFillTool(LilithTool):
    """
    Rellena un campo de texto.
    """
    name = "browser_fill"
    description = "Escribe texto en un campo identificado por action_id"
    
    parameters = {
        "action_id": {
            "type": "integer",
            "required": True
        },
        "text": {
            "type": "string",
            "description": "Texto a escribir",
            "required": True
        }
    }
    
    async def execute(self, action_id: int, text: str) -> ToolResult:
        engine = get_browser_engine()
        
        try:
            # Limpiar y escribir
            selector = f'[lilith-id="{action_id}"]'
            await engine.fill(selector, text)
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Filled field {action_id} with: {text[:50]}..."
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Fill failed: {str(e)}"
            )
```

### 16.4.4 browser_scroll

```python
class BrowserScrollTool(LilithTool):
    """
    Desplaza el viewport.
    """
    name = "browser_scroll"
    description = "Desplaza la página hacia arriba o abajo"
    
    parameters = {
        "direction": {
            "type": "string",
            "enum": ["up", "down"],
            "required": True
        },
        "amount": {
            "type": "integer",
            "description": "Píxeles a desplazar (default: viewport height)",
            "default": None
        }
    }
    
    async def execute(self, direction: str, amount: int = None) -> ToolResult:
        engine = get_browser_engine()
        
        try:
            state = await engine.scroll(direction, amount)
            
            return ToolResult(
                success=True,
                data={
                    "direction": direction,
                    "position": state.meta.viewport_position,
                    "can_scroll_down": state.meta.can_scroll_down,
                    "can_scroll_up": state.meta.can_scroll_up
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Scroll failed: {str(e)}"
            )
```

### 16.4.5 browser_snapshot

```python
class BrowserSnapshotTool(LilithTool):
    """
    Captura el estado actual sin navegar.
    """
    name = "browser_snapshot"
    description = "Obtiene el estado actual de la página (URL, elementos, contenido)"
    
    async def execute(self) -> ToolResult:
        engine = get_browser_engine()
        
        try:
            state = await engine.get_current_state(include_markdown=True)
            
            return ToolResult(
                success=True,
                data={
                    "url": state.current_url,
                    "title": state.title,
                    "actions": state.actions_tree,
                    "content_preview": state.content_markdown[:1000]
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Snapshot failed: {str(e)}"
            )
```

---

## 16.5 Modelo de Datos

### BrowserState

```python
@dataclass
class BrowserState:
    """Estado completo de una página web."""
    
    page_id: str = "v1-single-tab"
    current_url: str = ""
    title: str = ""
    
    # Metadata del viewport
    meta: ViewportMeta = field(default_factory=ViewportMeta)
    
    # Elementos interactivos etiquetados
    actions_tree: List[ActionElement] = field(default_factory=list)
    
    # Contenido convertido a markdown
    content_markdown: Optional[str] = None


@dataclass
class ViewportMeta:
    """Metadata del viewport."""
    viewport_position: str = "top"  # "top" | "middle" | "bottom"
    can_scroll_down: bool = False
    can_scroll_up: bool = False


@dataclass
class ActionElement:
    """Elemento interactivo etiquetado."""
    id: int
    role: str  # "a", "button", "input", etc.
    type: Optional[str] = None  # para inputs
    text: str = ""  # texto visible truncado a 80 chars
```

---

## 16.6 Integración con ToolRegistryV3

```python
# Backend/core/tools_v3/__init__.py

def create_default_registry() -> ToolRegistryV3:
    """Crea registro con todas las tools incluyendo browser."""
    registry = ToolRegistryV3()
    
    # Tools estándar
    registry.register("read_file", ReadFileTool())
    registry.register("edit_file", EditFileTool())
    # ...
    
    # Browser tools
    from .browser_tool import (
        BrowserGotoTool,
        BrowserClickTool,
        BrowserFillTool,
        BrowserScrollTool,
        BrowserSnapshotTool
    )
    
    registry.register("browser_goto", BrowserGotoTool())
    registry.register("browser_click", BrowserClickTool())
    registry.register("browser_fill", BrowserFillTool())
    registry.register("browser_scroll", BrowserScrollTool())
    registry.register("browser_snapshot", BrowserSnapshotTool())
    
    return registry
```

---

## 16.7 Configuración

```json
// Core/Config/browser.json
{
  "enabled": true,
  "headless": true,
  "viewport": {
    "width": 1280,
    "height": 720
  },
  "timeouts": {
    "navigation": 20,
    "click": 15,
    "fill": 10
  },
  "allowed_domains": [],
  "blocked_domains": [
    "localhost",
    "127.0.0.1",
    "0.0.0.0"
  ],
  "max_content_length": 50000
}
```

---

## 16.8 Seguridad

| Riesgo | Mitigación |
|--------|------------|
| **Localhost scanning** | Dominios bloqueados: localhost, 127.0.0.1, 10.x.x.x |
| **URLs maliciosas** | Validación de URL antes de navegar |
| **Ejecución de JS** | Sandbox de Chromium, sin privilegios |
| **Extracción masiva** | Límite de contenido (max_content_length) |
| **Rate limiting** | Cooldown entre navegaciones por sesión |

---

## 16.9 Limitaciones y Consideraciones

1. **Single-tab**: Solo una pestaña activa por proceso
2. **Estado compartido**: Todos los usuarios comparten el mismo browser (isolación futura)
3. **Timeouts**: Navegación lenta puede exceder límites
4. **JavaScript dinámico**: Algunos sitios pueden requerir esperas adicionales
5. **CAPTCHA**: No soporta resolución automática de CAPTCHAs

---

## 16.10 Referencias

| Recurso | Ubicación |
|---------|-----------|
| BrowserEngine | `Backend/core/browser/engine.py` |
| DOM Tagger | `Backend/core/browser/dom_tagger.js` |
| Distiller | `Backend/core/browser/distiller.py` |
| Browser Tools | `Backend/core/tools_v3/browser_tool.py` |
| Configuración | `Core/Config/browser.json` |

---

*Documento 16 del índice - Browser Tools (Playwright)*
