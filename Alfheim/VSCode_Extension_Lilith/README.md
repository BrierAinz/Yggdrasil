# Lilith Assistant — VS Code Extension

Integra el servidor Lilith AI directamente en VS Code / Cursor.

## Comando (V1)

- **`Lilith: Preguntar (selección/archivo)`**
  - Disponible en **menú contextual** del editor (clic derecho).
  - Pide un prompt (InputBox) y envía a la API:
    - `prompt`, `selection`, `file_path`, `language_id`, `workspace_name`
  - Muestra la respuesta en un **Webview**.

## Configuración

```json
{
  "lilith.serverUrl": "http://localhost:8000",
  "lilith.vscodeToken": "PON_AQUI_TU_LILITH_VSCODE_TOKEN"
}
```

## Desarrollo

```bash
npm install
npm run compile
# Presiona F5 en VS Code para lanzar la extensión en modo desarrollo
```

## Backend (API)

- Endpoint: `POST /api/vscode/ask`
- Auth: header `X-Lilith-VSCode-Token` == `LILITH_VSCODE_TOKEN`
