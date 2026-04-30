"""
TrafficTracker - Rastreador de flujos de requests entre agentes y reinos.

Registra delegaciones directas y orquestadas para visualización
en diagramas Sankey y grafos de flujo.
"""
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TrafficTracker:
    """
    Tracker en memoria de flujos de tráfico entre nodos del sistema.
    Ventana deslizante configurable (por defecto últimos 2000 flujos).
    """

    def __init__(self, max_entries: int = 2000):
        self.max_entries = max_entries
        self._flows: List[Dict] = []

    def record_flow(self, source: str, target: str, flow_type: str = "direct") -> None:
        """
        Registra un flujo de request de source a target.

        Args:
            source: Nodo origen (e.g., 'discord', 'crystal', 'albedo', 'lilith')
            target: Nodo destino (e.g., 'delegate_eva', 'delegate_adan')
            flow_type: Tipo de flujo ('direct', 'orchestrated', 'swarm')
        """
        self._flows.append(
            {
                "timestamp": time.time(),
                "source": source,
                "target": target,
                "flow_type": flow_type,
            }
        )
        if len(self._flows) > self.max_entries:
            self._flows = self._flows[-self.max_entries :]

    def get_sankey_data(self, window_seconds: float = 300) -> Dict:
        """
        Devuelve datos agregados para un diagrama Sankey.

        Returns:
            {
                "nodes": [{"id": str}, ...],
                "links": [{"source": str, "target": str, "value": int}, ...]
            }
        """
        cutoff = time.time() - window_seconds
        recent = [f for f in self._flows if f["timestamp"] > cutoff]

        nodes = set()
        links: Dict[tuple, int] = defaultdict(int)
        for f in recent:
            nodes.add(f["source"])
            nodes.add(f["target"])
            links[(f["source"], f["target"])] += 1

        return {
            "nodes": [{"id": n} for n in sorted(nodes)],
            "links": [
                {"source": s, "target": t, "value": v}
                for (s, t), v in sorted(links.items())
            ],
        }

    def get_flows(self, window_seconds: Optional[float] = None) -> List[Dict]:
        """Devuelve los flujos raw, opcionalmente filtrados por ventana temporal."""
        if window_seconds is None:
            return list(self._flows)
        cutoff = time.time() - window_seconds
        return [f for f in self._flows if f["timestamp"] > cutoff]

    def get_stats(self) -> Dict:
        """Resumen del tracker."""
        return {
            "total_flows": len(self._flows),
            "max_entries": self.max_entries,
        }


# Singleton global
_traffic_tracker: Optional[TrafficTracker] = None


def get_traffic_tracker() -> TrafficTracker:
    """Obtener instancia singleton del TrafficTracker."""
    global _traffic_tracker
    if _traffic_tracker is None:
        _traffic_tracker = TrafficTracker()
    return _traffic_tracker
