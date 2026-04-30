"""
Lilith — Dashboard de Observabilidad API.
Endpoints para el panel de control: agentes, memoria, aprendizaje, sesiones, auditoría.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger("lilith.dashboard_api")

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _json(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status)


# ─── Legacy stats (mantener compatibilidad) ───────────────────────────────────


@router.get("/stats")
async def get_dashboard_stats() -> JSONResponse:
    """Métricas agregadas legacy (compatibilidad v2.3)."""
    try:
        from src.metrics_collector import collect

        data = collect()
        return _json({"success": True, "data": data})
    except Exception as e:
        logger.debug("dashboard/stats legacy error: %s", e)
        return _json({"success": True, "data": {}})


# ─── Overview ─────────────────────────────────────────────────────────────────


@router.get("/overview")
async def get_overview() -> JSONResponse:
    """Resumen general del sistema: estado, canal activo, alertas."""
    result: Dict[str, Any] = {
        "status": "ok",
        "active_channel": None,
        "agent_health": {},
        "memory_vaults": [],
        "alerts": [],
    }

    # Canal de mayor prioridad activo
    try:
        from src.core.channel_priority import channel_priority

        result["active_channel"] = channel_priority.get_active_channel()
    except Exception:
        pass

    # Salud de agentes
    try:
        from src.core.agent_metrics import get_metrics

        result["agent_health"] = get_metrics().health_summary()
    except Exception:
        pass

    # Vaults de memoria
    try:
        from src.core.memory.muninn_memory import AGENT_VAULTS

        result["memory_vaults"] = list(dict.fromkeys(AGENT_VAULTS.values()))
    except Exception:
        result["memory_vaults"] = ["lilith", "odin", "eva", "adan", "crystal"]

    # Alertas: agentes degradados
    health = result["agent_health"]
    if isinstance(health, dict):
        for tool, info in (health.get("degraded_tools") or {}).items():
            result["alerts"].append(
                {
                    "level": "warning",
                    "tool": tool,
                    "reason": info.get("reason", "degraded"),
                }
            )

    return _json(result)


# ─── Agentes ──────────────────────────────────────────────────────────────────


@router.get("/agents")
async def get_agents() -> JSONResponse:
    """Métricas detalladas de todos los agentes/tools."""
    try:
        from src.core.agent_metrics import get_metrics

        m = get_metrics()
        return _json(
            {
                "stats": m.get_stats(),
                "health": m.health_summary(),
            }
        )
    except Exception as e:
        return _json({"stats": {}, "health": {}, "error": str(e)})


@router.get("/agents/{tool_name}")
async def get_agent_stats(tool_name: str) -> JSONResponse:
    """Métricas de un tool específico."""
    try:
        from src.core.agent_metrics import get_metrics

        data = get_metrics().get_stats(tool_name)
        if not data:
            return _json({"error": "tool not found"}, 404)
        return _json(data)
    except Exception as e:
        return _json({"error": str(e)}, 500)


# ─── Memoria ──────────────────────────────────────────────────────────────────


@router.get("/memory")
async def get_memory_stats() -> JSONResponse:
    """Estadísticas de MuninnDB (vaults, recuentos, últimas activaciones)."""
    root = _root()
    result: Dict[str, Any] = {
        "vaults": {},
        "recent_activations": [],
        "working_memory": {},
    }

    # Working memory size por canal
    try:
        from src.core.memory.working_memory import get_working_memory

        for channel in ("telegram", "discord", "discord_dm"):
            wm = get_working_memory(channel)
            items = getattr(wm, "_items", {})
            result["working_memory"][channel] = len(items)
    except Exception:
        pass

    # Contar entradas en archivos de sesión (proxy de actividad Muninn)
    try:
        sessions_dir = root / "Data" / "sessions"
        if sessions_dir.exists():
            for f in sessions_dir.glob("*.jsonl"):
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                    result["vaults"][f.stem] = len([l for l in lines if l.strip()])
                except Exception:
                    pass
    except Exception:
        pass

    # Edges count
    try:
        edges_file = root / "Data" / "muninn_edges.jsonl"
        if edges_file.exists():
            edges_count = len(
                [
                    l
                    for l in edges_file.read_text(encoding="utf-8").splitlines()
                    if l.strip()
                ]
            )
            result["edges_count"] = edges_count
    except Exception:
        result["edges_count"] = 0

    return _json(result)


# ─── Learning / Edges ─────────────────────────────────────────────────────────


@router.get("/learning")
async def get_learning() -> JSONResponse:
    """Datos del grafo de relaciones (EdgeManager) y patrones aprendidos."""
    root = _root()
    result: Dict[str, Any] = {
        "total_edges": 0,
        "top_concepts": [],
        "confirmation_patterns": {},
        "tool_sequences": [],
    }

    try:
        from src.core.muninn_edges import get_edge_manager

        em = get_edge_manager(root)

        # Leer todas las edges del JSONL
        edges_file = root / "Data" / "muninn_edges.jsonl"
        if edges_file.exists():
            import json

            edges = []
            for line in edges_file.read_text(encoding="utf-8").splitlines():
                try:
                    edges.append(json.loads(line))
                except Exception:
                    pass
            result["total_edges"] = len(edges)

            # Top conceptos por frecuencia de aparición
            from collections import Counter

            concept_counts: Counter = Counter()
            for e in edges:
                concept_counts[e.get("source", "")] += 1
                concept_counts[e.get("target", "")] += 1
            result["top_concepts"] = [
                {"concept": c, "count": n}
                for c, n in concept_counts.most_common(10)
                if c
            ]

            # Patrones de confirmación
            conf_edges = [e for e in edges if e.get("edge_type") == "confirmation"]
            authorized = sum(
                1
                for e in conf_edges
                if e.get("metadata", {}).get("action") == "authorize"
            )
            denied = sum(
                1 for e in conf_edges if e.get("metadata", {}).get("action") == "deny"
            )
            result["confirmation_patterns"] = {
                "total": len(conf_edges),
                "authorized": authorized,
                "denied": denied,
                "approval_rate": round(authorized / len(conf_edges), 2)
                if conf_edges
                else 0.0,
            }

            # Top secuencias de tools
            seq_edges = [e for e in edges if e.get("edge_type") == "tool_sequence"]
            seq_counts: Counter = Counter()
            for e in seq_edges:
                key = f"{e.get('source', '?')} → {e.get('target', '?')}"
                seq_counts[key] += 1
            result["tool_sequences"] = [
                {"sequence": s, "count": n} for s, n in seq_counts.most_common(10)
            ]
    except Exception as e:
        result["error"] = str(e)

    return _json(result)


# ─── Sesiones ─────────────────────────────────────────────────────────────────


@router.get("/sessions")
async def get_sessions() -> JSONResponse:
    """Resúmenes de sesiones del SessionSummarizer."""
    root = _root()
    try:
        from src.core.session_summarizer import get_session_summarizer

        ss = get_session_summarizer(root)
        summaries = getattr(ss, "_summaries", None)
        if summaries is None:
            # Intentar cargar desde archivo
            try:
                import json

                sf = root / "Data" / "session_summaries.jsonl"
                summaries = []
                if sf.exists():
                    for line in sf.read_text(encoding="utf-8").splitlines():
                        try:
                            summaries.append(json.loads(line))
                        except Exception:
                            pass
            except Exception:
                summaries = []

        recent = list(reversed(summaries[-20:])) if summaries else []
        return _json(
            {
                "total_summaries": len(summaries) if summaries else 0,
                "recent": recent,
            }
        )
    except Exception as e:
        return _json({"total_summaries": 0, "recent": [], "error": str(e)})


# ─── Auditoría ────────────────────────────────────────────────────────────────


@router.get("/audit/recent")
async def get_audit_recent() -> JSONResponse:
    """Últimas N entradas del log de auditoría del PC Agent."""
    root = _root()
    try:
        import json

        audit_file = root / "Data" / "pc_agent_audit.jsonl"
        if not audit_file.exists():
            return _json({"entries": [], "total": 0})

        lines = audit_file.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
            if len(entries) >= 50:
                break

        return _json({"entries": entries, "total": len(lines)})
    except Exception as e:
        return _json({"entries": [], "total": 0, "error": str(e)})


# ─── Dashboard HTML ───────────────────────────────────────────────────────────

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lilith — Dashboard de Observabilidad</title>
<style>
  :root {
    --bg: #0d0d0f; --surface: #16161a; --surface2: #1e1e24;
    --border: #2a2a35; --text: #e2e2e8; --muted: #888899;
    --accent: #7c6af7; --green: #4caf8a; --red: #e05c6e; --yellow: #f0a040;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 18px; color: var(--accent); }
  header span { color: var(--muted); font-size: 12px; }
  #refresh-btn { margin-left: auto; background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
  #refresh-btn:hover { border-color: var(--accent); }
  main { padding: 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }
  .card h2 { font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px; }
  .stat-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--border); }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { color: var(--muted); }
  .stat-val { font-weight: 600; }
  .ok { color: var(--green); } .warn { color: var(--yellow); } .err { color: var(--red); }
  .alert { background: var(--surface2); border-left: 3px solid var(--yellow); padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; font-size: 13px; }
  .tag { display: inline-block; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 1px 7px; font-size: 11px; margin: 2px; }
  .audit-entry { background: var(--surface2); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 12px; line-height: 1.5; }
  .audit-entry .op { color: var(--accent); font-weight: 600; }
  .audit-entry .ts { color: var(--muted); }
  #loading { text-align: center; padding: 60px; color: var(--muted); font-size: 16px; }
  pre { white-space: pre-wrap; word-break: break-all; font-family: 'Cascadia Code', monospace; font-size: 11px; color: var(--muted); }
</style>
</head>
<body>
<header>
  <h1>⚙ Lilith</h1>
  <span>Dashboard de Observabilidad</span>
  <button id="refresh-btn" onclick="loadAll()">↺ Actualizar</button>
</header>
<div id="loading">Cargando datos...</div>
<main id="main" style="display:none"></main>

<script>
const API = '';

async function fetchJson(path) {
  try {
    const r = await fetch(API + path);
    return await r.json();
  } catch(e) { return {}; }
}

function card(title, content) {
  return `<div class="card"><h2>${title}</h2>${content}</div>`;
}

function row(label, val, cls='') {
  return `<div class="stat-row"><span class="stat-label">${label}</span><span class="stat-val ${cls}">${val}</span></div>`;
}

function statusClass(val, okThreshold=0.8, warnThreshold=0.5) {
  if (val === undefined || val === null) return '';
  if (val >= okThreshold) return 'ok';
  if (val >= warnThreshold) return 'warn';
  return 'err';
}

async function loadAll() {
  document.getElementById('loading').style.display = 'block';
  document.getElementById('main').style.display = 'none';

  const [overview, agents, memory, learning, sessions, audit] = await Promise.all([
    fetchJson('/api/dashboard/overview'),
    fetchJson('/api/dashboard/agents'),
    fetchJson('/api/dashboard/memory'),
    fetchJson('/api/dashboard/learning'),
    fetchJson('/api/dashboard/sessions'),
    fetchJson('/api/dashboard/audit/recent'),
  ]);

  const sections = [];

  // ── Overview ──
  const alerts = (overview.alerts || []).map(a =>
    `<div class="alert">⚠ <strong>${a.tool || ''}</strong>: ${a.reason || ''}</div>`
  ).join('');
  const systemStatus = (overview.alerts || []).length === 0 ? '<span class="ok">Operativo</span>' : `<span class="warn">${overview.alerts.length} alertas</span>`;
  sections.push(card('Sistema', [
    row('Estado', systemStatus),
    row('Canal activo', overview.active_channel || '—'),
    row('Vaults de memoria', (overview.memory_vaults || []).join(', ') || '—'),
    alerts ? `<div style="margin-top:10px">${alerts}</div>` : '',
  ].join('')));

  // ── Agentes ──
  const stats = agents.stats || {};
  const toolNames = Object.keys(stats).slice(0, 12);
  const agentRows = toolNames.map(t => {
    const s = stats[t];
    if (!s) return '';
    const sr = typeof s.success_rate === 'number' ? (s.success_rate * 100).toFixed(0) + '%' : '—';
    const lat = typeof s.p95_latency_ms === 'number' ? s.p95_latency_ms.toFixed(0) + 'ms' : '—';
    const cls = statusClass(s.success_rate);
    return row(t, `${sr} · p95=${lat} · ${s.total_calls || 0} calls`, cls);
  }).join('');
  sections.push(card('Agentes & Tools', agentRows || '<span class="stat-label">Sin datos aún</span>'));

  // ── Memoria ──
  const wm = memory.working_memory || {};
  const wmRows = Object.entries(wm).map(([ch, n]) => row(ch, n + ' items')).join('');
  const vaultRows = Object.entries(memory.vaults || {}).map(([v, n]) => row(v, n + ' entradas')).join('');
  sections.push(card('Memoria', [
    `<div style="margin-bottom:8px;color:var(--muted);font-size:12px">Working Memory</div>`,
    wmRows || row('—', '—'),
    vaultRows ? `<div style="margin:10px 0 6px;color:var(--muted);font-size:12px">Sesiones</div>${vaultRows}` : '',
    row('Edges en grafo', learning.total_edges || 0),
  ].join('')));

  // ── Learning ──
  const topConcepts = (learning.top_concepts || []).slice(0, 8)
    .map(c => `<span class="tag">${c.concept} ×${c.count}</span>`).join('');
  const conf = learning.confirmation_patterns || {};
  const seqs = (learning.tool_sequences || []).slice(0, 5)
    .map(s => row(s.sequence, `×${s.count}`)).join('');
  sections.push(card('Aprendizaje', [
    row('Total edges', learning.total_edges || 0),
    row('Confirmaciones', (conf.total || 0) + ` (${Math.round((conf.approval_rate || 0) * 100)}% aprobadas)`),
    topConcepts ? `<div style="margin:10px 0 4px;color:var(--muted);font-size:12px">Top conceptos</div><div>${topConcepts}</div>` : '',
    seqs ? `<div style="margin:10px 0 4px;color:var(--muted);font-size:12px">Secuencias frecuentes</div>${seqs}` : '',
  ].join('')));

  // ── Sesiones ──
  const recSessions = (sessions.recent || []).slice(0, 5).map(s => {
    const ts = s.created_at ? new Date(s.created_at * 1000).toLocaleString('es') : '—';
    const text = s.summary ? s.summary.slice(0, 100) : (s.text || '').slice(0, 100);
    return `<div class="audit-entry"><span class="ts">${ts}</span> — ${text}</div>`;
  }).join('');
  sections.push(card('Sesiones recientes', [
    row('Total resúmenes', sessions.total_summaries || 0),
    recSessions || '<span class="stat-label">Sin resúmenes aún</span>',
  ].join('')));

  // ── Auditoría PC ──
  const audEntries = (audit.entries || []).slice(0, 8).map(e => {
    const ts = e.timestamp ? new Date(e.timestamp * 1000).toLocaleString('es') : (e.ts ? new Date(e.ts * 1000).toLocaleString('es') : '—');
    const ok = e.success !== false ? '✅' : '❌';
    return `<div class="audit-entry">${ok} <span class="op">${e.op || '?'}</span> <span class="ts">${ts}</span><br><pre>${JSON.stringify(e.params || {}).slice(0, 120)}</pre></div>`;
  }).join('');
  sections.push(card('Auditoría PC Agent', [
    row('Total entradas', audit.total || 0),
    audEntries || '<span class="stat-label">Sin actividad</span>',
  ].join('')));

  document.getElementById('main').innerHTML = sections.join('');
  document.getElementById('loading').style.display = 'none';
  document.getElementById('main').style.display = 'grid';
}

loadAll();
// Auto-refresh cada 60 segundos
setInterval(loadAll, 60000);
</script>
</body>
</html>"""


# ─── Modelos ──────────────────────────────────────────────────────────────────


@router.get("/models")
async def get_models_stats() -> JSONResponse:
    """Estadísticas de uso de modelos LLM y ahorros."""
    result: Dict[str, Any] = {
        "models_usage": {},
        "savings": {
            "total_saved": 0,
            "percentage": 0,
        },
        "complexity_distribution": {},
        "fallback_stats": {},
        "recent_calls": [],
    }

    try:
        from src.llm.cost_tracker_extended import get_cost_tracker_v2

        tracker = get_cost_tracker_v2()

        # Reporte de ahorros
        savings_report = tracker.get_savings_report(days=7)
        result["savings"] = {
            "total_saved": f"${savings_report.get('savings', 0):.2f}",
            "percentage": savings_report.get("savings_percentage", 0),
            "actual_cost": f"${savings_report.get('actual_cost', 0):.2f}",
            "baseline_cost": f"${savings_report.get('baseline_cost', 0):.2f}",
            "period_days": savings_report.get("period_days", 7),
        }

        # Uso por modelo
        by_model = savings_report.get("by_model", [])
        for model_data in by_model:
            model_name = model_data["model"]
            result["models_usage"][model_name] = {
                "calls": model_data.get("calls", 0),
                "cost": f"${model_data.get('cost', 0):.2f}",
                "avg_latency_ms": model_data.get("avg_latency_ms", 0),
                "input_tokens": model_data.get("input_tokens", 0),
                "output_tokens": model_data.get("output_tokens", 0),
            }

        # Distribución por complejidad
        result["complexity_distribution"] = savings_report.get("by_complexity", {})

    except Exception as e:
        logger.warning(f"[Dashboard] Error getting model stats: {e}")
        result["error"] = str(e)

    # Stats del selector
    try:
        from src.llm.model_selector import get_model_selector

        selector = get_model_selector()
        selector_stats = selector.get_stats()
        result["fallback_stats"] = selector_stats.get("fallback_stats", {})
    except Exception as e:
        logger.warning(f"[Dashboard] Error getting selector stats: {e}")

    # Stats del cache
    try:
        from src.llm.model_cache import get_model_cache

        cache = get_model_cache()
        cache_stats = cache.get_stats()
        result["cache_stats"] = {
            "hits": cache_stats.get("hits", 0),
            "misses": cache_stats.get("misses", 0),
            "hit_rate": cache_stats.get("hit_rate", 0),
            "total_entries": cache_stats.get("total_entries", 0),
        }
        savings = cache.get_savings_estimate()
        result["cache_stats"][
            "estimated_savings"
        ] = f"${savings.get('estimated_savings_usd', 0):.2f}"
    except Exception as e:
        logger.warning(f"[Dashboard] Error getting cache stats: {e}")

    return _json(result)


@router.get("/models/daily")
async def get_daily_model_costs(days: int = 7) -> JSONResponse:
    """Costos diarios de modelos."""
    try:
        from src.llm.cost_tracker_extended import get_cost_tracker_v2

        tracker = get_cost_tracker_v2()
        daily = tracker.get_daily_costs(days=days)
        return _json({"daily": daily, "days": days})
    except Exception as e:
        return _json({"daily": [], "error": str(e)}, 500)


@router.get("/models/efficiency")
async def get_model_efficiency(days: int = 30) -> JSONResponse:
    """Eficiencia por modelo (costo/latencia)."""
    try:
        from src.llm.cost_tracker_extended import get_cost_tracker_v2

        tracker = get_cost_tracker_v2()
        efficiency = tracker.get_model_efficiency(days=days)
        return _json(efficiency)
    except Exception as e:
        return _json({"error": str(e)}, 500)


# ─── Dashboard HTML ───────────────────────────────────────────────────────────

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lilith — Dashboard de Observabilidad</title>
<style>
  :root {
    --bg: #0d0d0f; --surface: #16161a; --surface2: #1e1e24;
    --border: #2a2a35; --text: #e2e2e8; --muted: #888899;
    --accent: #7c6af7; --green: #4caf8a; --red: #e05c6e; --yellow: #f0a040;
    --blue: #5c9dff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 18px; color: var(--accent); }
  header span { color: var(--muted); font-size: 12px; }
  #refresh-btn { margin-left: auto; background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
  #refresh-btn:hover { border-color: var(--accent); }
  main { padding: 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }
  .card h2 { font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px; }
  .stat-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--border); }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { color: var(--muted); }
  .stat-val { font-weight: 600; }
  .ok { color: var(--green); } .warn { color: var(--yellow); } .err { color: var(--red); }
  .accent { color: var(--accent); }
  .blue { color: var(--blue); }
  .alert { background: var(--surface2); border-left: 3px solid var(--yellow); padding: 8px 12px; border-radius: 4px; margin-bottom: 6px; font-size: 13px; }
  .tag { display: inline-block; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 1px 7px; font-size: 11px; margin: 2px; }
  .audit-entry { background: var(--surface2); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; font-size: 12px; line-height: 1.5; }
  .audit-entry .op { color: var(--accent); font-weight: 600; }
  .audit-entry .ts { color: var(--muted); }
  #loading { text-align: center; padding: 60px; color: var(--muted); font-size: 16px; }
  pre { white-space: pre-wrap; word-break: break-all; font-family: 'Cascadia Code', monospace; font-size: 11px; color: var(--muted); }
  .savings-card { background: linear-gradient(135deg, var(--surface) 0%, rgba(76,175,138,0.1) 100%); }
  .savings-card h2 { color: var(--green); }
  .model-bar { display: flex; align-items: center; margin: 8px 0; }
  .model-bar .label { width: 120px; font-size: 12px; color: var(--muted); }
  .model-bar .bar-bg { flex: 1; height: 8px; background: var(--surface2); border-radius: 4px; overflow: hidden; }
  .model-bar .bar-fill { height: 100%; border-radius: 4px; }
  .model-bar .value { width: 80px; text-align: right; font-size: 12px; }
</style>
</head>
<body>
<header>
  <h1>⚙ Lilith</h1>
  <span>Dashboard de Observabilidad</span>
  <button id="refresh-btn" onclick="loadAll()">↺ Actualizar</button>
</header>
<div id="loading">Cargando datos...</div>
<main id="main" style="display:none"></main>

<script>
const API = '';

async function fetchJson(path) {
  try {
    const r = await fetch(API + path);
    return await r.json();
  } catch(e) { return {}; }
}

function card(title, content, extraClass='') {
  return `<div class="card ${extraClass}"><h2>${title}</h2>${content}</div>`;
}

function row(label, val, cls='') {
  return `<div class="stat-row"><span class="stat-label">${label}</span><span class="stat-val ${cls}">${val}</span></div>`;
}

function statusClass(val, okThreshold=0.8, warnThreshold=0.5) {
  if (val === undefined || val === null) return '';
  if (val >= okThreshold) return 'ok';
  if (val >= warnThreshold) return 'warn';
  return 'err';
}

function modelBar(model, calls, maxCalls, color) {
  const pct = maxCalls > 0 ? (calls / maxCalls * 100).toFixed(1) : 0;
  return `
    <div class="model-bar">
      <span class="label">${model.length > 15 ? model.slice(0,12)+'...' : model}</span>
      <div class="bar-bg"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
      <span class="value">${calls} calls</span>
    </div>
  `;
}

async function loadAll() {
  document.getElementById('loading').style.display = 'block';
  document.getElementById('main').style.display = 'none';

  const [overview, agents, memory, learning, sessions, audit, models] = await Promise.all([
    fetchJson('/api/dashboard/overview'),
    fetchJson('/api/dashboard/agents'),
    fetchJson('/api/dashboard/memory'),
    fetchJson('/api/dashboard/learning'),
    fetchJson('/api/dashboard/sessions'),
    fetchJson('/api/dashboard/audit/recent'),
    fetchJson('/api/dashboard/models'),
  ]);

  const sections = [];

  // ── Overview ──
  const alerts = (overview.alerts || []).map(a =>
    `<div class="alert">⚠ <strong>${a.tool || ''}</strong>: ${a.reason || ''}</div>`
  ).join('');
  const systemStatus = (overview.alerts || []).length === 0 ? '<span class="ok">Operativo</span>' : `<span class="warn">${overview.alerts.length} alertas</span>`;
  sections.push(card('Sistema', [
    row('Estado', systemStatus),
    row('Canal activo', overview.active_channel || '—'),
    row('Vaults de memoria', (overview.memory_vaults || []).join(', ') || '—'),
    alerts ? `<div style="margin-top:10px">${alerts}</div>` : '',
  ].join('')));

  // ── Agentes ──
  const stats = agents.stats || {};
  const toolNames = Object.keys(stats).slice(0, 12);
  const agentRows = toolNames.map(t => {
    const s = stats[t];
    if (!s) return '';
    const sr = typeof s.success_rate === 'number' ? (s.success_rate * 100).toFixed(0) + '%' : '—';
    const lat = typeof s.p95_latency_ms === 'number' ? s.p95_latency_ms.toFixed(0) + 'ms' : '—';
    const cls = statusClass(s.success_rate);
    return row(t, `${sr} · p95=${lat} · ${s.total_calls || 0} calls`, cls);
  }).join('');
  sections.push(card('Agentes & Tools', agentRows || '<span class="stat-label">Sin datos aún</span>'));

  // ── Modelos & Ahorros ──
  const savings = models.savings || {};
  const modelUsage = models.models_usage || {};
  const modelNames = Object.keys(modelUsage);
  const totalCalls = modelNames.reduce((sum, m) => sum + (modelUsage[m].calls || 0), 0);
  const maxCalls = modelNames.length > 0 ? Math.max(...modelNames.map(m => modelUsage[m].calls || 0)) : 1;

  const modelBars = modelNames.slice(0, 6).map((m, i) => {
    const colors = ['#7c6af7', '#4caf8a', '#5c9dff', '#f0a040', '#e05c6e', '#888899'];
    return modelBar(m, modelUsage[m].calls || 0, maxCalls, colors[i % colors.length]);
  }).join('');

  const cacheStats = models.cache_stats || {};

  sections.push(card('💰 Ahorros Multi-Modelo', [
    row('Ahorro total', savings.total_saved || '$0.00', 'ok'),
    row('Porcentaje', (savings.percentage || 0) + '% vs Opus', 'ok'),
    row('Costo real', savings.actual_cost || '$0.00'),
    row('Costo baseline', savings.baseline_cost || '$0.00'),
    row('Período', (savings.period_days || 7) + ' días'),
    `<div style="margin-top:12px;border-top:1px solid var(--border);padding-top:12px;">`,
    row('Cache hits', (cacheStats.hits || 0), 'accent'),
    row('Cache hit rate', (cacheStats.hit_rate || 0) + '%', 'accent'),
    row('Cache savings', cacheStats.estimated_savings || '$0.00', 'ok'),
    '</div>',
  ].join(''), 'savings-card'));

  sections.push(card('🤖 Uso de Modelos (7 días)', [
    row('Total llamadas', totalCalls),
    modelBars || '<span class="stat-label">Sin datos aún</span>',
  ].join('')));

  // ── Memoria ──
  const wm = memory.working_memory || {};
  const wmRows = Object.entries(wm).map(([ch, n]) => row(ch, n + ' items')).join('');
  const vaultRows = Object.entries(memory.vaults || {}).map(([v, n]) => row(v, n + ' entradas')).join('');
  sections.push(card('Memoria', [
    `<div style="margin-bottom:8px;color:var(--muted);font-size:12px">Working Memory</div>`,
    wmRows || row('—', '—'),
    vaultRows ? `<div style="margin:10px 0 6px;color:var(--muted);font-size:12px">Sesiones</div>${vaultRows}` : '',
    row('Edges en grafo', learning.total_edges || 0),
  ].join('')));

  // ── Learning ──
  const topConcepts = (learning.top_concepts || []).slice(0, 8)
    .map(c => `<span class="tag">${c.concept} ×${c.count}</span>`).join('');
  const conf = learning.confirmation_patterns || {};
  const seqs = (learning.tool_sequences || []).slice(0, 5)
    .map(s => row(s.sequence, `×${s.count}`)).join('');
  sections.push(card('Aprendizaje', [
    row('Total edges', learning.total_edges || 0),
    row('Confirmaciones', (conf.total || 0) + ` (${Math.round((conf.approval_rate || 0) * 100)}% aprobadas)`),
    topConcepts ? `<div style="margin:10px 0 4px;color:var(--muted);font-size:12px">Top conceptos</div><div>${topConcepts}</div>` : '',
    seqs ? `<div style="margin:10px 0 4px;color:var(--muted);font-size:12px">Secuencias frecuentes</div>${seqs}` : '',
  ].join('')));

  // ── Sesiones ──
  const recSessions = (sessions.recent || []).slice(0, 5).map(s => {
    const ts = s.created_at ? new Date(s.created_at * 1000).toLocaleString('es') : '—';
    const text = s.summary ? s.summary.slice(0, 100) : (s.text || '').slice(0, 100);
    return `<div class="audit-entry"><span class="ts">${ts}</span> — ${text}</div>`;
  }).join('');
  sections.push(card('Sesiones recientes', [
    row('Total resúmenes', sessions.total_summaries || 0),
    recSessions || '<span class="stat-label">Sin resúmenes aún</span>',
  ].join('')));

  // ── Auditoría PC ──
  const audEntries = (audit.entries || []).slice(0, 8).map(e => {
    const ts = e.timestamp ? new Date(e.timestamp * 1000).toLocaleString('es') : (e.ts ? new Date(e.ts * 1000).toLocaleString('es') : '—');
    const ok = e.success !== false ? '✅' : '❌';
    return `<div class="audit-entry">${ok} <span class="op">${e.op || '?'}</span> <span class="ts">${ts}</span><br><pre>${JSON.stringify(e.params || {}).slice(0, 120)}</pre></div>`;
  }).join('');
  sections.push(card('Auditoría PC Agent', [
    row('Total entradas', audit.total || 0),
    audEntries || '<span class="stat-label">Sin actividad</span>',
  ].join('')));

  document.getElementById('main').innerHTML = sections.join('');
  document.getElementById('loading').style.display = 'none';
  document.getElementById('main').style.display = 'grid';
}

loadAll();
// Auto-refresh cada 60 segundos
setInterval(loadAll, 60000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_html() -> HTMLResponse:
    """Panel de control visual de Lilith."""
    return HTMLResponse(content=_DASHBOARD_HTML, status_code=200)
