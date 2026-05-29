"""
MuninnDB — Edges / Relaciones entre conceptos.
Almacena aristas dirigidas (source → target, tipo, peso) en JSONL local.
Permite razonar sobre relaciones: "tool A se usa con B", "topic X implica Y", etc.
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("lilith.muninn_edges")

_DEFAULT_DATA_DIR = "Data"
_EDGES_FILE = "muninn_edges.jsonl"


class EdgeManager:
    """
    Gestiona un grafo de relaciones entre conceptos como JSONL local.
    Cada arista: {source, target, edge_type, weight, created_at, updated_at, metadata}
    """

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self._path = self.base_path / _DEFAULT_DATA_DIR / _EDGES_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # ─── I/O ──────────────────────────────────────────────────────────────────

    def _load(self) -> List[Dict]:
        if not self._path.exists():
            return []
        edges = []
        try:
            with open(self._path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            edges.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.warning("muninn_edges: error al leer %s: %s", self._path, e)
        return edges

    def _save(self, edges: List[Dict]) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                for edge in edges:
                    f.write(json.dumps(edge, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("muninn_edges: error al guardar: %s", e)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _edge_key(source: str, target: str, edge_type: str) -> str:
        return f"{source}||{target}||{edge_type}"

    def _find_edge(
        self, edges: List[Dict], source: str, target: str, edge_type: str
    ) -> Optional[Dict]:
        key = self._edge_key(source, target, edge_type)
        for e in edges:
            if self._edge_key(e["source"], e["target"], e["edge_type"]) == key:
                return e
        return None

    # ─── API pública ──────────────────────────────────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Añade o refuerza una arista. Si ya existe la misma (source, target, edge_type),
        incrementa el peso en `weight` en lugar de duplicar.
        """
        source, target, edge_type = source.strip(), target.strip(), edge_type.strip()
        if not source or not target or not edge_type:
            return
        edges = self._load()
        existing = self._find_edge(edges, source, target, edge_type)
        now = time.time()
        if existing:
            existing["weight"] = round(existing.get("weight", 1.0) + weight, 4)
            existing["updated_at"] = now
            if metadata:
                existing.setdefault("metadata", {}).update(metadata)
        else:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "edge_type": edge_type,
                    "weight": round(weight, 4),
                    "created_at": now,
                    "updated_at": now,
                    "metadata": metadata or {},
                }
            )
        self._save(edges)

    def strengthen_edge(
        self, source: str, target: str, edge_type: str, delta: float = 0.1
    ) -> bool:
        """Incrementa el peso de una arista existente. Retorna True si existía."""
        edges = self._load()
        existing = self._find_edge(edges, source, target, edge_type)
        if not existing:
            return False
        existing["weight"] = round(existing.get("weight", 1.0) + delta, 4)
        existing["updated_at"] = time.time()
        self._save(edges)
        return True

    def get_edges(
        self,
        source: Optional[str] = None,
        target: Optional[str] = None,
        edge_type: Optional[str] = None,
        min_weight: float = 0.0,
    ) -> List[Dict]:
        """Devuelve aristas filtradas, ordenadas por peso descendente."""
        edges = self._load()
        result = []
        for e in edges:
            if source and e.get("source") != source:
                continue
            if target and e.get("target") != target:
                continue
            if edge_type and e.get("edge_type") != edge_type:
                continue
            if e.get("weight", 0) < min_weight:
                continue
            result.append(e)
        result.sort(key=lambda x: x.get("weight", 0), reverse=True)
        return result

    def search_related(
        self, concept: str, max_hops: int = 1, min_weight: float = 0.3
    ) -> List[Dict]:
        """
        BFS de hasta `max_hops` saltos desde `concept` (como source).
        Devuelve todas las aristas atravesadas.
        """
        visited_nodes = {concept}
        frontier = [concept]
        found_edges: List[Dict] = []
        for _ in range(max_hops):
            next_frontier = []
            for node in frontier:
                for e in self.get_edges(source=node, min_weight=min_weight):
                    found_edges.append(e)
                    target = e["target"]
                    if target not in visited_nodes:
                        visited_nodes.add(target)
                        next_frontier.append(target)
            frontier = next_frontier
            if not frontier:
                break
        return found_edges

    def format_for_context(self, edges: List[Dict], max_edges: int = 5) -> str:
        """Formatea aristas como bloque de texto para inyección en prompt."""
        if not edges:
            return ""
        lines = []
        for e in edges[:max_edges]:
            src = e.get("source", "?")
            tgt = e.get("target", "?")
            etype = e.get("edge_type", "→")
            w = e.get("weight", 1.0)
            lines.append(f"  {src} —[{etype} w={w:.2f}]→ {tgt}")
        return "[Relaciones conocidas]\n" + "\n".join(lines)

    def record_plan_edges(self, steps: List[Dict], user_intent: str) -> None:
        """
        Registra aristas a partir de los steps de un plan:
        - user_intent → tool_name (edge_type="intent_uses_tool")
        - tool_N → tool_N+1 (edge_type="tool_sequence")
        """
        intent_short = user_intent[:80].strip() or "unknown_intent"
        tool_names = [str(s.get("tool_name", "unknown")).strip() for s in (steps or [])]
        for tool in tool_names:
            self.add_edge(intent_short, tool, "intent_uses_tool", weight=0.5)
        for i in range(len(tool_names) - 1):
            self.add_edge(tool_names[i], tool_names[i + 1], "tool_sequence", weight=0.5)

    def record_confirmation_edge(
        self, action: str, plan_summary: str, tool_names: List[str]
    ) -> None:
        """
        Registra edges de confirmación:
        - plan_summary → "owner_approved"/"owner_denied" (edge_type="confirmation")
        - cada tool → "approved"/"denied" (edge_type="tool_outcome")
        """
        outcome = "owner_approved" if action == "authorize" else "owner_denied"
        tool_outcome = "approved" if action == "authorize" else "denied"
        plan_short = plan_summary[:80].strip() or "unknown_plan"
        self.add_edge(plan_short, outcome, "confirmation", weight=1.0)
        for tool in tool_names:
            if tool:
                self.add_edge(tool, tool_outcome, "tool_outcome", weight=0.5)


# ─── Singleton ────────────────────────────────────────────────────────────────

_edge_managers: Dict[str, "EdgeManager"] = {}


def get_edge_manager(base_path: Path) -> EdgeManager:
    key = str(base_path)
    if key not in _edge_managers:
        _edge_managers[key] = EdgeManager(base_path)
    return _edge_managers[key]
