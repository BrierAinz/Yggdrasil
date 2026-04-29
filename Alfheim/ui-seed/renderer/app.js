async function sendMessage() {
    const input = document.getElementById('message-input');
    const chat = document.getElementById('chat-history');
    const msg = input.value.trim();
    if (!msg) return;
    chat.innerHTML += `<div class="user">${escapeHtml(msg)}</div>`;
    input.value = '';
    chat.scrollTop = chat.scrollHeight;
    try {
        const res = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        chat.innerHTML += `<div class="bot">${escapeHtml(data.response)}</div>`;
        if (data.tool_call && data.tool_call.tool) {
            chat.innerHTML += `<div class="tool">Tool: ${escapeHtml(data.tool_call.tool)}</div>`;
        }
    } catch (e) {
        chat.innerHTML += `<div class="error">Error: ${escapeHtml(e.message)}</div>`;
    }
    chat.scrollTop = chat.scrollHeight;
}
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
async function loadTools() {
    try {
        const res = await fetch('http://localhost:8000/tools');
        const tools = await res.json();
        const list = document.getElementById('tools-list');
        list.innerHTML = Object.entries(tools).map(([name, desc]) => `<li><b>${name}</b>: ${desc}</li>`).join('');
    } catch (e) {
        console.error('No se pudieron cargar tools:', e);
    }
}
document.addEventListener('DOMContentLoaded', loadTools);
