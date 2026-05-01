/* ═══════════════════════════════════════════════════════════════════════════
   Lilith Dashboard v2.0 — JavaScript Client
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Config ──────────────────────────────────────────────────────────────────
const CONFIG = {
    wsUrl: `ws://${window.location.hostname}:8765`,
    httpUrl: `${window.location.protocol}//${window.location.hostname}:8766`,
    reconnectInterval: 3000,
    maxReconnectAttempts: 10,
    pingInterval: 30000,
    statusUpdateInterval: 5000,
    maxChatMessages: 500,
};

// ── State ───────────────────────────────────────────────────────────────────
let ws = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let pingTimer = null;
let statusTimer = null;
let currentLayout = 'grid';
let startTime = Date.now();

// ── WebSocket ───────────────────────────────────────────────────────────────
function connect() {
    const statusDot = document.getElementById('connection-status');
    const statusText = document.getElementById('status-text');
    statusDot.className = 'status-dot connecting';
    statusText.textContent = 'Connecting...';

    try {
        ws = new WebSocket(CONFIG.wsUrl);
    } catch (e) {
        console.error('[Dashboard] WebSocket creation failed:', e);
        scheduleReconnect();
        return;
    }

    ws.onopen = () => {
        reconnectAttempts = 0;
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Connected';
        console.log('[Dashboard] WebSocket connected');
        startPing();
        startStatusUpdates();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (e) {
            console.error('[Dashboard] Parse error:', e);
        }
    };

    ws.onclose = () => {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = 'Disconnected';
        console.log('[Dashboard] WebSocket closed');
        stopPing();
        stopStatusUpdates();
        scheduleReconnect();
    };

    ws.onerror = (err) => {
        console.error('[Dashboard] WebSocket error:', err);
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = 'Error';
    };
}

function scheduleReconnect() {
    if (reconnectAttempts >= CONFIG.maxReconnectAttempts) {
        document.getElementById('status-text').textContent = 'Max reconnects reached';
        return;
    }
    reconnectAttempts++;
    const delay = Math.min(CONFIG.reconnectInterval * reconnectAttempts, 15000);
    console.log(`[Dashboard] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
    reconnectTimer = setTimeout(connect, delay);
}

function startPing() {
    pingTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
        }
    }, CONFIG.pingInterval);
}

function stopPing() {
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
}

function startStatusUpdates() {
    fetchStatus();
    statusTimer = setInterval(fetchStatus, CONFIG.statusUpdateInterval);
}

function stopStatusUpdates() {
    if (statusTimer) { clearInterval(statusTimer); statusTimer = null; }
}

function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
        return true;
    }
    console.warn('[Dashboard] Not connected, message dropped');
    return false;
}

// ── Message Handler ─────────────────────────────────────────────────────────
function handleMessage(data) {
    switch (data.type) {
        case 'init':
            handleInit(data);
            break;
        case 'chat_response':
            addChatMessage('assistant', data.content || data.message || '');
            break;
        case 'command_result':
            addTerminalLine(data.output || '', 'output');
            break;
        case 'status':
            updateSystemStatus(data.data);
            break;
        case 'swarm_status':
            updateSwarmStatus(data.data);
            break;
        case 'mcp_status':
            updateMcpStatus(data.data);
            break;
        case 'memory_results':
            updateMemoryResults(data.results || []);
            break;
        case 'pong':
            // Heartbeat OK
            break;
        case 'error':
            addChatMessage('error', data.message || 'Unknown error');
            break;
        case 'layout_updated':
            applyLayout(data.layout, data.panes);
            break;
        default:
            console.log('[Dashboard] Unknown message type:', data.type, data);
    }
}

// ── Init ────────────────────────────────────────────────────────────────────
function handleInit(data) {
    console.log('[Dashboard] Init received:', data);

    // Apply theme
    if (data.theme) {
        applyTheme(data.theme);
    }

    // Apply layout
    if (data.layout) {
        applyLayout(data.layout.type || 'grid', data.panes || []);
    }

    // Apply initial status
    if (data.lilith_status) {
        updateSystemStatus(data.lilith_status);
    }
}

function applyTheme(theme) {
    const root = document.documentElement;
    for (const [key, value] of Object.entries(theme)) {
        const cssVar = `--${key.replace(/_/g, '-')}`;
        root.style.setProperty(cssVar, value);
    }
}

function applyLayout(layoutType, panes) {
    currentLayout = layoutType;
    const mainContent = document.getElementById('main-content');

    // Remove all layout classes
    mainContent.classList.remove('layout-single', 'layout-vertical');

    if (layoutType === 'single') {
        mainContent.classList.add('layout-single');
    } else if (layoutType === 'vertical') {
        mainContent.classList.add('layout-vertical');
    }

    // Reorder panes if specified
    if (Array.isArray(panes) && panes.length > 0) {
        const paneMap = {
            'chat': 'pane-chat',
            'terminal': 'pane-terminal',
            'system': 'pane-system',
            'memory': 'pane-memory'
        };
        const ordered = panes.map(p => document.getElementById(paneMap[p])).filter(Boolean);
        ordered.forEach(pane => mainContent.appendChild(pane));
    }
}

// ── Chat ────────────────────────────────────────────────────────────────────
function sendChat() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    addChatMessage('user', message);
    send({ type: 'chat', message: message });
    input.value = '';
}

function addChatMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${role}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'msg-role';
    roleLabel.textContent = role === 'user' ? 'YOU' : role === 'assistant' ? 'LILITH' : role.toUpperCase();

    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.textContent = content;

    msgDiv.appendChild(roleLabel);
    msgDiv.appendChild(contentDiv);
    container.appendChild(msgDiv);

    // Trim old messages
    while (container.children.length > CONFIG.maxChatMessages) {
        container.removeChild(container.firstChild);
    }

    // Auto-scroll
    const chatBody = document.getElementById('chat-body');
    chatBody.scrollTop = chatBody.scrollHeight;
}

// ── Terminal ────────────────────────────────────────────────────────────────
function sendTerminalCommand() {
    const input = document.getElementById('terminal-input');
    const command = input.value.trim();
    if (!command) return;

    addTerminalLine(`$ ${command}`, 'input');
    send({ type: 'command', command: command });
    input.value = '';
}

function addTerminalLine(text, type) {
    const container = document.getElementById('terminal-output');
    const line = document.createElement('div');
    line.className = `term-line term-line-${type}`;
    line.textContent = text;
    container.appendChild(line);

    // Auto-scroll
    const paneBody = container.parentElement;
    paneBody.scrollTop = paneBody.scrollHeight;
}

// ── System Status ───────────────────────────────────────────────────────────
function updateSystemStatus(data) {
    if (!data) return;
    const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) el.textContent = val;
    };

    setText('sys-model', data.model || '---');
    setText('sys-memory', data.memory || '---');
    setText('sys-swarm', data.swarm || 'inactive');
    setText('sys-mcp', data.mcp || 'inactive');
    setText('sys-clients', data.clients_connected || 0);

    // Uptime
    if (data.uptime) {
        const mins = Math.floor(data.uptime / 60);
        setText('sys-uptime', mins > 60 ? `${Math.floor(mins/60)}h ${mins%60}m` : `${mins}m`);
    } else {
        const elapsed = Math.floor((Date.now() - startTime) / 60000);
        setText('sys-uptime', `${elapsed}m`);
    }
}

function updateSwarmStatus(data) {
    if (!data) return;
    const el = document.getElementById('sys-swarm');
    if (el) {
        el.textContent = `${data.active_agents || 0}/${data.max_agents || 5} agents`;
        el.style.color = data.active_agents > 0 ? 'var(--accent-green)' : 'var(--text-dim)';
    }
}

function updateMcpStatus(data) {
    if (!data) return;
    const el = document.getElementById('sys-mcp');
    if (el) {
        el.textContent = `${data.connected || 0} servers`;
        el.style.color = data.connected > 0 ? 'var(--accent-green)' : 'var(--text-dim)';
    }
}

// ── Memory Search ───────────────────────────────────────────────────────────
function searchMemory(query) {
    if (!query || query.length < 2) return;
    send({ type: 'memory_search', query: query });
}

function updateMemoryResults(results) {
    const container = document.getElementById('memory-results');
    container.innerHTML = '';

    if (!results || results.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'memory-item';
        empty.innerHTML = '<span class="mem-key">No results</span>';
        container.appendChild(empty);
        return;
    }

    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'memory-item';
        div.innerHTML = `
            <span class="mem-key">${escapeHtml(item.key || item.id || '?')}</span>
            <div class="mem-value">${escapeHtml(item.content || item.value || '')}</div>
        `;
        container.appendChild(div);
    });
}

// ── Status Updates ──────────────────────────────────────────────────────────
async function fetchStatus() {
    try {
        const resp = await fetch(`${CONFIG.httpUrl}/api/status`);
        if (resp.ok) {
            const data = await resp.json();
            updateSystemStatus(data);
            updateStatusBar(data);
        }
    } catch (e) {
        // Silently fail - server may not be up yet
    }
}

function updateStatusBar(data) {
    const right = document.getElementById('statusbar-right');
    if (right && data) {
        const clients = data.clients_connected || 0;
        const msgs = data.chat_messages || 0;
        right.textContent = `Clients: ${clients} | Messages: ${msgs}`;
    }
}

// ── Layout Toggle ───────────────────────────────────────────────────────────
function toggleLayout() {
    const mainContent = document.getElementById('main-content');
    if (currentLayout === 'grid') {
        applyLayout('vertical', null);
    } else if (currentLayout === 'vertical') {
        applyLayout('single', null);
    } else {
        applyLayout('grid', null);
    }
    send({ type: 'set_layout', layout: currentLayout });
}

// ── Settings ────────────────────────────────────────────────────────────────
function toggleSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.toggle('hidden');
}

// ── Utilities ────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Pane Focus ──────────────────────────────────────────────────────────────
function setupPaneFocus() {
    document.querySelectorAll('.pane').forEach(pane => {
        pane.addEventListener('click', () => {
            document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
            pane.classList.add('active');
        });
    });
}

// ── Keyboard Shortcuts ──────────────────────────────────────────────────────
function setupKeyboard() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter: send chat
        if (e.ctrlKey && e.key === 'Enter') {
            const chatInput = document.getElementById('chat-input');
            if (document.activeElement === chatInput) {
                sendChat();
                e.preventDefault();
            }
        }

        // Escape: close modals
        if (e.key === 'Escape') {
            const modal = document.getElementById('settings-modal');
            if (!modal.classList.contains('hidden')) {
                toggleSettings();
            }
        }

        // Ctrl+1/2/3/4: focus pane
        if (e.ctrlKey && e.key >= '1' && e.key <= '4') {
            const panes = ['pane-chat', 'pane-terminal', 'pane-system', 'pane-memory'];
            const idx = parseInt(e.key) - 1;
            const pane = document.getElementById(panes[idx]);
            if (pane) {
                const input = pane.querySelector('input');
                if (input) input.focus();
                pane.click();
            }
            e.preventDefault();
        }
    });

    // Chat input: Enter to send
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            sendChat();
            e.preventDefault();
        }
    });

    // Terminal input: Enter to send
    document.getElementById('terminal-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendTerminalCommand();
            e.preventDefault();
        }
    });

    // Memory search: Enter to search (debounced)
    let memoryDebounce = null;
    document.getElementById('memory-search-input').addEventListener('input', (e) => {
        clearTimeout(memoryDebounce);
        memoryDebounce = setTimeout(() => searchMemory(e.target.value), 500);
    });
}

// ── Init ────────────────────────────────────────────────────────────────────
function init() {
    console.log('[Dashboard] Initializing Lilith Dashboard v2.0...');
    setupPaneFocus();
    setupKeyboard();
    addChatMessage('system', 'Connecting to Lilith...');
    connect();
}

// ── Start ───────────────────────────────────────────────────────────────────
window.addEventListener('load', init);
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
});
