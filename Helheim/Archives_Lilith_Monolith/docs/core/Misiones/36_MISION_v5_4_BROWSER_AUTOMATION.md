# Misión 36: Advanced Browser Automation v5.4

> **Versión objetivo**: Lilith v5.4
> **Feature**: Playwright-based Browser Automation
> **Prioridad**: Media-Alta (capability expansion)
> **Esfuerzo estimado**: 16-20 horas
> **Dependencias**: v5.0-alpha deployado

---

## 🎯 Objetivo

Implementar un sistema robusto de **automatizacion web** usando Playwright que permita a Lilith:
- Navegar y extraer contenido de paginas web complejas
- Interactuar con SPAs y sitios con JavaScript
- Tomar screenshots y generar PDFs
- Llenar formularios y ejecutar acciones
- Esperar dinamicamente por contenido

**Estado actual**: Web scraping basico con requests/BeautifulSoup
**Estado deseado**: Browser automation completo con Playwright + analisis inteligente

---

## 💡 Motivacion

### Problemas Actuales

```
Usuario: "Monitorea precios en Amazon"
Sistema actual: requests.get() → 403 Forbidden (bot detected)

Usuario: "Extrae tabla de esta pagina SPA"
Sistema actual: BeautifulSoup → tabla vacia (contenido cargado con JS)

Usuario: "Toma screenshot de esta dashboard"
Sistema actual: No puede (requiere browser real)
```

**Limitaciones**:
- Sites modernos detectan bots simples
- SPAs requieren JavaScript execution
- No puede interactuar (clicks, forms, login)
- No puede esperar por contenido dinamico
- No puede tomar screenshots

### Solucion: Playwright Automation

```
Usuario: "Monitorea precios en Amazon"
→ Browser headless con Playwright
→ Stealth mode (evita deteccion)
→ Extrae precios correctamente
→ Success

Usuario: "Extrae tabla de esta SPA"
→ Browser espera por JS execution
→ waitFor selector aparezca
→ Extrae tabla completa
→ Success

Usuario: "Toma screenshot del dashboard"
→ Browser navega a URL
→ Espera carga completa
→ Screenshot full-page
→ PDF generado
→ Success
```

---

## 🏗️ Arquitectura

### Componentes Nuevos

#### 1. `PlaywrightBrowser`

**Ubicacion**: `Core/Backend/core/playwright_browser.py`

```python
class PlaywrightBrowser:
    """
    Wrapper sobre Playwright para automatizacion web.

    Features:
    - Browser pool (reuse contexts)
    - Stealth mode (anti-deteccion)
    - Smart waiting (dinamico)
    - Screenshot & PDF generation
    - Network interception
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts = {}  # Pool de contextos

    async def initialize(self):
        """Inicializa Playwright"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

    async def get_context(
        self,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict] = None
    ):
        """Obtiene o crea contexto de browser"""

        context_config = {
            'viewport': viewport or {'width': 1920, 'height': 1080},
            'user_agent': user_agent or self._get_random_user_agent(),
            'java_script_enabled': True,
            'bypass_csp': True
        }

        context = await self.browser.new_context(**context_config)
        await self._apply_stealth_mode(context)

        return context

    async def _apply_stealth_mode(self, context):
        """Aplica tecnicas anti-deteccion"""

        await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        window.chrome = { runtime: {} };
        """)

    async def navigate_and_extract(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        wait_for: Optional[str] = None,
        timeout: int = 30000
    ) -> Dict:
        """Navega a URL y extrae contenido"""

        context = await self.get_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)
            else:
                await page.wait_for_load_state('networkidle', timeout=timeout)

            content = {
                'url': page.url,
                'title': await page.title(),
                'html': await page.content(),
                'text': await page.inner_text('body'),
            }

            if selectors:
                content['selectors'] = {}
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        content['selectors'][selector] = [
                            await el.inner_text() for el in elements
                        ]
                    except:
                        content['selectors'][selector] = []

            return content

        finally:
            await page.close()
            await context.close()

    async def take_screenshot(
        self,
        url: str,
        wait_for: Optional[str] = None,
        full_page: bool = True,
        format: str = 'png'
    ) -> bytes:
        """Toma screenshot de pagina"""

        context = await self.get_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle')

            if wait_for:
                await page.wait_for_selector(wait_for)

            screenshot = await page.screenshot(
                full_page=full_page,
                type=format
            )

            return screenshot

        finally:
            await page.close()
            await context.close()

    async def generate_pdf(
        self,
        url: str,
        wait_for: Optional[str] = None
    ) -> bytes:
        """Genera PDF de pagina"""

        context = await self.get_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle')

            if wait_for:
                await page.wait_for_selector(wait_for)

            pdf = await page.pdf(
                format='A4',
                print_background=True
            )

            return pdf

        finally:
            await page.close()
            await context.close()

    async def fill_form(
        self,
        url: str,
        form_data: Dict[str, str],
        submit_selector: Optional[str] = None
    ) -> Dict:
        """Llena y submits formulario"""

        context = await self.get_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle')

            for selector, value in form_data.items():
                await page.fill(selector, value)

            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state('networkidle')

            return {
                'success': True,
                'final_url': page.url,
                'title': await page.title()
            }

        finally:
            await page.close()
            await context.close()
```

#### 2. `BrowserTaskExecutor`

**Ubicacion**: `Core/Backend/core/browser_task_executor.py`

```python
class BrowserTaskExecutor:
    """
    Ejecuta tareas de browser automation con retry y error handling.
    """

    def __init__(self):
        self.browser = PlaywrightBrowser()
        self.task_queue = asyncio.Queue()

    async def execute_task(
        self,
        task_type: str,
        params: Dict,
        max_retries: int = 3
    ) -> Dict:
        """Ejecuta tarea con retry logic"""

        for attempt in range(max_retries):
            try:
                if task_type == 'extract':
                    result = await self.browser.navigate_and_extract(**params)
                elif task_type == 'screenshot':
                    result = await self.browser.take_screenshot(**params)
                elif task_type == 'pdf':
                    result = await self.browser.generate_pdf(**params)
                elif task_type == 'form':
                    result = await self.browser.fill_form(**params)
                else:
                    raise ValueError(f"Unknown task type: {task_type}")

                return {'success': True, 'data': result}

            except TimeoutError:
                if attempt == max_retries - 1:
                    return {'success': False, 'error': 'Timeout'}
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                if attempt == max_retries - 1:
                    return {'success': False, 'error': str(e)}
                await asyncio.sleep(1)
```

#### 3. `WebContentAnalyzer`

**Ubicacion**: `Core/Backend/core/web_content_analyzer.py`

```python
class WebContentAnalyzer:
    """
    Analiza contenido extraido de paginas web.

    Features:
    - Extraccion de metadatos
    - Deteccion de tipo de pagina
    - Extraccion de estructuras (tablas, listas)
    - Limpieza de HTML
    """

    def analyze_page(self, content: Dict) -> Dict:
        """Analiza contenido de pagina"""

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content['html'], 'html.parser')

        return {
            'type': self._detect_page_type(soup),
            'metadata': self._extract_metadata(soup),
            'headings': self._extract_headings(soup),
            'tables': self._extract_tables(soup),
            'links': self._extract_links(soup),
            'images': self._extract_images(soup),
            'forms': self._detect_forms(soup),
            'cleaned_text': self._clean_text(content['text'])
        }

    def _extract_tables(self, soup) -> List[Dict]:
        """Extrae tablas como estructuras"""
        tables = []
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                rows.append(cells)
            tables.append({'rows': rows})
        return tables
```

---

## 📋 Alcance (Scope)

### ✅ Fase 1: Core Browser Automation (v5.4.0)

1. **Playwright Integration**
   - Browser pool management
   - Context reuse
   - Stealth mode

2. **Basic Operations**
   - Navigate & extract
   - Screenshots (PNG, JPEG)
   - PDF generation
   - Form filling

3. **Smart Waiting**
   - waitFor selectors
   - Network idle detection
   - Dynamic timeout adjustment

4. **Content Analysis**
   - Page type detection
   - Structure extraction (tables, lists)
   - Metadata extraction

### ✅ Fase 2: Tools Integration (v5.4.0)

1. **New Tools**
   - `browser_navigate` - Navegar y extraer
   - `browser_screenshot` - Screenshot
   - `browser_pdf` - Generar PDF
   - `browser_fill_form` - Llenar forms

2. **Planner Integration**
   - Deteccion automatica de "screenshot"
   - Deteccion de "extraer tabla"
   - Deteccion de "navegar a"

### ❌ NO Incluido (v5.5+)

- Cookie management persistente
- Multi-tab orchestration
- Video recording
- Network interception avanzada
- Proxy rotation
- CAPTCHA solving

---

## 🎯 Criterios de Éxito

### Tests Unitarios (16 nuevos)

```python
# test_playwright_browser.py (10 tests)
def test_stealth_mode()
def test_navigate_and_extract()
def test_screenshot()
def test_pdf_generation()
def test_form_filling()

# test_web_content_analyzer.py (6 tests)
def test_detect_page_type()
def test_extract_tables()
def test_extract_metadata()
```

### Smoke Tests (4 criticos)

1. **Extract con SPA**
   ```
   URL: React SPA
   → Espera JS execution
   → Extrae contenido correcto
   ```

2. **Screenshot full-page**
   ```
   URL: Pagina larga
   → Screenshot completo
   → Formato PNG
   ```

3. **Llenar formulario**
   ```
   URL: Form de contacto
   → Llena campos
   → Submit exitoso
   ```

4. **Anti-deteccion**
   ```
   URL: Bot detection test
   → Stealth mode activo
   → Pasa deteccion
   ```

---

## 📦 Archivos a Crear/Modificar

### Nuevos (9 archivos)
```
Core/Backend/
├── core/
│   ├── playwright_browser.py         # Core wrapper
│   ├── browser_task_executor.py      # Task execution
│   ├── web_content_analyzer.py       # Content analysis
│   └── browser_tools.py              # Tool definitions
├── Tests/
│   ├── test_playwright_browser.py    # 10 tests
│   └── test_web_content_analyzer.py  # 6 tests

Core/Config/
└── browser_automation.json           # Config (nuevo)
```

### Modificados (3 archivos)
```
Core/Backend/
├── core/
│   └── tools_v3/tool_registry.py     # +4 browser tools
└── api/
    └── browser_api.py                # REST endpoints (nuevo)
```

---

## ⚙️ Configuracion

```json
{
  "playwright": {
    "headless": true,
    "browser": "chromium",
    "default_timeout": 30000,
    "viewport": {
      "width": 1920,
      "height": 1080
    }
  },
  "stealth": {
    "enabled": true,
    "random_user_agent": true,
    "hide_webdriver": true
  },
  "limits": {
    "max_concurrent_browsers": 3,
    "max_page_size_mb": 50,
    "rate_limit_per_domain": 10
  }
}
```

---

## 🚀 Plan de Implementacion

| Fase | Tiempo | Tareas |
|------|--------|--------|
| Fase 1 | 8-10h | PlaywrightBrowser, stealth mode, basic ops, tests (10) |
| Fase 2 | 4-6h | BrowserTaskExecutor, WebContentAnalyzer, retry logic, tests (6) |
| Fase 3 | 4-6h | 4 nuevos tools, planner integration, API endpoints, smoke tests (4) |

**Total**: 16-20 horas

---

## 📊 Impacto

### Positivo
- ✅ SPAs funcionan correctamente
- ✅ Screenshots y PDFs
- ✅ Form automation
- ✅ Anti-deteccion built-in

### Riesgos
- ⚠️ Playwright installation (mitigado: requirements.txt)
- ⚠️ Memory usage (mitigado: context pool)
- ⚠️ Sites blocking (mitigado: stealth mode)

---

*Mision creada: 2026-03-26*
*Estado: 📋 Disenada, pendiente de implementacion*
*Prioridad: Media-Alta (capability expansion)*
