/* ═══════════════════════════════════════════════════════════════════════════
   Lilith Dashboard v3.0 — ULTRA-PREMIUM Dark Fantasy / Norse / Lovecraftian Client
   "From the abyss between the stars, the old runes still pulse."
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
    particleCount: 45,
    glitchInterval: 12000,
    trailParticles: true,
    eldritchEffects: true,
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
let mouseX = 0;
let mouseY = 0;
let trailTimer = null;

// ── Rune characters for particles ───────────────────────────────────────────
const RUNE_CHARS = ['ᚠ','ᚢ','ᚦ','ᚨ','ᚱ','ᚲ','ᚷ','ᚹ','ᚺ','ᚾ','ᛁ','ᛃ','ᛈ','ᛇ','ᛉ','ᛊ','ᛏ','ᛒ','ᛖ','ᛗ','ᛚ','ᛜ','ᛞ','ᛟ'];
const ELDRITCH_CHARS = ['⌬','⍟','⎔','⎈','⏣','◈','◇','△','▽','☽','☾','⊛','⊕','⊗','⏢','⍙','⌘','⎋'];
const ELDRITCH_SYMBOLS = ['᛭','✦','✧','⟡','⟐','⬡','⬢','◈'];

// ── Mouse tracking for interactive effects ──────────────────────────────────
document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;

    // Cursor trail particles
    if (CONFIG.trailParticles && Math.random() > 0.7) {
        spawnTrailParticle(e.clientX, e.clientY);
    }
});

function spawnTrailParticle(x, y) {
    const el = document.createElement('div');
    el.className = 'cursor-trail';
    el.style.left = (x - 3 + (Math.random() - 0.5) * 10) + 'px';
    el.style.top = (y - 3 + (Math.random() - 0.5) * 10) + 'px';
    const hue = [270, 340, 190][Math.floor(Math.random() * 3)];
    el.style.background = `hsla(${hue}, 80%, 60%, 0.6)`;
    el.style.boxShadow = `0 0 6px hsla(${hue}, 80%, 60%, 0.4)`;
    document.body.appendChild(el);
    setTimeout(() => {
        if (el.parentNode) el.parentNode.removeChild(el);
    }, 800);
}

// ── Particle Canvas System (Enhanced) ──────────────────────────────────────
function initParticleCanvas() {
    particleCanvas = document.getElementById('particle-canvas');
    if (!particleCanvas) return;

    particleCtx = particleCanvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Create particles with varied types
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

function createParticle(forceJustCreated) {
    const type = Math.random();
    let char, hue, behavior;

    if (type < 0.5) {
        // Rune characters - Norse
        char = RUNE_CHARS[Math.floor(Math.random() * RUNE_CHARS.length)];
        hue = Math.random() > 0.5 ? 270 : 340; // purple or red
        behavior = 'drift';
    } else if (type < 0.8) {
        // Eldritch symbols - Lovecraftian
        char = ELDRITCH_CHARS[Math.floor(Math.random() * ELDRITCH_CHARS.length)];
        hue = Math.random() > 0.5 ? 300 : 190; // magenta or cyan
        behavior = 'pulse';
    } else {
        // Tiny stars/dots
        char = ELDRITCH_SYMBOLS[Math.floor(Math.random() * ELDRITCH_SYMBOLS.length)];
        hue = 45; // gold
        behavior = 'twinkle';
    }

    return {
        x: Math.random() * (particleCanvas ? particleCanvas.width : window.innerWidth),
        y: Math.random() * (particleCanvas ? particleCanvas.height : window.innerHeight),
        char: char,
        size: behavior === 'twinkle' ? Math.random() * 6 + 4 : Math.random() * 10 + 8,
        speed: Math.random() * 0.35 + 0.08,
        opacity: Math.random() * 0.12 + 0.03,
        maxOpacity: Math.random() * 0.18 + 0.06,
        drift: (Math.random() - 0.5) * 0.3,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.008,
        hue: hue,
        behavior: behavior,
        phase: Math.random() * Math.PI * 2, // for pulsing
        justCreated: forceJustCreated || false,
        life: forceJustCreated ? 0 : 1,
    };
}

function animateParticles() {
    if (!particleCtx || !particleCanvas) return;

    // Semi-transparent clear for trails effect
    particleCtx.fillStyle = 'rgba(5, 5, 16, 0.15)';
    particleCtx.fillRect(0, 0, particleCanvas.width, particleCanvas.height);

    const time = Date.now() * 0.001;
    const mouseInfluenceRadius = 150;

    particles.forEach(p => {
        // Mouse repulsion
        const dx = p.x - mouseX;
        const dy = p.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < mouseInfluenceRadius && dist > 0) {
            const force = (mouseInfluenceRadius - dist) / mouseInfluenceRadius * 0.5;
            p.x += (dx / dist) * force;
            p.y += (dy / dist) * force;
        }

        // Behavior-specific updates
        let alpha = p.opacity;

        if (p.behavior === 'pulse') {
            alpha = p.maxOpacity * (0.5 + 0.5 * Math.sin(time * 1.5 + p.phase));
        } else if (p.behavior === 'twinkle') {
            alpha = p.maxOpacity * (0.3 + 0.7 * Math.pow(Math.sin(time * 2 + p.phase), 2));
        } else {
            // Drift - with subtle flicker
            const flicker = Math.sin(time * 0.7 + p.x * 0.01) * 0.04;
            alpha = Math.max(0, Math.min(1, p.opacity + flicker));
        }

        // Fade in newly created particles
        if (p.justCreated) {
            p.life = Math.min(1, p.life + 0.01);
            alpha *= p.life;
            if (p.life >= 1) p.justCreated = false;
        }

        // Update position
        p.y -= p.speed;
        p.x += p.drift;
        p.rotation += p.rotationSpeed;

        // Draw with glow
        particleCtx.save();
        particleCtx.translate(p.x, p.y);
        particleCtx.rotate(p.rotation);
        particleCtx.font = `${p.size}px monospace`;
        particleCtx.fillStyle = `hsla(${p.hue}, 80%, 65%, ${alpha})`;
        particleCtx.shadowColor = `hsla(${p.hue}, 80%, 65%, ${alpha * 2})`;
        particleCtx.shadowBlur = p.behavior === 'twinkle' ? 12 : 8;
        particleCtx.textAlign = 'center';
        particleCtx.textBaseline = 'middle';
        particleCtx.fillText(p.char, 0, 0);

        // Extra glow layer for pulsing particles
        if (p.behavior === 'pulse') {
            particleCtx.shadowBlur = 16;
            particleCtx.fillStyle = `hsla(${p.hue}, 80%, 65%, ${alpha * 0.3})`;
            particleCtx.fillText(p.char, 0, 0);
        }

        particleCtx.restore();

        // Reset if off screen
        if (p.y < -30) {
            p.y = particleCanvas.height + 30;
            p.x = Math.random() * particleCanvas.width;
        }
        if (p.x < -30) p.x = particleCanvas.width + 30;
        if (p.x > particleCanvas.width + 30) p.x = -30;
    });

    // Occasional shooting rune
    if (Math.random() < 0.002) {
        spawnShootingRune();
    }

    animFrame = requestAnimationFrame(animateParticles);
}

function spawnShootingRune() {
    const startX = Math.random() * particleCanvas.width;
    const startY = Math.random() * particleCanvas.height * 0.3;
    const rune = RUNE_CHARS[Math.floor(Math.random() * RUNE_CHARS.length)];

    let frame = 0;
    const maxFrames = 30;
    const targetX = startX + (Math.random() - 0.5) * 400;
    const targetY = startY + 200 + Math.random() * 300;

    function drawFrame() {
        if (!particleCtx || frame >= maxFrames) return;
        const progress = frame / maxFrames;
        const alpha = Math.sin(progress * Math.PI) * 0.5;

        const x = startX + (targetX - startX) * progress;
        const y = startY + (targetY - startY) * progress;

        particleCtx.save();
        particleCtx.font = '14px monospace';
        particleCtx.fillStyle = `hsla(45, 100%, 70%, ${alpha})`;
        particleCtx.shadowColor = `hsla(45, 100%, 70%, ${alpha * 2})`;
        particleCtx.shadowBlur = 20;
        particleCtx.textAlign = 'center';
        particleCtx.textBaseline = 'middle';
        particleCtx.fillText(rune, x, y);
        particleCtx.restore();

        frame++;
        requestAnimationFrame(drawFrame);
    }

    drawFrame();
}

// ── CSS Rune Particles (overlay - enhanced) ──────────────────────────────────
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
        const duration = Math.random() * 25 + 20;
        const delay = Math.random() * 15;
        const hue = [270, 340, 160, 200, 45][Math.floor(Math.random() * 5)];

        el.style.left = x + '%';
        el.style.fontSize = size + 'px';
        el.style.animationDuration = duration + 's';
        el.style.animationDelay = delay + 's';
        el.style.color = `hsla(${hue}, 70%, 60%, 0.15)`;
        el.style.textShadow = `0 0 8px hsla(${hue}, 70%, 60%, 0.3), 0 0 16px hsla(${hue}, 70%, 60%, 0.15)`;

        container.appendChild(el);

        // Remove after animation completes
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
            spawn(); // Spawn replacement
        }, (duration + delay) * 1000);
    }

    // Initial batch
    for (let i = 0; i < 15; i++) {
        setTimeout(() => spawn(), Math.random() * 12000);
    }
}

// ── Title Glitch Effect (Enhanced) ──────────────────────────────────────────
function initTitleGlitch() {
    const title = document.getElementById('title-lilith');
    if (!title) return;

    // Store original text for recovery
    const originalText = title.textContent || 'LILITH';

    // Glitch character set
    const glitchChars = '᛭⌬⍟⎔ᚠᚢᚦᚨᚱᚲᚹᚺᛁᛊᛏᛖᛗᛚᛞᛟ∎⊕⊗⏢';

    function triggerGlitch() {
        // Phase 1: Rapid glitch
        let glitchCount = 0;
        const maxGlitches = 3;

        function applyGlitch() {
            if (glitchCount >= maxGlitches) {
                // Recovery
                title.classList.add('glitch');
                setTimeout(() => {
                    title.classList.remove('glitch');
                    title.textContent = originalText;
                }, 200);
                return;
            }

            // Partial corruption
            let text = originalText.split('');
            const corruptIdx = Math.floor(Math.random() * text.length);
            text[corruptIdx] = glitchChars[Math.floor(Math.random() * glitchChars.length)];
            title.textContent = text.join('');

            glitchCount++;
            setTimeout(applyGlitch, 60 + Math.random() * 80);
        }

        applyGlitch();

        // Schedule next glitch
        const nextDelay = CONFIG.glitchInterval + Math.random() * 10000;
        setTimeout(triggerGlitch, nextDelay);
    }

    // First glitch after a few seconds
    setTimeout(triggerGlitch, 3000 + Math.random() * 5000);

    // Set data attribute for CSS
    title.dataset.original = originalText;
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

        // Visual pulse effect on connect
        const header = document.getElementById('header');
        if (header) {
            header.style.boxShadow = '0 0 30px #00ff8830, inset 0 0 20px #00ff8810';
            setTimeout(() => { header.style.boxShadow = ''; }, 1000);
        }

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

        // Visual shock effect on disconnect
        const header = document.getElementById('header');
        if (header) {
            header.style.boxShadow = '0 0 30px #ff336630, inset 0 0 20px #ff336610';
            setTimeout(() => { header.style.boxShadow = ''; }, 1500);
        }

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

    // Auto-scroll with smooth behavior
    const chatBody = document.getElementById('chat-body');
    chatBody.scrollTo({
        top: chatBody.scrollHeight,
        behavior: 'smooth'
    });
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

    // Add eldritch reveal animation
    line.style.opacity = '0';
    line.style.transform = 'translateY(4px)';
    line.style.filter = 'blur(2px)';
    container.appendChild(line);

    requestAnimationFrame(() => {
        line.style.transition = 'opacity 0.3s ease, transform 0.3s ease, filter 0.3s ease';
        line.style.opacity = '1';
        line.style.transform = 'translateY(0)';
        line.style.filter = 'blur(0)';
    });

    // Auto-scroll
    const paneBody = container.parentElement;
    paneBody.scrollTo({
        top: paneBody.scrollHeight,
        behavior: 'smooth'
    });
}

// ── System Status ───────────────────────────────────────────────────────────
function updateSystemStatus(data) {
    if (!data) return;
    const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) {
            // Animated value update with glow effect
            if (el.textContent !== String(val)) {
                el.textContent = val;
                el.style.textShadow = '0 0 20px #00eeff60, 0 0 40px #00eeff30';
                setTimeout(() => {
                    el.style.textShadow = '';
                }, 500);
            }
        }
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
            el.style.textShadow = '0 0 8px #00ff8840, 0 0 16px #00ff8820';
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
            el.style.textShadow = '0 0 8px #00ff8840, 0 0 16px #00ff8820';
        }
    }
}

// ── Memory Search ────────────────────────────────────────────────────────────
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

    results.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'memory-item';
        div.style.animationDelay = `${idx * 0.05}s`;
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

// ── Layout Toggle ────────────────────────────────────────────────────────────
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

// ── Settings ──────────────────────────────────────────────────────────────────
function toggleSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.toggle('hidden');
}

// ── Utilities ──────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Pane Focus (Enhanced) ──────────────────────────────────────────────────────
function setupPaneFocus() {
    document.querySelectorAll('.pane').forEach(pane => {
        pane.addEventListener('click', () => {
            document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
            pane.classList.add('active');

            // Ripple effect on focus
            pane.style.boxShadow = '0 0 30px #ff336640, inset 0 0 20px #ff336615';
            setTimeout(() => {
                // Allow the animation class to take over
                pane.style.boxShadow = '';
            }, 400);
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

// ── Visual Enhancements ────────────────────────────────────────────────────
function addEldritchBorderEffect() {
    // Pulse active pane border with eldritch energy
    setInterval(() => {
        const activePane = document.querySelector('.pane.active');
        if (!activePane) return;

        // Occasional "power surge" effect
        if (Math.random() < 0.1) {
            activePane.style.borderColor = 'var(--accent-purple)';
            activePane.style.boxShadow = '0 0 30px #aa55ff40, 0 0 60px #ff336630, inset 0 0 20px #aa55ff15';
            setTimeout(() => {
                activePane.style.borderColor = '';
                activePane.style.boxShadow = '';
            }, 200);
        }
    }, 3000);
}

// ── Ambient Sound Effect (Visual Only - screen pulse) ───────────────────────
function initAmbientEffects() {
    // Periodic "void pulse" on the entire app
    setInterval(() => {
        const app = document.getElementById('app');
        if (!app) return;

        // Subtle brightness/contrast shift
        if (Math.random() < 0.3) {
            app.style.filter = 'brightness(1.02) contrast(1.01)';
            setTimeout(() => {
                app.style.filter = '';
            }, 150 + Math.random() * 200);
        }
    }, 8000 + Math.random() * 4000);
}

// ── Interactive Sigil Border ─────────────────────────────────────────────────
function initSigilBorder() {
    const sigilBorder = document.getElementById('sigil-border');
    if (!sigilBorder) return;

    // Make sigils react to mouse proximity
    document.addEventListener('mousemove', (e) => {
        const corners = sigilBorder.querySelectorAll('.sigil-corner');
        corners.forEach(corner => {
            const rect = corner.getBoundingClientRect();
            const dx = e.clientX - rect.left - rect.width / 2;
            const dy = e.clientY - rect.top - rect.height / 2;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 200) {
                const intensity = 1 - dist / 200;
                corner.style.opacity = 0.15 + intensity * 0.5;
                corner.style.textShadow = `0 0 ${6 + intensity * 12}px var(--accent-purple), 0 0 ${12 + intensity * 20}px var(--accent-purple)`;
            }
        });
    });
}

// ── Healthy Reconnection Animation ──────────────────────────────────────────
function initConnectionAnimations() {
    // Watch for connection status changes and animate accordingly
    const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
            if (mutation.attributeName === 'class') {
                const target = mutation.target;
                if (target.id === 'connection-status') {
                    const pulse = document.createElement('div');
                    pulse.style.cssText = `
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        width: 100px;
                        height: 100px;
                        border-radius: 50%;
                        pointer-events: none;
                        z-index: 9999;
                        animation: connection-pulse 1s ease-out forwards;
                    `;

                    if (target.classList.contains('connected')) {
                        pulse.style.border = '2px solid #00ff88';
                        pulse.style.boxShadow = '0 0 30px #00ff8840';
                    } else if (target.classList.contains('disconnected')) {
                        pulse.style.border = '2px solid #ff3366';
                        pulse.style.boxShadow = '0 0 30px #ff336640';
                    }

                    document.body.appendChild(pulse);
                    setTimeout(() => {
                        if (pulse.parentNode) pulse.parentNode.removeChild(pulse);
                    }, 1000);
                }
            }
        });
    });

    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
        observer.observe(statusEl, { attributes: true });
    }
}

// ── Random Eldritch Events ──────────────────────────────────────────────────
function initEldritchEvents() {
    // Occasional "whisper" - brief text flash at edges
    setInterval(() => {
        if (Math.random() > 0.6) return;

        const whispers = [
            'ᚠᛁᚱᛁᚾ', 'ᚦᚨᛏᛟᛋ', 'ᛉᛊᛏᚨᚾ', 'ᚹᚨᛚᚺᚨᛚᚺ', 'ᛞᛖᚨᚦ',
            '⌬⍟⎔', 'ᛁᚨᚺ', 'ᛈᚺᚾᛏ', '◇△▽', '☊☋☌'
        ];

        const whisper = document.createElement('div');
        whisper.textContent = whispers[Math.floor(Math.random() * whispers.length)];
        whisper.style.cssText = `
            position: fixed;
            font-family: var(--font-mono);
            font-size: ${8 + Math.random() * 6}px;
            color: var(--accent-purple);
            opacity: 0;
            pointer-events: none;
            z-index: 3;
            text-shadow: 0 0 8px var(--accent-purple);
            transition: opacity 1s ease;
        `;

        // Random edge position
        const edge = Math.floor(Math.random() * 4);
        switch(edge) {
            case 0: whisper.style.top = '5%'; whisper.style.left = (10 + Math.random() * 80) + '%'; break;
            case 1: whisper.style.bottom = '8%'; whisper.style.left = (10 + Math.random() * 80) + '%'; break;
            case 2: whisper.style.left = '3%'; whisper.style.top = (10 + Math.random() * 80) + '%'; break;
            case 3: whisper.style.right = '3%'; whisper.style.top = (10 + Math.random() * 80) + '%'; break;
        }

        document.body.appendChild(whisper);

        // Fade in and out
        requestAnimationFrame(() => {
            whisper.style.opacity = '0.15';
            setTimeout(() => {
                whisper.style.opacity = '0';
                setTimeout(() => {
                    if (whisper.parentNode) whisper.parentNode.removeChild(whisper);
                }, 1000);
            }, 2000 + Math.random() * 3000);
        });
    }, 15000 + Math.random() * 10000);
}

// ── Init ────────────────────────────────────────────────────────────────────
function init() {
    console.log('[Dashboard] Awakening Lilith Dashboard v3.0...');

    // Visual systems
    initParticleCanvas();
    spawnCSSRunes();
    initTitleGlitch();
    addEldritchBorderEffect();
    initAmbientEffects();
    initSigilBorder();
    initConnectionAnimations();
    initEldritchEvents();

    // Core functionality
    setupPaneFocus();
    setupKeyboard();
    addChatMessage('system', '⌬ The void stirs... connecting to Lilith ⌬');
    connect();
}

// ── Start ────────────────────────────────────────────────────────────────────
window.addEventListener('load', init);
window.addEventListener('beforeunload', () => {
    if (ws) ws.close();
    if (animFrame) cancelAnimationFrame(animFrame);
});

// ── Add connection-pulse animation to stylesheet dynamically ────────────────
(function injectDynamicStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes connection-pulse {
            0% { transform: translate(-50%, -50%) scale(0.5); opacity: 0.8; }
            100% { transform: translate(-50%, -50%) scale(3); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
})();
