/* ═══════════════════════════════════════════════════════════════════════════
   Lilith Dashboard v3.0 — Dark Fantasy / Norse / Lovecraftian Client
   "The void stares back, and it whispers in runes."
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
    particleCount: 35,
    glitchInterval: 12000,
};

// ── State ───────────────────────────────────────────────────────────────────
let ws = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let pingTimer = null;
let statusTimer = null;
let currentLayout = 'grid';
let startTime = Date.now();
let isLilithTyping = false;
let particleCanvas = null;
let particleCtx = null;
let particles = [];
let animFrame = null;

// ── Rune characters for particles ───────────────────────────────────────────
const RUNE_CHARS = ['ᚠ','ᚢ','ᚦ','ᚨ','ᚱ','ᚲ','ᚷ','ᚹ','ᚺ','ᚾ','ᛁ','ᛃ','ᛈ','ᛇ','ᛉ','ᛊ','ᛏ','ᛒ','ᛖ','ᛗ','ᛚ','ᛜ','ᛞ','ᛟ'];
const ELDRITCH_CHARS = ['⌬','⍟','⎔','⎈','⏣','◈','◇','△','▽','☽','☾','⊛','⊕','⊗'];

// ── Particle Canvas System ──────────────────────────────────────────────────
function initParticleCanvas() {
    particleCanvas = document.getElementById('particle-canvas');
    if (!particleCanvas) return;

    particleCtx = particleCanvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Create particles
    for (let i = 0; i < CONFIG.particleCount; i++) {
        particles.push(createParticle());
    }

    animateParticles();
}

function resizeCanvas() {
    if (!particleCanvas) return;
    particleCanvas.width = window.innerWidth;
    particleCanvas.height = window.innerHeight;
}

function createParticle() {
    const isRune = Math.random() > 0.4;
    return {
        x: Math.random() * (particleCanvas ? particleCanvas.width : window.innerWidth),
        y: Math.random() * (particleCanvas ? particleCanvas.height : window.innerHeight),
        char: isRune
            ? RUNE_CHARS[Math.floor(Math.random() * RUNE_CHARS.length)]
            : ELDRITCH_CHARS[Math.floor(Math.random() * ELDRITCH_CHARS.length)],
        size: Math.random() * 10 + 8,
        speed: Math.random() * 0.3 + 0.1,
        opacity: Math.random() * 0.12 + 0.04,
        drift: (Math.random() - 0.5) * 0.3,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.005,
        hue: Math.random() > 0.5 ? 270 : (Math.random() > 0.5 ? 340 : 160), // purple, red, or green
    };
}

function animateParticles() {
    if (!particleCtx || !particleCanvas) return;

    particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);

    particles.forEach(p => {
        // Update position
        p.y -= p.speed;
        p.x += p.drift;
        p.rotation += p.rotationSpeed;

        // Flicker opacity
        const flicker = Math.sin(Date.now() * 0.001 + p.x) * 0.03;
        const alpha = Math.max(0, Math.min(1, p.opacity + flicker));

        // Draw
        particleCtx.save();
        particleCtx.translate(p.x, p.y);
        particleCtx.rotate(p.rotation);
        particleCtx.font = `${p.size}px monospace`;
        particleCtx.fillStyle = `hsla(${p.hue}, 80%, 65%, ${alpha})`;
        particleCtx.shadowColor = `hsla(${p.hue}, 80%, 65%, ${alpha * 2})`;
        particleCtx.shadowBlur = 6;
        particleCtx.textAlign = 'center';
        particleCtx.textBaseline = 'middle';
        particleCtx.fillText(p.char, 0, 0);
        particleCtx.restore();

        // Reset if off screen
        if (p.y < -20) {
            p.y = particleCanvas.height + 20;
            p.x = Math.random() * particleCanvas.width;
        }
        if (p.x < -20) p.x = particleCanvas.width + 20;
        if (p.x > particleCanvas.width + 20) p.x = -20;
    });

    animFrame = requestAnimationFrame(animateParticles);
}

// ── CSS Rune Particles (overlay) ────────────────────────────────────────────
function spawnCSSRunes() {
    const container = document.getElementById('rune-particles');
    if (!container) return;

    const allChars = [...RUNE_CHARS, ...ELDRITCH_CHARS];

    function spawn() {
        const el = document.createElement('span');
        el.className = 'rune-float';
        el.textContent = allChars[Math.floor(Math.random() * allChars.length)];

        const x = Math.random() * 100;
        const size = Math.random() * 8 + 10;
        const duration = Math.random() * 20 + 25;
        const delay = Math.random() * 15;
        const hue = [270, 340, 160, 200][Math.floor(Math.random() * 4)];

        el.style.left = x + '%';
        el.style.fontSize = size + 'px';
        el.style.animationDuration = duration + 's';
        el.style.animationDelay = delay + 's';
        el.style.color = `hsla(${hue}, 70%, 60%, 0.15)`;
        el.style.textShadow = `0 0 6px hsla(${hue}, 70%, 60%, 0.3)`;

        container.appendChild(el);

        // Remove after animation completes
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
            spawn(); // Spawn replacement
        }, (duration + delay) * 1000);
    }

    // Initial batch
    for (let i = 0; i < 12; i++) {
        setTimeout(() => spawn(), Math.random() * 10000);
    }
}

// ── Title Glitch Effect ─────────────────────────────────────────────────────
function initTitleGlitch() {
    const title = document.getElementById('title-lilith');
    if (!title) return;

    function triggerGlitch() {
        title.classList.add('glitch');
        setTimeout(() => title.classList.remove('glitch'), 300);

        // Schedule next glitch
        const nextDelay = CONFIG.glitchInterval + Math.random() * 8000;
        setTimeout(triggerGlitch, nextDelay);
    }

    // First glitch after a few seconds
    setTimeout(triggerGlitch, 3000 + Math.random() * 5000);
}

// ── Typing Indicator ────────────────────────────────────────────────────────
function showTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.remove('hidden');
    }
    isLilithTyping = true;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.classList.add('hidden');
    }
    isLilithTyping = false;
}

// ── WebSocket ───────────────────────────────────────────────────────────────
function connect() {
    const statusDot = document.getElementById('connection-status');
    const statusText = document.getElementById('status-text');
    if (statusDot) statusDot.className = 'status-rune connecting';
    if (statusText) statusText.textContent = 'Summoning...';

    try {
        ws = new WebSocket(CONFIG.wsUrl);
    } catch (e) {
        console.error('[Dashboard] WebSocket creation failed:', e);
        scheduleReconnect();
        return;
    }

    ws.onopen = () => {
        reconnectAttempts = 0;
        if (statusDot) statusDot.className = 'status-rune connected';
        if (statusText) statusText.textContent = 'Bound to the Void';
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
        if (statusDot) statusDot.className = 'status-rune disconnected';
        if (statusText) statusText.textContent = 'Severed';
        console.log('[Dashboard] WebSocket closed');
        hideTypingIndicator();
        stopPing();
        stopStatusUpdates();
        scheduleReconnect();
    };

    ws.onerror = (err) => {
        console.error('[Dashboard] WebSocket error:', err);
        if (statusDot) statusDot.className = 'status-rune disconnected';
        if (statusText) statusText.textContent = 'Void Error';
    };
}

function scheduleReconnect() {
    if (reconnectAttempts >= CONFIG.maxReconnectAttempts) {
        const statusText = document.getElementById('status-text');
        if (statusText) statusText.textContent = 'The Void is Silent';
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
    console.warn('[Dashboard] Not connected, message lost to the void');
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

    if (data.theme) {
        applyTheme(data.theme);
    }

    if (data.layout) {
        applyLayout(data.layout.type || 'grid', data.panes || []);
    }

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

    mainContent.classList.remove('layout-single', 'layout-vertical');

    if (layoutType === 'single') {
        mainContent.classList.add('layout-single');
    } else if (layoutType === 'vertical') {
        mainContent.classList.add('layout-vertical');
    }

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
    showTypingIndicator();
    send({ type: 'chat', message: message });
    input.value = '';
}

function addChatMessage(role, content) {
    hideTypingIndicator();

    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${role}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'msg-role';

    // Role labels with thematic naming
    if (role === 'user') {
        roleLabel.textContent = '▻ MORTAL';
    } else if (role === 'assistant') {
        roleLabel.textContent = '◈ LILITH';
    } else {
        roleLabel.textContent = role.toUpperCase();
    }

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

    addTerminalLine(`᛬ ${command}`, 'input');
    send({ type: 'command', command: command });
    input.value = '';
}

function addTerminalLine(text, type) {
    const container = document.getElementById('terminal-output');
    const line = document.createElement('div');
    line.className = `term-line term-line-${type}`;
    line.textContent = text;

    // Add subtle animation
    line.style.opacity = '0';
    line.style.transform = 'translateY(4px)';
    container.appendChild(line);

    requestAnimationFrame(() => {
        line.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        line.style.opacity = '1';
        line.style.transform = 'translateY(0)';
    });

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
    setText('sys-swarm', data.swarm || 'dormant');
    setText('sys-mcp', data.mcp || 'dormant');
    setText('sys-clients', data.clients_connected || 0);

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
        if (data.active_agents > 0) {
            el.style.textShadow = '0 0 8px #00ff8840';
        }
    }
}

function updateMcpStatus(data) {
    if (!data) return;
    const el = document.getElementById('sys-mcp');
    if (el) {
        el.textContent = `${data.connected || 0} servers`;
        el.style.color = data.connected > 0 ? 'var(--accent-green)' : 'var(--text-dim)';
        if (data.connected > 0) {
            el.style.textShadow = '0 0 8px #00ff8840';
        }
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
        empty.innerHTML = '<span class="mem-key">∅ The archives are silent</span>';
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
        // Silently fail - the void is unreachable
    }
}

function updateStatusBar(data) {
    const right = document.getElementById('statusbar-right');
    if (right && data) {
        const clients = data.clients_connected || 0;
        const msgs = data.chat_messages || 0;
        right.textContent = `⌬ Seekers: ${clients} ᛬ Whispers: ${msgs}`;
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

// ── Visual Enhancements ─────────────────────────────────────────────────────
function addEldritchBorderEffect() {
    // Add subtle pulsing border to active pane at intervals
    setInterval(() => {
        const activePane = document.querySelector('.pane.active');
        if (!activePane) return;
        activePane.style.transition = 'box-shadow 0.5s ease';
    }, 1000);
}

// ── Init ────────────────────────────────────────────────────────────────────
function init() {
    console.log('[Dashboard] Awakening Lilith Dashboard v3.0...');

    // Visual systems
    initParticleCanvas();
    spawnCSSRunes();
    initTitleGlitch();

    // Core functionality
    setupPaneFocus();
    setupKeyboard();
    addChatMessage('system', '⌬ The void stirs... connecting to Lilith ⌬');
    connect();
}

// ── Start ───────────────────────────────────────────────────────────────────
window.addEventListener('load', init);
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
    if (animFrame) cancelAnimationFrame(animFrame);
});
