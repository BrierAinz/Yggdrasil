"""
PatternLearner - MÃ³dulo de aprendizaje de patrones para Lilith

Detecta hÃ¡bitos del desarrollador:
- Secuencias de comandos (despuÃ©s de X, siempre hace Y)
- Patrones temporales (cada N minutos, a cierta hora)
- Patrones contextuales (en proyecto tipo X, usa herramienta Y)
- Frecuencias de uso de comandos/tools

Usa el histÃ³rico para predecir prÃ³ximas acciones.
"""

import hashlib
import json
import logging
import os
import threading
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("PatternLearner")


@dataclass
class Action:
    """Representa una acciÃ³n del usuario"""

    timestamp: str
    action_type: str  # "command", "tool", "file_edit", "git_op"
    details: str  # Comando completo o descripciÃ³n
    context: Dict[str, Any]  # Proyecto, archivo, branch, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "details": self.details,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Action":
        return cls(
            timestamp=data["timestamp"],
            action_type=data["action_type"],
            details=data["details"],
            context=data.get("context", {}),
        )

    def fingerprint(self) -> str:
        """Generar fingerprint Ãºnico de la acciÃ³n"""
        # Simplificar detalles para agrupar acciones similares
        simplified = self._simplify_details()
        key = f"{self.action_type}:{simplified}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _simplify_details(self) -> str:
        """Simplificar detalles para pattern matching"""
        details = self.details.lower()

        if self.action_type == "command":
            # Extraer comando base (sin argumentos especÃ­ficos)
            parts = details.split()
            if parts:
                base = parts[0]
                # Normalizar comandos git
                if base == "git" and len(parts) > 1:
                    return f"git {parts[1]}"
                return base

        elif self.action_type == "file_edit":
            # Extraer extensiÃ³n del archivo
            if "." in details:
                return f"edit *.{details.split('.')[-1]}"
            return "edit file"

        elif self.action_type == "tool":
            # Tool name sin parÃ¡metros
            return details.split()[0] if details else "tool"

        return details[:50]


@dataclass
class Pattern:
    """PatrÃ³n detectado"""

    pattern_id: str
    pattern_type: str  # "sequence", "temporal", "contextual", "frequency"
    description: str
    confidence: float  # 0.0 - 1.0
    occurrences: int
    first_seen: str
    last_seen: str
    actions: List[str]  # Fingerprints de acciones
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "actions": self.actions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Pattern":
        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=data["pattern_type"],
            description=data["description"],
            confidence=data["confidence"],
            occurrences=data["occurrences"],
            first_seen=data["first_seen"],
            last_seen=data["last_seen"],
            actions=data["actions"],
            metadata=data.get("metadata", {}),
        )


class PatternLearner:
    """
    Aprende patrones de comportamiento del desarrollador.

    Detecta:
    - Secuencias: DespuÃ©s de X, siempre hace Y
    - Temporales: Cada N minutos, a cierta hora
    - Contextuales: En proyecto tipo X, usa Y
    - Frecuencia: QuÃ© comandos/tools usa mÃ¡s
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or Path.home() / ".Lilith" / "patterns")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.actions_file = self.storage_path / "actions.jsonl"
        self.patterns_file = self.storage_path / "patterns.json"

        # Buffer de acciones recientes (para anÃ¡lisis en tiempo real)
        self.recent_actions: deque = deque(maxlen=100)
        self.action_history: List[Action] = []
        self.patterns: Dict[str, Pattern] = {}

        # Contadores
        self.action_counts: Dict[str, int] = defaultdict(int)
        self.sequence_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        self._lock = threading.Lock()

        # Cargar datos existentes
        self._load_patterns()
        self._load_recent_actions()

        logger.info(
            f"PatternLearner initialized. Loaded {len(self.patterns)} patterns."
        )

    def record_action(
        self, action_type: str, details: str, context: Optional[Dict] = None
    ) -> bool:
        """
        Registrar una acciÃ³n del usuario

        Args:
            action_type: Tipo de acciÃ³n (command, tool, file_edit, git_op)
            details: Detalles de la acciÃ³n
            context: Contexto adicional (proyecto, archivo, etc.)

        Returns:
            True si se registrÃ³ exitosamente
        """
        action = Action(
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            details=details,
            context=context or {},
        )

        with self._lock:
            # AÃ±adir a buffer e historial
            self.recent_actions.append(action)
            self.action_history.append(action)

            # Actualizar contadores
            fingerprint = action.fingerprint()
            self.action_counts[fingerprint] += 1

            # Detectar secuencias (pares de acciones consecutivas)
            if len(self.recent_actions) >= 2:
                prev_action = list(self.recent_actions)[-2]
                prev_fp = prev_action.fingerprint()
                seq_key = (prev_fp, fingerprint)
                self.sequence_counts[seq_key] += 1

            # Guardar a disco (append)
            self._append_action(action)

            # Analizar patrones periÃ³dicamente
            if len(self.action_history) % 10 == 0:
                self._analyze_patterns()

        return True

    def _append_action(self, action: Action):
        """Guardar acciÃ³n a disco"""
        try:
            with open(self.actions_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(action.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error saving action: {e}")

    def _load_recent_actions(self, limit: int = 1000):
        """Cargar acciones recientes"""
        if not self.actions_file.exists():
            return

        try:
            with open(self.actions_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        data = json.loads(line.strip())
                        action = Action.from_dict(data)
                        self.action_history.append(action)
                        self.recent_actions.append(action)

                        # Reconstruir contadores
                        fp = action.fingerprint()
                        self.action_counts[fp] += 1
                    except:
                        continue
        except Exception as e:
            logger.error(f"Error loading actions: {e}")

    def _load_patterns(self):
        """Cargar patrones detectados"""
        if not self.patterns_file.exists():
            return

        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for pattern_data in data:
                    pattern = Pattern.from_dict(pattern_data)
                    self.patterns[pattern.pattern_id] = pattern
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")

    def _save_patterns(self):
        """Guardar patrones a disco"""
        try:
            data = [p.to_dict() for p in self.patterns.values()]
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _analyze_patterns(self):
        """Analizar y detectar nuevos patrones"""
        # Analizar secuencias frecuentes
        self._detect_sequence_patterns()

        # Analizar frecuencias
        self._detect_frequency_patterns()

        # Analizar patrones temporales
        self._detect_temporal_patterns()

        # Analizar patrones contextuales
        self._detect_contextual_patterns()

        # Guardar patrones actualizados
        self._save_patterns()

    def _detect_sequence_patterns(self):
        """Detectar secuencias de acciones frecuentes"""
        # Buscar pares de acciones que ocurran juntas frecuentemente
        for (action_a, action_b), count in self.sequence_counts.items():
            if count >= 3:  # MÃ­nimo 3 ocurrencias
                confidence = min(count / 10, 1.0)  # Max confianza a 10 ocurrencias

                pattern_id = f"seq_{action_a}_{action_b}"

                # Buscar nombres legibles
                action_a_name = self._get_action_name(action_a)
                action_b_name = self._get_action_name(action_b)

                description = (
                    f"DespuÃ©s de '{action_a_name}', usualmente hace '{action_b_name}'"
                )

                if pattern_id in self.patterns:
                    # Actualizar patrÃ³n existente
                    pattern = self.patterns[pattern_id]
                    pattern.occurrences = count
                    pattern.confidence = confidence
                    pattern.last_seen = datetime.now().isoformat()
                else:
                    # Crear nuevo patrÃ³n
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        pattern_type="sequence",
                        description=description,
                        confidence=confidence,
                        occurrences=count,
                        first_seen=datetime.now().isoformat(),
                        last_seen=datetime.now().isoformat(),
                        actions=[action_a, action_b],
                        metadata={"action_a": action_a_name, "action_b": action_b_name},
                    )
                    self.patterns[pattern_id] = pattern
                    logger.info(f"New sequence pattern detected: {description}")

    def _detect_frequency_patterns(self):
        """Detectar acciones mÃ¡s frecuentes"""
        # Top acciones por frecuencia
        sorted_actions = sorted(
            self.action_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        for fingerprint, count in sorted_actions:
            if count >= 5:
                pattern_id = f"freq_{fingerprint}"
                action_name = self._get_action_name(fingerprint)

                description = f"Usa frecuentemente: {action_name}"

                if pattern_id not in self.patterns:
                    pattern = Pattern(
                        pattern_id=pattern_id,
                        pattern_type="frequency",
                        description=description,
                        confidence=min(count / 20, 1.0),
                        occurrences=count,
                        first_seen=datetime.now().isoformat(),
                        last_seen=datetime.now().isoformat(),
                        actions=[fingerprint],
                        metadata={"action_name": action_name, "count": count},
                    )
                    self.patterns[pattern_id] = pattern

    def _detect_temporal_patterns(self):
        """Detectar patrones temporales"""
        if len(self.action_history) < 20:
            return

        # Analizar intervalos entre acciones similares
        action_times: Dict[str, List[datetime]] = defaultdict(list)

        for action in self.action_history[-100:]:  # Ãšltimas 100 acciones
            fp = action.fingerprint()
            try:
                ts = datetime.fromisoformat(action.timestamp)
                action_times[fp].append(ts)
            except:
                continue

        # Buscar acciones con intervalos regulares
        for fingerprint, times in action_times.items():
            if len(times) >= 3:
                intervals = []
                for i in range(1, len(times)):
                    interval = (times[i] - times[i - 1]).total_seconds() / 60  # minutos
                    intervals.append(interval)

                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    variance = sum((x - avg_interval) ** 2 for x in intervals) / len(
                        intervals
                    )

                    # Si la varianza es baja, es un patrÃ³n temporal regular
                    if (
                        variance < avg_interval * 0.5 and avg_interval > 5
                    ):  # > 5 minutos
                        pattern_id = f"temp_{fingerprint}"
                        action_name = self._get_action_name(fingerprint)

                        description = f"Usa '{action_name}' aproximadamente cada {int(avg_interval)} minutos"

                        if pattern_id not in self.patterns:
                            pattern = Pattern(
                                pattern_id=pattern_id,
                                pattern_type="temporal",
                                description=description,
                                confidence=0.7,
                                occurrences=len(times),
                                first_seen=times[0].isoformat(),
                                last_seen=times[-1].isoformat(),
                                actions=[fingerprint],
                                metadata={
                                    "action_name": action_name,
                                    "avg_interval_minutes": avg_interval,
                                    "variance": variance,
                                },
                            )
                            self.patterns[pattern_id] = pattern

    def _detect_contextual_patterns(self):
        """Detectar patrones segÃºn contexto (proyecto, tipo)"""
        context_actions: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        for action in self.action_history:
            project_type = action.context.get("project_type", "unknown")
            fingerprint = action.fingerprint()
            context_actions[project_type][fingerprint] += 1

        # Para cada tipo de proyecto, encontrar acciones caracterÃ­sticas
        for project_type, actions in context_actions.items():
            if project_type == "unknown":
                continue

            total = sum(actions.values())
            for fingerprint, count in actions.items():
                ratio = count / total if total > 0 else 0

                # Si usa esta acciÃ³n >50% del tiempo en este tipo de proyecto
                if ratio > 0.5 and count >= 3:
                    pattern_id = f"ctx_{project_type}_{fingerprint}"
                    action_name = self._get_action_name(fingerprint)

                    description = f"En proyectos {project_type}, usa frecuentemente: {action_name}"

                    if pattern_id not in self.patterns:
                        pattern = Pattern(
                            pattern_id=pattern_id,
                            pattern_type="contextual",
                            description=description,
                            confidence=ratio,
                            occurrences=count,
                            first_seen=datetime.now().isoformat(),
                            last_seen=datetime.now().isoformat(),
                            actions=[fingerprint],
                            metadata={
                                "project_type": project_type,
                                "action_name": action_name,
                                "usage_ratio": ratio,
                            },
                        )
                        self.patterns[pattern_id] = pattern

    def _get_action_name(self, fingerprint: str) -> str:
        """Obtener nombre legible de una acciÃ³n por fingerprint"""
        # Buscar en historial
        for action in reversed(self.action_history):
            if action.fingerprint() == fingerprint:
                return f"{action.action_type}: {action._simplify_details()}"
        return fingerprint[:20]

    def predict_next_action(
        self,
        last_action_type: Optional[str] = None,
        last_action_details: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Predecir prÃ³ximas acciones basadas en patrones

        Returns:
            Lista de predicciones ordenadas por confianza
        """
        predictions = []

        with self._lock:
            # 1. Buscar patrones de secuencia
            if last_action_details:
                last_action = Action(
                    timestamp=datetime.now().isoformat(),
                    action_type=last_action_type or "unknown",
                    details=last_action_details,
                    context=context or {},
                )
                last_fp = last_action.fingerprint()

                for pattern in self.patterns.values():
                    if pattern.pattern_type == "sequence" and len(pattern.actions) >= 2:
                        if pattern.actions[0] == last_fp:
                            next_fp = pattern.actions[1]
                            next_name = self._get_action_name(next_fp)
                            predictions.append(
                                {
                                    "action": next_name,
                                    "confidence": pattern.confidence,
                                    "reason": f"DespuÃ©s de '{last_action._simplify_details()}', usualmente hace esto",
                                    "pattern_type": "sequence",
                                    "occurrences": pattern.occurrences,
                                }
                            )

            # 2. Buscar patrones contextuales
            if context and context.get("project_type"):
                project_type = context["project_type"]
                for pattern in self.patterns.values():
                    if pattern.pattern_type == "contextual":
                        if pattern.metadata.get("project_type") == project_type:
                            action_name = pattern.metadata.get("action_name", "unknown")
                            predictions.append(
                                {
                                    "action": action_name,
                                    "confidence": pattern.confidence,
                                    "reason": f"ComÃºn en proyectos {project_type}",
                                    "pattern_type": "contextual",
                                    "occurrences": pattern.occurrences,
                                }
                            )

            # 3. Acciones frecuentes
            for pattern in self.patterns.values():
                if pattern.pattern_type == "frequency":
                    action_name = pattern.metadata.get("action_name", "unknown")
                    # Evitar duplicados
                    if not any(p["action"] == action_name for p in predictions):
                        predictions.append(
                            {
                                "action": action_name,
                                "confidence": pattern.confidence
                                * 0.7,  # Penalizar frecuencia pura
                                "reason": "AcciÃ³n frecuentemente usada",
                                "pattern_type": "frequency",
                                "occurrences": pattern.occurrences,
                            }
                        )

        # Ordenar por confianza
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return predictions[:5]  # Top 5

    def get_patterns(
        self, pattern_type: Optional[str] = None, min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Obtener patrones detectados"""
        patterns = []

        for pattern in self.patterns.values():
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
            if pattern.confidence < min_confidence:
                continue
            patterns.append(pattern.to_dict())

        # Ordenar por confianza
        patterns.sort(key=lambda x: x["confidence"], reverse=True)

        return patterns

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadÃ­sticas del learner"""
        return {
            "total_actions_recorded": len(self.action_history),
            "unique_actions": len(self.action_counts),
            "patterns_detected": len(self.patterns),
            "patterns_by_type": {
                "sequence": len(
                    [p for p in self.patterns.values() if p.pattern_type == "sequence"]
                ),
                "temporal": len(
                    [p for p in self.patterns.values() if p.pattern_type == "temporal"]
                ),
                "contextual": len(
                    [
                        p
                        for p in self.patterns.values()
                        if p.pattern_type == "contextual"
                    ]
                ),
                "frequency": len(
                    [p for p in self.patterns.values() if p.pattern_type == "frequency"]
                ),
            },
            "top_actions": sorted(
                [
                    {"action": self._get_action_name(fp), "count": count}
                    for fp, count in self.action_counts.items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )[:10],
        }


# Singleton
_pattern_learner: Optional[PatternLearner] = None


def get_pattern_learner() -> PatternLearner:
    """Obtener instancia singleton"""
    global _pattern_learner
    if _pattern_learner is None:
        _pattern_learner = PatternLearner()
    return _pattern_learner


# === Testing ===
if __name__ == "__main__":
    print("=" * 60)
    print("PatternLearner - Test Suite")
    print("=" * 60)

    learner = get_pattern_learner()

    # Simular acciones
    print("\n[Test 1] Registrar acciones de ejemplo")

    # Secuencia: editar archivo â†’ ejecutar tests
    for i in range(5):
        learner.record_action("file_edit", "models.py", {"project_type": "python"})
        learner.record_action("command", "pytest tests/", {"project_type": "python"})

    # Secuencia: git status â†’ git add
    for i in range(3):
        learner.record_action("git_op", "git status", {"project_type": "python"})
        learner.record_action("git_op", "git add .", {"project_type": "python"})

    print("âœ“ Recorded 16 actions")

    # Test 2: Analizar patrones
    print("\n[Test 2] Analizar patrones")
    learner._analyze_patterns()
    stats = learner.get_stats()
    print(f"âœ“ Detected {stats['patterns_detected']} patterns")
    print(f"  - Sequence: {stats['patterns_by_type']['sequence']}")
    print(f"  - Contextual: {stats['patterns_by_type']['contextual']}")

    # Test 3: Predecir
    print("\n[Test 3] Predecir prÃ³xima acciÃ³n")
    predictions = learner.predict_next_action(
        last_action_type="file_edit",
        last_action_details="models.py",
        context={"project_type": "python"},
    )
    for pred in predictions[:3]:
        print(f"  - {pred['action']} ({pred['confidence']:.0%} confianza)")
        print(f"    RazÃ³n: {pred['reason']}")

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
