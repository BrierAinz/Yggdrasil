"""
ConflictResolver - Resolucion de conflictos entre agentes
========================================================
Detecta, analiza y resuelve conflictos de archivos modificados
por multiples agentes del swarm.
"""
import difflib
import re
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class ConflictSeverity(Enum):
    """Nivel de severidad del conflicto."""

    NONE = "none"
    LOW = "low"  # Cambios en diferentes secciones, auto-mergeable
    MEDIUM = "medium"  # Posible solapamiento, revisar
    HIGH = "high"  # Conflicto claro, intervencion requerida


class ConflictResolution(Enum):
    """Resultado de la resolucion."""

    AUTO_MERGED = "auto_merged"
    MANUAL_REQUIRED = "manual_required"
    DISCARDED = "discarded"
    PENDING = "pending"


@dataclass
class Conflict:
    """Representa un conflicto detectado."""

    file_path: str
    agent_ids: List[str]
    diffs: List[str]
    severity: ConflictSeverity
    resolution: ConflictResolution = ConflictResolution.PENDING
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    merge_result: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "file": self.file_path,
            "agents": self.agent_ids,
            "severity": self.severity.value,
            "resolution": self.resolution.value,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "error": self.error_message,
        }


class ConflictResolver:
    """Resuelve conflictos entre agentes del swarm."""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo = repo_path or Path.cwd()
        self.conflicts: List[Conflict] = []
        self._lock = threading.RLock()
        self._resolved_count = 0
        self._auto_merged_count = 0

    def detect_conflicts(
        self, file_modifications: Dict[str, List[Tuple[str, str]]]
    ) -> List[Conflict]:
        """
        Detecta conflictos a partir de modificaciones de archivos.

        Args:
            file_modifications: {file_path: [(agent_id, diff_content), ...]}

        Returns:
            Lista de Conflictos detectados.
        """
        new_conflicts = []

        for file_path, modifications in file_modifications.items():
            if len(modifications) < 2:
                continue  # Solo un agente modifico, no hay conflicto

            agent_ids = [m[0] for m in modifications]
            diffs = [m[1] for m in modifications]

            # Analizar severidad
            severity = self._analyze_severity(file_path, diffs)

            conflict = Conflict(
                file_path=file_path,
                agent_ids=agent_ids,
                diffs=diffs,
                severity=severity,
            )

            with self._lock:
                # Evitar duplicados
                existing = self._find_existing(file_path, agent_ids)
                if existing:
                    existing.diffs = diffs
                    existing.severity = severity
                else:
                    self.conflicts.append(conflict)
                    new_conflicts.append(conflict)

        return new_conflicts

    def _find_existing(
        self, file_path: str, agent_ids: List[str]
    ) -> Optional[Conflict]:
        """Busca conflicto existente para mismo archivo y agentes."""
        ids_set = set(agent_ids)
        for c in self.conflicts:
            if c.file_path == file_path and not c.resolved_at:
                if set(c.agent_ids) == ids_set:
                    return c
        return None

    def _analyze_severity(self, file_path: str, diffs: List[str]) -> ConflictSeverity:
        """Analiza la severidad del conflicto."""
        if len(diffs) < 2:
            return ConflictSeverity.NONE

        # Extraer lineas modificadas de cada diff
        modified_lines_list = []
        for diff in diffs:
            lines = self._extract_modified_lines(diff)
            modified_lines_list.append(set(lines))

        # Verificar solapamiento
        overlap_found = False
        max_overlap_ratio = 0.0

        for i in range(len(modified_lines_list)):
            for j in range(i + 1, len(modified_lines_list)):
                set_i = modified_lines_list[i]
                set_j = modified_lines_list[j]
                if set_i and set_j:
                    intersection = set_i & set_j
                    union = set_i | set_j
                    if intersection and union:
                        overlap_ratio = len(intersection) / len(union)
                        max_overlap_ratio = max(max_overlap_ratio, overlap_ratio)
                        if overlap_ratio > 0.3:
                            overlap_found = True

        if not overlap_found or max_overlap_ratio < 0.1:
            return ConflictSeverity.LOW
        elif max_overlap_ratio < 0.6:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.HIGH

    def _extract_modified_lines(self, diff: str) -> List[int]:
        """Extrae numeros de linea modificadas de un diff."""
        lines = []
        for line in diff.split("\n"):
            # Formato diff unificado: @@ -start,count +start,count @@
            match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                start = int(match.group(3))
                count = int(match.group(4)) if match.group(4) else 1
                lines.extend(range(start, start + count))
        return lines

    def attempt_auto_merge(self, conflict: Conflict) -> bool:
        """
        Intenta auto-merge de un conflicto.

        Returns:
            True si se resolvio automaticamente.
        """
        if conflict.severity == ConflictSeverity.HIGH:
            conflict.resolution = ConflictResolution.MANUAL_REQUIRED
            conflict.error_message = "Severidad alta, requiere intervencion manual"
            return False

        # Para severidad baja: intentar merge simple
        if conflict.severity == ConflictSeverity.LOW:
            # Verificar que los cambios estan en secciones diferentes
            if self._can_simple_merge(conflict.diffs):
                merged = self._simple_merge(conflict.diffs)
                if merged is not None:
                    conflict.merge_result = merged
                    conflict.resolution = ConflictResolution.AUTO_MERGED
                    conflict.resolved_at = time.time()
                    with self._lock:
                        self._resolved_count += 1
                        self._auto_merged_count += 1
                    return True

        conflict.resolution = ConflictResolution.MANUAL_REQUIRED
        conflict.error_message = "No se pudo resolver automaticamente"
        return False

    def _can_simple_merge(self, diffs: List[str]) -> bool:
        """Verifica si los diffs pueden mergearse sin solapamiento."""
        # Extraer rangos de lineas modificadas
        ranges = []
        for diff in diffs:
            lines = self._extract_modified_lines(diff)
            if lines:
                ranges.append((min(lines), max(lines)))

        if not ranges:
            return True

        # Verificar que los rangos no se solapan
        ranges.sort()
        for i in range(len(ranges) - 1):
            if ranges[i][1] >= ranges[i + 1][0]:
                return False
        return True

    def _simple_merge(self, diffs: List[str]) -> Optional[str]:
        """Realiza merge simple de diffs no solapados."""
        # Implementacion basica: concatenar los hunks de diff
        # En una implementacion real, aplicaria los patches secuencialmente
        all_hunks = []
        for diff in diffs:
            hunks = self._split_into_hunks(diff)
            all_hunks.extend(hunks)

        # Ordenar hunks por linea de inicio
        all_hunks.sort(key=lambda h: h["start_line"])

        # Verificar que no hay solapamiento
        for i in range(len(all_hunks) - 1):
            if all_hunks[i]["end_line"] >= all_hunks[i + 1]["start_line"]:
                return None

        # Reconstruir diff mergeado
        merged_lines = []
        for hunk in all_hunks:
            merged_lines.extend(hunk["lines"])

        return "\n".join(merged_lines) if merged_lines else None

    def _split_into_hunks(self, diff: str) -> List[Dict]:
        """Divide un diff en hunks individuales."""
        hunks = []
        current_hunk = None

        for line in diff.split("\n"):
            match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                if current_hunk:
                    hunks.append(current_hunk)
                start = int(match.group(3))
                current_hunk = {
                    "start_line": start,
                    "end_line": start,
                    "lines": [line],
                }
            elif current_hunk:
                current_hunk["lines"].append(line)
                # Actualizar end_line basado en lineas agregadas
                if line.startswith("+") and not line.startswith("+++"):
                    current_hunk["end_line"] += 1

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    def resolve_manually(
        self,
        conflict: Conflict,
        resolution: ConflictResolution,
        merge_result: Optional[str] = None,
    ) -> bool:
        """Resuelve un conflicto manualmente."""
        with self._lock:
            conflict.resolution = resolution
            conflict.resolved_at = time.time()
            if merge_result:
                conflict.merge_result = merge_result
            self._resolved_count += 1
            if resolution == ConflictResolution.AUTO_MERGED:
                self._auto_merged_count += 1
            return True

    def get_pending_conflicts(self) -> List[Conflict]:
        """Retorna conflictos pendientes."""
        with self._lock:
            return [
                c for c in self.conflicts if c.resolution == ConflictResolution.PENDING
            ]

    def get_stats(self) -> Dict:
        """Estadisticas de resolucion."""
        with self._lock:
            pending = len(
                [
                    c
                    for c in self.conflicts
                    if c.resolution == ConflictResolution.PENDING
                ]
            )
            resolved = len([c for c in self.conflicts if c.resolved_at is not None])
            auto = len(
                [
                    c
                    for c in self.conflicts
                    if c.resolution == ConflictResolution.AUTO_MERGED
                ]
            )
            manual = len(
                [
                    c
                    for c in self.conflicts
                    if c.resolution == ConflictResolution.MANUAL_REQUIRED
                ]
            )

            return {
                "total_conflicts": len(self.conflicts),
                "pending": pending,
                "resolved": resolved,
                "auto_merged": auto,
                "manual_required": manual,
                "auto_merge_rate": auto / resolved if resolved > 0 else 0.0,
            }

    def clear_resolved(self):
        """Limpia conflictos resueltos antiguos."""
        with self._lock:
            cutoff = time.time() - 3600  # 1 hora
            self.conflicts = [
                c
                for c in self.conflicts
                if c.resolution == ConflictResolution.PENDING
                or (c.resolved_at and c.resolved_at > cutoff)
            ]
