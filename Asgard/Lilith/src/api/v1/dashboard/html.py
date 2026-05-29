"""
Dashboard HTML Template

SPA completo con:
- Chart.js para gráficos de barras/líneas
- D3.js para grafo de ejecución
- WebSocket para feed live
- Dark theme responsive
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lilith Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        :root {
            --bg-primary: #0f1419;
            --bg-secondary: #1a1f28;
            --bg-tertiary: #242a35;
            --text-primary: #e8eaed;
            --text-secondary: #9aa0a6;
            --border-color: #3c4048;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: var(--bg-secondary);
            border-bottom: 2px solid var(--border-color);
            padding: 20px 0;
            margin-bottom: 30px;
        }

        h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 14px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .stat-card {
            text-align: center;
        }

        .stat-value {
            font-size: 36px;
            font-weight: 700;
            color: var(--accent-blue);
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 14px;
            margin-top: 5px;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        .graph-container {
            height: 500px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            position: relative;
        }

        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: var(--text-secondary);
        }

        .spinner {
            border: 3px solid var(--border-color);
            border-top: 3px solid var(--accent-blue);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .btn {
            background: var(--accent-blue);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }

        .btn:hover {
            background: #2563eb;
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: var(--border-color);
        }

        .feed-item {
            background: var(--bg-tertiary);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid var(--accent-green);
            font-size: 14px;
        }

        .feed-time {
            color: var(--text-secondary);
            font-size: 12px;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-healthy {
            background: #10b98120;
            color: var(--accent-green);
        }

        .status-degraded {
            background: #f59e0b20;
            color: var(--accent-yellow);
        }

        .status-unhealthy {
            background: #ef444420;
            color: var(--accent-red);
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: border-color 0.2s;
        }

        .tab:hover {
            border-bottom-color: var(--text-secondary);
        }

        .tab.active {
            border-bottom-color: var(--accent-blue);
            color: var(--accent-blue);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 14px;
        }

        td {
            font-size: 14px;
        }

        .node {
            cursor: pointer;
        }

        .node circle {
            fill: var(--accent-blue);
            stroke: var(--border-color);
            stroke-width: 2px;
        }

        .node:hover circle {
            fill: #2563eb;
        }

        .node text {
            fill: var(--text-primary);
            font-size: 12px;
            text-anchor: middle;
        }

        .link {
            stroke: var(--border-color);
            stroke-width: 2px;
            fill: none;
        }

        .link-arrow {
            fill: var(--border-color);
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🔮 Lilith Dashboard</h1>
            <div class="subtitle">Sistema de monitoring y analytics</div>
        </div>
    </header>

    <div class="container">
        <!-- Overview Cards -->
        <div class="grid">
            <div class="card stat-card">
                <div class="stat-value" id="total-calls">-</div>
                <div class="stat-label">Total de llamadas</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="success-rate">-</div>
                <div class="stat-label">Tasa de éxito</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value" id="avg-latency">-</div>
                <div class="stat-label">Latencia promedio (ms)</div>
            </div>
            <div class="card stat-card">
                <div class="stat-value">
                    <span class="status-badge" id="health-status">-</span>
                </div>
                <div class="stat-label">Estado del sistema</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" onclick="switchTab('analytics')">📊 Analytics</div>
            <div class="tab" onclick="switchTab('memory')">💾 Memoria</div>
            <div class="tab" onclick="switchTab('graph')">🌐 Grafo</div>
            <div class="tab" onclick="switchTab('sessions')">📝 Sesiones</div>
            <div class="tab" onclick="switchTab('audit')">🔒 Auditoría</div>
        </div>

        <!-- Tab: Analytics -->
        <div id="analytics-tab" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <div class="card-title">📈 Intents más usados</div>
                    <div class="chart-container">
                        <canvas id="intents-chart"></canvas>
                    </div>
                </div>
                <div class="card">
                    <div class="card-title">🎯 Distribución de confianza</div>
                    <div class="chart-container">
                        <canvas id="confidence-chart"></canvas>
                    </div>
                </div>
            </div>
            <div class="grid">
                <div class="card">
                    <div class="card-title">⚡ Latencia por herramienta</div>
                    <div class="chart-container">
                        <canvas id="latency-chart"></canvas>
                    </div>
                </div>
                <div class="card">
                    <div class="card-title">✅ Tasa de éxito por agente</div>
                    <div class="chart-container">
                        <canvas id="agents-chart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab: Memory -->
        <div id="memory-tab" class="tab-content">
            <div class="card">
                <div class="card-title">💾 Estadísticas de memoria</div>
                <div id="memory-stats" class="loading">
                    <div class="spinner"></div>
                    Cargando...
                </div>
            </div>
        </div>

        <!-- Tab: Graph -->
        <div id="graph-tab" class="tab-content">
            <div class="card">
                <div class="card-title">🌐 Grafo de ejecución</div>
                <div id="execution-graph" class="graph-container"></div>
            </div>
        </div>

        <!-- Tab: Sessions -->
        <div id="sessions-tab" class="tab-content">
            <div class="card">
                <div class="card-title">📝 Resúmenes de sesión</div>
                <div id="sessions-list"></div>
            </div>
        </div>

        <!-- Tab: Audit -->
        <div id="audit-tab" class="tab-content">
            <div class="card">
                <div class="card-title">🔒 Auditoría reciente</div>
                <div id="audit-list"></div>
            </div>
        </div>

        <!-- Export Button -->
        <div style="margin-top: 30px; text-align: center;">
            <button class="btn" onclick="exportData()">📦 Exportar datos</button>
        </div>
    </div>

    <script>
        // Estado global
        let charts = {};

        // Inicialización
        document.addEventListener('DOMContentLoaded', () => {
            loadOverview();
            loadAnalytics();
            // WebSocket para feed live (TODO)
        });

        // Funciones de carga
        async function loadOverview() {
            try {
                const res = await fetch('/api/dashboard/overview');
                const data = await res.json();

                document.getElementById('total-calls').textContent = data.agents?.total_calls || 0;
                document.getElementById('success-rate').textContent = ((data.agents?.success_rate || 0) * 100).toFixed(1) + '%';
                document.getElementById('avg-latency').textContent = (data.agents?.avg_latency_ms || 0).toFixed(1);

                const healthBadge = document.getElementById('health-status');
                const status = data.health?.status || 'unknown';
                healthBadge.textContent = status.toUpperCase();
                healthBadge.className = 'status-badge status-' + status;
            } catch (e) {
                console.error('Failed to load overview:', e);
            }
        }

        async function loadAnalytics() {
            try {
                const res = await fetch('/api/dashboard/analytics?days=7');
                const data = await res.json();

                // Intents chart
                createBarChart('intents-chart',
                    data.top_intents?.map(i => i.intent) || [],
                    data.top_intents?.map(i => i.count) || [],
                    'Intents más usados'
                );

                // Confidence distribution
                const confData = data.confidence_distribution || {};
                createPieChart('confidence-chart',
                    ['High', 'Medium', 'Low', 'Unknown'],
                    [confData.high || 0, confData.medium || 0, confData.low || 0, confData.unknown || 0]
                );

                // Tool latency
                createBarChart('latency-chart',
                    data.tool_latencies?.map(t => t.tool) || [],
                    data.tool_latencies?.map(t => t.avg_latency_ms) || [],
                    'Latencia promedio (ms)'
                );

                // Agent success rates
                createBarChart('agents-chart',
                    data.agent_success_rates?.map(a => a.agent) || [],
                    data.agent_success_rates?.map(a => a.success_rate) || [],
                    'Tasa de éxito (%)'
                );
            } catch (e) {
                console.error('Failed to load analytics:', e);
            }
        }

        async function loadMemory() {
            try {
                const res = await fetch('/api/dashboard/memory');
                const data = await res.json();

                const html = `
                    <table>
                        <tr><th colspan="2">ChromaDB</th></tr>
                        <tr><td>Total chunks</td><td>${data.chromadb?.total_chunks || 'N/A'}</td></tr>
                        <tr><th colspan="2">MuninnDB</th></tr>
                        <tr><td>Total edges</td><td>${data.muninn?.total_edges || 0}</td></tr>
                        <tr><th colspan="2">Episódica</th></tr>
                        <tr><td>Total episodios</td><td>${data.episodic?.total_episodes || 0}</td></tr>
                        <tr><td>Tamaño (MB)</td><td>${data.episodic?.size_mb || 0}</td></tr>
                    </table>
                `;

                document.getElementById('memory-stats').innerHTML = html;
            } catch (e) {
                console.error('Failed to load memory:', e);
            }
        }

        async function loadGraph() {
            try {
                const res = await fetch('/api/dashboard/graph?limit=100');
                const data = await res.json();

                renderGraph(data);
            } catch (e) {
                console.error('Failed to load graph:', e);
            }
        }

        async function loadSessions() {
            try {
                const res = await fetch('/api/dashboard/sessions?limit=20');
                const data = await res.json();

                const html = data.map(session => `
                    <div class="feed-item">
                        <div><strong>Sesión ${session.session_id?.slice(0, 8) || 'unknown'}</strong></div>
                        <div>${session.summary || 'Sin resumen'}</div>
                        <div class="feed-time">${new Date(session.summary_created_at).toLocaleString()}</div>
                    </div>
                `).join('');

                document.getElementById('sessions-list').innerHTML = html || '<div class="loading">No hay sesiones resumidas</div>';
            } catch (e) {
                console.error('Failed to load sessions:', e);
            }
        }

        async function loadAudit() {
            try {
                const res = await fetch('/api/dashboard/audit?days=7&limit=50');
                const data = await res.json();

                const html = `
                    <table>
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Tipo</th>
                                <th>Confianza</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.map(event => `
                                <tr>
                                    <td>${new Date(event.timestamp).toLocaleString()}</td>
                                    <td>${event.decision_type || 'unknown'}</td>
                                    <td>${event.confidence ? (event.confidence * 100).toFixed(0) + '%' : 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;

                document.getElementById('audit-list').innerHTML = html || '<div class="loading">No hay eventos</div>';
            } catch (e) {
                console.error('Failed to load audit:', e);
            }
        }

        // Tab switching
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(tabName + '-tab').classList.add('active');

            // Load data if needed
            if (tabName === 'memory') loadMemory();
            if (tabName === 'graph') loadGraph();
            if (tabName === 'sessions') loadSessions();
            if (tabName === 'audit') loadAudit();
        }

        // Chart helpers
        function createBarChart(canvasId, labels, data, label) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;

            if (charts[canvasId]) charts[canvasId].destroy();

            charts[canvasId] = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: label,
                        data: data,
                        backgroundColor: '#3b82f6',
                        borderColor: '#2563eb',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#3c4048' }, ticks: { color: '#9aa0a6' } },
                        x: { grid: { color: '#3c4048' }, ticks: { color: '#9aa0a6' } }
                    }
                }
            });
        }

        function createPieChart(canvasId, labels, data) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return;

            if (charts[canvasId]) charts[canvasId].destroy();

            charts[canvasId] = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#6b7280']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { color: '#e8eaed' } }
                    }
                }
            });
        }

        // Graph rendering with D3
        function renderGraph(data) {
            const container = document.getElementById('execution-graph');
            container.innerHTML = '';

            const width = container.clientWidth;
            const height = container.clientHeight;

            const svg = d3.select('#execution-graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);

            const simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2));

            const link = svg.append('g')
                .selectAll('line')
                .data(data.links)
                .enter().append('line')
                .attr('class', 'link');

            const node = svg.append('g')
                .selectAll('g')
                .data(data.nodes)
                .enter().append('g')
                .attr('class', 'node')
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));

            node.append('circle')
                .attr('r', 10);

            node.append('text')
                .attr('dy', 20)
                .text(d => d.label.slice(0, 15));

            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });

            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }

            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }

            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
        }

        // Export data
        async function exportData() {
            try {
                window.location.href = '/api/dashboard/export';
            } catch (e) {
                console.error('Failed to export:', e);
                alert('Error al exportar datos');
            }
        }
    </script>
</body>
</html>
"""


def get_dashboard_html() -> str:
    """Obtener HTML del dashboard"""
    return DASHBOARD_HTML
