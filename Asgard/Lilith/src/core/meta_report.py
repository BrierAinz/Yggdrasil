"""
Lilith 3.5 D.2 — Meta-informe de configuración y uso.
Lee decision_audit y memory.json; devuelve resumen (use_learned_plan %, sugerencias). Sin auto-aplicar cambios.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MetaReport")

DEFAULT_BASE: Optional[Path] = None


def _base() -> Path:
    global DEFAULT_BASE
    if DEFAULT_BASE is None:
        DEFAULT_BASE = Path(__file__).resolve().parent.parent.parent.parent
    return DEFAULT_BASE


def build_meta_report(
    base_path: Optional[Path] = None, audit_limit: int = 1000
) -> Dict[str, Any]:
    """
    Genera el meta-informe: conteo por decision_source, config actual, sugerencias.
    No modifica memory.json.
    """
    base = Path(base_path) if base_path else _base()
    report: Dict[str, Any] = {
        "sources": {},
        "config": {},
        "suggestions": [],
        "total_decisions": 0,
    }
    try:
        from src.core.json_safe import safe_load, safe_load_lines

        cfg = safe_load(base / "Config" / "memory.json", default={})
        if isinstance(cfg, dict):
            report["config"] = {
                k: v for k, v in cfg.items() if isinstance(v, (str, int, float, bool))
            }
        audit_path = base / "Data" / "decision_audit.jsonl"
        if audit_path.exists():
            lines = safe_load_lines(audit_path, default=[])
            total = 0
            for entry in lines[-audit_limit:]:
                if not isinstance(entry, dict):
                    continue
                total += 1
                src = (entry.get("decision_source") or "unknown").strip()
                report["sources"][src] = report["sources"].get(src, 0) + 1
            report["total_decisions"] = total
            if total > 0:
                pct_learned = (report["sources"].get("learned_plan", 0) / total) * 100
                pct_intent = (report["sources"].get("intent_patterns", 0) / total) * 100
                pct_fallback = (
                    report["sources"].get("fallback_lucifer", 0) / total
                ) * 100
                if pct_fallback > 50:
                    report["suggestions"].append(
                        "Más del 50% son fallback; considera añadir intenciones en intent_patterns.json o entrenar patrones."
                    )
                if pct_learned < 10 and total > 20:
                    report["suggestions"].append(
                        "Pocos planes aprendidos; use_learned_plan podría estar desactivado o hay pocos patrones procedimentales."
                    )
    except Exception as e:
        logger.warning("MetaReport: %s", e)
        report["error"] = str(e)
    return report


def write_meta_report(base_path: Optional[Path] = None) -> Path:
    """Escribe el meta-informe en Data/meta_report.json. Devuelve la ruta del archivo."""
    base = Path(base_path) if base_path else _base()
    path = base / "Data" / "meta_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    report = build_meta_report(base_path=base)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path
