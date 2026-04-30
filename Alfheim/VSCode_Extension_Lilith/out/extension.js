"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const https = __importStar(require("https"));
const http = __importStar(require("http"));
const url_1 = require("url");
function postJson(url, body, headers, timeoutMs = 120000) {
    return new Promise((resolve, reject) => {
        const parsed = new url_1.URL(url);
        const data = JSON.stringify(body);
        const isHttps = parsed.protocol === 'https:';
        const transport = isHttps ? https : http;
        const options = {
            hostname: parsed.hostname,
            port: parsed.port || (isHttps ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data),
                ...headers,
            },
        };
        const req = transport.request(options, (res) => {
            let raw = '';
            res.on('data', (chunk) => (raw += chunk));
            res.on('end', () => {
                try {
                    resolve(JSON.parse(raw));
                }
                catch {
                    reject(new Error(`Respuesta no-JSON (${res.statusCode}): ${raw.slice(0, 200)}`));
                }
            });
        });
        req.setTimeout(timeoutMs, () => {
            req.destroy();
            reject(new Error('Timeout: Lilith no respondió en 2 minutos'));
        });
        req.on('error', reject);
        req.write(data);
        req.end();
    });
}
let panel;
function getOrCreatePanel(ctx) {
    if (panel) {
        panel.reveal(vscode.ViewColumn.Beside);
        return panel;
    }
    panel = vscode.window.createWebviewPanel('lilithResponse', 'Lilith ✦', vscode.ViewColumn.Beside, { enableScripts: false, retainContextWhenHidden: true });
    panel.onDidDispose(() => { panel = undefined; }, null, ctx.subscriptions);
    return panel;
}
function stripCodeFences(text) {
    return (text || '')
        .replace(/^```[\w]*\s*\n?/, '')
        .replace(/\n?```$/, '')
        .trim();
}
function buildHtml(p, prompt, response, meta) {
    const nonce = Math.random().toString(36).slice(2);
    const csp = p.webview.cspSource;
    const color = '#c9a227';
    const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const renderMarkdown = (text) => {
        let html = escapeHtml(text);
        html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang, code) => `<pre><code class="lang-${lang || 'text'}">${code}</code></pre>`);
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\n/g, '<br>');
        return html;
    };
    const infoParts = [
        meta.workspaceName ? `Workspace: <strong>${escapeHtml(meta.workspaceName)}</strong>` : '',
        meta.filePath ? `Archivo: <strong>${escapeHtml(meta.filePath)}</strong>` : '',
        meta.languageId ? `Lenguaje: <strong>${escapeHtml(meta.languageId)}</strong>` : '',
    ].filter(Boolean);
    const infoLine = infoParts.length ? infoParts.join(' · ') : 'Contexto: (no disponible)';
    return /* html */ `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'nonce-${nonce}'; img-src ${csp} data:;">
  <style nonce="${nonce}">
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0a0a0f; color: #e8e0d0; font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px; line-height: 1.6; }
    .header { background: linear-gradient(135deg, #12121a 0%, #1a1a26 100%); border-bottom: 2px solid ${color}; padding: 14px 18px; display: flex; align-items: center; gap: 10px; }
    .crown { font-size: 20px; }
    .header-text h2 { color: ${color}; font-size: 14px; font-weight: 700; letter-spacing: 1px; }
    .header-text p { color: #8a8090; font-size: 11px; margin-top: 2px; }
    .body { padding: 16px 18px; }
    .section { margin-bottom: 20px; }
    .section h3 { color: ${color}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid rgba(201,162,39,0.15); }
    .message-box { background: #111118; border: 1px solid rgba(201,162,39,0.15); border-radius: 6px; padding: 14px; }
    .message-box pre { background: #0a0a12; border: 1px solid rgba(255,255,255,0.06); border-radius: 4px; padding: 10px 12px; overflow-x: auto; margin: 8px 0; }
    .message-box code { font-family: 'JetBrains Mono', 'Cascadia Code', 'Courier New', monospace; font-size: 12px; color: #b8d4f8; }
    .message-box strong { color: #f0e8c8; }
  </style>
</head>
<body>
  <div class="header">
    <span class="crown">👑</span>
    <div class="header-text">
      <h2>Pregunta a Lilith</h2>
      <p>${infoLine}</p>
    </div>
  </div>
  <div class="body">
    <div class="section">
      <h3>Prompt</h3>
      <div class="message-box">${renderMarkdown(prompt)}</div>
    </div>
    <div class="section">
      <h3>Respuesta</h3>
      <div class="message-box">${renderMarkdown(response)}</div>
    </div>
  </div>
</body>
</html>`;
}
async function callLilithAPI(payload) {
    const cfg = vscode.workspace.getConfiguration('lilith');
    const serverUrl = cfg.get('serverUrl', 'http://localhost:8000');
    const token = (cfg.get('vscodeToken', '') || '').trim();
    if (!token) {
        vscode.window.showErrorMessage('Lilith: configura lilith.vscodeToken (LILITH_VSCODE_TOKEN) en settings.');
        return null;
    }
    try {
        const headers = { 'X-Lilith-VSCode-Token': token };
        const result = await postJson(`${serverUrl}/api/vscode/ask`, payload, headers);
        return (result.response || '').trim() || null;
    }
    catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`Lilith: ${msg}`);
        return null;
    }
}
async function runAskCommand(ctx) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('Lilith: abre un archivo primero.');
        return;
    }
    const doc = editor.document;
    const selection = editor.selection;
    const selected = selection.isEmpty ? '' : doc.getText(selection);
    const filePath = vscode.workspace.asRelativePath(doc.uri) || '';
    const languageId = doc.languageId || '';
    const workspaceName = vscode.workspace.name || '';
    const prompt = await vscode.window.showInputBox({
        title: 'Lilith: Pregunta (V1)',
        prompt: 'Escribe tu pregunta. Se enviará junto a la selección (si existe).',
        placeHolder: 'Ej: “Explícame esta función y dame 2 mejoras seguras.”',
        ignoreFocusOut: true,
        validateInput: (v) => (v.trim().length < 2 ? 'Escribe al menos 2 caracteres.' : null),
    });
    if (!prompt) {
        return;
    }
    const p = getOrCreatePanel(ctx);
    p.webview.html = /* html */ `<!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>body{background:#0a0a0f;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;}
    .s{color:#c9a227;text-align:center;} .i{font-size:32px;display:block;animation:spin 1s linear infinite;}
    @keyframes spin{to{transform:rotate(360deg);}}</style></head>
    <body><div class="s"><span class="i">⚙</span><br>Consultando a Lilith…</div></body></html>`;
    const response = await callLilithAPI({
        prompt: prompt.trim(),
        selection: selected,
        file_path: filePath,
        language_id: languageId,
        workspace_name: workspaceName,
    });
    if (!response) {
        return;
    }
    p.webview.html = buildHtml(p, prompt.trim(), response, {
        workspaceName,
        filePath,
        languageId,
    });
}
function activate(ctx) {
    ctx.subscriptions.push(vscode.commands.registerCommand('lilith.ask', () => runAskCommand(ctx)));
    // Inline suggestions (V2)
    const inlineProvider = {
        async provideInlineCompletionItems(document, position, _context, _token) {
            const editor = vscode.window.activeTextEditor;
            if (!editor)
                return [];
            const selection = editor.selection;
            const selectedText = document.getText(selection.isEmpty
                ? new vscode.Range(Math.max(0, position.line - 10), 0, position.line, position.character)
                : selection);
            if (!selectedText.trim())
                return [];
            const resp = await callLilithAPI({
                prompt: 'Completa o mejora este código. Devuelve SOLO el código, sin explicación.',
                selection: selectedText,
                file_path: document.fileName,
                language_id: document.languageId,
                workspace_name: vscode.workspace.name || '',
            });
            if (!resp)
                return [];
            const range = selection.isEmpty
                ? new vscode.Range(position, position)
                : selection;
            return [new vscode.InlineCompletionItem(resp, range)];
        },
    };
    ctx.subscriptions.push(vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, inlineProvider));
    // Apply patch command
    const applyPatch = vscode.commands.registerCommand('lilith.applyPatch', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor)
            return;
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        if (!selectedText.trim()) {
            vscode.window.showWarningMessage('Selecciona el código a reemplazar primero.');
            return;
        }
        const prompt = await vscode.window.showInputBox({
            prompt: 'Instrucción para Lilith (ej: "refactoriza", "añade tipos", "corrige el bug")',
            placeHolder: 'Qué quieres que haga Lilith con esta selección...',
        });
        if (!prompt)
            return;
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Lilith pensando...',
        }, async () => {
            const resp = await callLilithAPI({
                prompt: `${prompt}. Devuelve SOLO el bloque de código corregido, sin explicación ni markdown.`,
                selection: selectedText,
                file_path: editor.document.fileName,
                language_id: editor.document.languageId,
                workspace_name: vscode.workspace.name || '',
            });
            if (!resp)
                return;
            const clean = stripCodeFences(resp);
            // Mostrar diff visual antes de aplicar (V3)
            const lang = editor.document.languageId;
            const left = await vscode.workspace.openTextDocument({ content: selectedText, language: lang });
            const right = await vscode.workspace.openTextDocument({ content: clean, language: lang });
            const title = `Lilith Diff: ${prompt.trim().slice(0, 60)}`;
            await vscode.commands.executeCommand('vscode.diff', left.uri, right.uri, title);
            const choice = await vscode.window.showInformationMessage('¿Aplicar este parche sobre tu selección?', { modal: true }, 'Aplicar', 'Cancelar');
            if (choice !== 'Aplicar') {
                return;
            }
            await editor.edit((editBuilder) => {
                editBuilder.replace(selection, clean);
            });
            vscode.window.showInformationMessage('Lilith aplicó el parche.');
        });
    });
    ctx.subscriptions.push(applyPatch);
    vscode.window.showInformationMessage('Lilith Assistant activada (V2: inline + patch) ✦');
}
function deactivate() { }
//# sourceMappingURL=extension.js.map
