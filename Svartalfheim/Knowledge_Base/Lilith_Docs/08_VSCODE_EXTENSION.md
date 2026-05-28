# 08 - Extensión VS Code

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/VSCode/`

---

## 8.1 Estructura

```
VSCode/
├── package.json              # Manifest
├── tsconfig.json             # TypeScript config
├── README.md
├── src/
│   └── extension.ts          # Código principal (345 líneas)
├── out/
│   ├── extension.js          # Compilado
│   └── extension.js.map
└── lilith-assistant-0.1.0.vsix  # Paquete
```

### Tecnologías

| Tecnología | Versión |
|------------|---------|
| TypeScript | 5.3 |
| VSCode API | ^1.80.0 |
| Target | ES2020 / CommonJS |

---

## 8.2 package.json - Contribuciones

### Información Básica

| Campo | Valor |
|-------|-------|
| Nombre | `lilith-assistant` |
| Versión | `0.1.0` |
| Publisher | `lilith-ai` |
| Categorías | AI, Other |
| Activation | `onStartupFinished` |

### Comandos

```json
"contributes.commands": [
  {
    "command": "lilith.ask",
    "title": "Lilith: Preguntar (selección/archivo)"
  },
  {
    "command": "lilith.applyPatch",
    "title": "Lilith: Aplicar parche en selección"
  }
]
```

### Menús Contextuales

```json
"contributes.menus.editor/context": [
  {
    "command": "lilith.ask",
    "group": "lilith@1",
    "when": "editorTextFocus"
  },
  {
    "command": "lilith.applyPatch",
    "group": "lilith@2",
    "when": "editorHasSelection"
  }
]
```

### Configuración

```json
"contributes.configuration": {
  "properties": {
    "lilith.serverUrl": {
      "type": "string",
      "default": "http://localhost:8000",
      "description": "URL del servidor Lilith"
    },
    "lilith.vscodeToken": {
      "type": "string",
      "default": "",
      "description": "Token de autenticación"
    }
  }
}
```

---

## 8.3 Integración con Lilith Core

### Flujo de Comunicación

```
┌─────────────────┐      HTTP POST      ┌─────────────────┐
│   VSCode Ext    │ ───────────────────>│   Lilith Core   │
│   (extensión)   │  /api/vscode/ask    │   (FastAPI)     │
└─────────────────┘                     └─────────────────┘
      │                                          │
      │         ┌─────────────────┐             │
      └────────>│  vscode_api.py  │<────────────┘
                │  (Router API)   │
                └─────────────────┘
```

### Backend: vscode_api.py

**Endpoint:** `POST /api/vscode/ask`

**Autenticación:**
```
Header: X-Lilith-VSCode-Token
Value:  {LILITH_VSCODE_TOKEN env var}
```

**Request Schema:**
```typescript
interface VSCodeAskRequest {
  prompt: string;           // Requerido, max 4000 chars
  selection?: string;       // Opcional, max 120k chars
  file_path?: string;       // Opcional, max 400 chars
  language_id?: string;     // Opcional, max 400 chars
  workspace_name?: string;  // Opcional, max 400 chars
}
```

**Response Schema:**
```typescript
interface VSCodeAskResponse {
  response: string;
}
```

**Contexto enviado:**
```
Eres Lilith en modo desarrollador para VS Code.
Responde en español, directo y accionable.
Si falta contexto, pide el mínimo imprescindible.
Si incluyes código, mantenlo corto y enfocado.

Workspace: {workspace_name}
Archivo: {file_path}
Lenguaje: {language_id}
Selección:
``` {selection} ```
```

---

## 8.4 Comandos

### 8.4.1 `lilith.ask` - Preguntar a Lilith

**Funcionalidad:** Envía pregunta con contexto del archivo/selección.

**Flujo:**
1. Obtiene editor activo
2. Recopila: selección, ruta, languageId, workspace
3. Muestra input box para prompt
4. Muestra webview con spinner
5. Envía POST a `/api/vscode/ask`
6. Muestra respuesta en webview

**Webview Features:**
- Tema oscuro (#0a0a0f)
- Acentos dorados (#c9a227)
- Renderizado Markdown básico
- CSP implementado
- Retiene contexto

### 8.4.2 `lilith.applyPatch` - Aplicar Parche

**Funcionalidad:** Refactoriza código seleccionado.

**Flujo:**
1. Requiere selección activa
2. Pide instrucción al usuario
3. Envía a Lilith con prompt especial
4. Muestra diff visual (`vscode.diff`)
5. Pide confirmación modal
6. Aplica reemplazo

**Prompt especial:**
```
{instrucción}. Devuelve SOLO el bloque de código corregido, 
sin explicación ni markdown.
```

---

## 8.5 Configuración

### settings.json

```json
{
  "lilith.serverUrl": "http://localhost:8000",
  "lilith.vscodeToken": "tu_token_aqui"
}
```

### Variables de Entorno (Lilith Core)

| Variable | Descripción |
|----------|-------------|
| `LILITH_VSCODE_TOKEN` | Token secreto para autenticar |

---

## 8.6 Inline Completions (Ghost Text)

Registra `InlineCompletionItemProvider` global:

```typescript
vscode.languages.registerInlineCompletionItemProvider(
  { pattern: '**' },
  inlineProvider
);
```

**Comportamiento:**
- Actúa en cualquier archivo
- Toma últimas 10 líneas o selección
- Solicita a Lilith completar/mejorar
- Muestra sugerencias inline

---

## 8.7 Estilos Visuales

```css
Color primario:     #c9a227 (Dorado)
Fondo principal:    #0a0a0f (Negro azulado)
Fondo secundario:   #111118 (Gris oscuro)
Texto principal:    #e8e0d0 (Beige claro)
Texto secundario:   #8a8090 (Gris púrpura)
Código:             #b8d4f8 (Azul claro)
```

---

## 8.8 Funciones Utilitarias

| Función | Descripción |
|---------|-------------|
| `postJson<T>()` | Cliente HTTP (timeout 2 min) |
| `stripCodeFences()` | Elimina ``` del código |
| `buildHtml()` | Genera HTML del webview |
| `getOrCreatePanel()` | Singleton webview |

---

## 8.9 Scripts de Build

```json
{
  "compile": "tsc -p ./",
  "watch": "tsc -watch -p ./",
  "lint": "eslint src --ext ts"
}
```

---

## 8.10 Resumen de Capacidades

| Versión | Feature | Estado |
|---------|---------|--------|
| V1 | Comando `ask` con webview | ✅ |
| V2 | Inline completions | ✅ |
| V2 | Comando `applyPatch` | ✅ |
| V2 | Diff visual antes de aplicar | ✅ |
| V2 | Autenticación por token | ✅ |
| V2 | Soporte HTTPS/HTTP | ✅ |

---

*Documento 08 del índice de documentación de Lilith*
