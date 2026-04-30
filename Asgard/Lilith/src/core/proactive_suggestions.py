"""
ProactiveSuggestions - MÃ³dulo de sugerencias proactivas para Lilith

Analiza el contexto y sugiere acciones sin que el usuario pregunte:
- Archivos sin docstring â†’ "Â¿Genero docstring?"
- Muchos archivos modified â†’ "Â¿Commit ahora?"
- Tests fallando â†’ "Â¿Reviso errores?"
- Nuevas dependencias â†’ "Â¿Instalo?"

Integra: FileWatcher + PatternLearner + GitContext
"""

import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ProactiveSuggestions")


class SuggestionPriority(str, Enum):
    """Prioridad de la sugerencia"""

    HIGH = "high"  # Inmediata, requiere atenciÃ³n
    MEDIUM = "medium"  # Importante pero no urgente
    LOW = "low"  # Informativa


class SuggestionType(str, Enum):
    """Tipo de sugerencia"""

    DOCUMENTATION = "documentation"  # Docstrings, README, etc.
    GIT = "git"  # Commit, push, status
    TEST = "test"  # Ejecutar tests
    CODE_QUALITY = "code_quality"  # Lint, format
    DEPENDENCY = "dependency"  # Instalar dependencias
    SECURITY = "security"  # Problemas de seguridad
    PATTERN = "pattern"  # Basada en hÃ¡bitos del usuario
    GENERAL = "general"  # Otras


@dataclass
class Suggestion:
    """Una sugerencia proactiva"""

    suggestion_id: str
    type: SuggestionType
    priority: SuggestionPriority
    title: str
    message: str
    action_command: str  # Comando sugerido
    action_description: str  # DescripciÃ³n de la acciÃ³n
    dismiss_text: str  # Texto del botÃ³n de descartar
    timestamp: str
    context: Dict[str, Any]  # Contexto que disparÃ³ la sugerencia
    shown: bool = False
    dismissed: bool = False
    dismissed_at: Optional[str] = None
    action_taken: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "action_command": self.action_command,
            "action_description": self.action_description,
            "dismiss_text": self.dismiss_text,
            "timestamp": self.timestamp,
            "context": self.context,
            "shown": self.shown,
            "dismissed": self.dismissed,
            "dismissed_at": self.dismissed_at,
            "action_taken": self.action_taken,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Suggestion":
        return cls(
            suggestion_id=data["suggestion_id"],
            type=SuggestionType(data["type"]),
            priority=SuggestionPriority(data["priority"]),
            title=data["title"],
            message=data["message"],
            action_command=data["action_command"],
            action_description=data["action_description"],
            dismiss_text=data["dismiss_text"],
            timestamp=data["timestamp"],
            context=data.get("context", {}),
            shown=data.get("shown", False),
            dismissed=data.get("dismissed", False),
            dismissed_at=data.get("dismissed_at"),
            action_taken=data.get("action_taken", False),
        )


class ProactiveSuggestions:
    """
    Sistema de sugerencias proactivas para Lilith.

    CaracterÃ­sticas:
    - Rate limiting (max 1 sugerencia cada 5 min)
    - PriorizaciÃ³n inteligente
    - Aprendizaje de dismissals (quÃ© sugerencias rechaza)
    - AnÃ¡lisis de contexto en tiempo real
    """

    # Rate limiting
    MIN_INTERVAL_SECONDS = 300  # 5 minutos entre sugerencias
    MAX_SUGGESTIONS_QUEUE = 10

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path or Path.home() / ".Lilith" / "suggestions"
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.suggestions_file = self.storage_path / "suggestions.json"
        self.dismissed_file = self.storage_path / "dismissed_patterns.json"

        # Cola de sugerencias activas
        self.suggestions: Dict[str, Suggestion] = {}
        self.suggestion_queue: List[str] = []  # IDs ordenados por prioridad

        # Rate limiting
        self.last_suggestion_time: Optional[datetime] = None
        self.suggestions_shown_count = 0

        # Aprendizaje de dismissals
        self.dismissed_patterns: Dict[str, int] = {}  # patrÃ³n -> contador

        # Callbacks para notificaciones
        self._on_suggestion_callbacks: List[Callable] = []

        self._lock = threading.Lock()

        # Cargar datos
        self._load_suggestions()
        self._load_dismissed_patterns()

        logger.info("ProactiveSuggestions initialized")

    def _load_suggestions(self):
        """Cargar sugerencias previas"""
        if self.suggestions_file.exists():
            try:
                with open(self.suggestions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sugg_data in data:
                        sugg = Suggestion.from_dict(sugg_data)
                        if not sugg.dismissed and not sugg.action_taken:
                            self.suggestions[sugg.suggestion_id] = sugg
                            self.suggestion_queue.append(sugg.suggestion_id)
            except Exception as e:
                logger.error(f"Error loading suggestions: {e}")

    def _save_suggestions(self):
        """Guardar sugerencias"""
        try:
            data = [s.to_dict() for s in self.suggestions.values()]
            with open(self.suggestions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving suggestions: {e}")

    def _load_dismissed_patterns(self):
        """Cargar patrones de dismissals"""
        if self.dismissed_file.exists():
            try:
                with open(self.dismissed_file, "r", encoding="utf-8") as f:
                    self.dismissed_patterns = json.load(f)
            except Exception as e:
                logger.error(f"Error loading dismissed patterns: {e}")

    def _save_dismissed_patterns(self):
        """Guardar patrones de dismissals"""
        try:
            with open(self.dismissed_file, "w", encoding="utf-8") as f:
                json.dump(self.dismissed_patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving dismissed patterns: {e}")

    def _can_show_suggestion(self) -> bool:
        """Verificar si podemos mostrar una sugerencia (rate limiting)"""
        if self.last_suggestion_time is None:
            return True

        elapsed = (datetime.now() - self.last_suggestion_time).total_seconds()
        return elapsed >= self.MIN_INTERVAL_SECONDS

    def _is_pattern_dismissed(
        self, suggestion_type: SuggestionType, context_key: str
    ) -> bool:
        """Verificar si el usuario ha descartado este patrÃ³n antes"""
        pattern_key = f"{suggestion_type.value}:{context_key}"
        return self.dismissed_patterns.get(pattern_key, 0) >= 3  # 3 strikes

    def _generate_id(self) -> str:
        """Generar ID Ãºnico para sugerencia"""
        return (
            f"sugg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.suggestions)}"
        )

    def add_suggestion(self, suggestion: Suggestion) -> bool:
        """
        AÃ±adir una nueva sugerencia

        Returns:
            True si se aÃ±adiÃ³, False si fue filtrada
        """
        with self._lock:
            # Verificar si ya existe una sugerencia similar
            for existing in self.suggestions.values():
                if (
                    existing.type == suggestion.type
                    and existing.context == suggestion.context
                    and not existing.dismissed
                ):
                    return False  # Duplicado

            # Verificar si el patrÃ³n ha sido descartado mÃºltiples veces
            context_key = suggestion.context.get("key", "general")
            if self._is_pattern_dismissed(suggestion.type, context_key):
                logger.debug(
                    f"Suggestion pattern dismissed too many times: {suggestion.type}"
                )
                return False

            # AÃ±adir a la cola
            self.suggestions[suggestion.suggestion_id] = suggestion
            self._insert_by_priority(suggestion.suggestion_id)

            # Limitar tamaÃ±o de cola
            while len(self.suggestion_queue) > self.MAX_SUGGESTIONS_QUEUE:
                oldest_id = self.suggestion_queue.pop()
                if oldest_id in self.suggestions:
                    del self.suggestions[oldest_id]

            self._save_suggestions()

            # Notificar
            self._notify_new_suggestion(suggestion)

            logger.info(f"Added suggestion: {suggestion.title}")
            return True

    def _insert_by_priority(self, suggestion_id: str):
        """Insertar ID en la cola ordenado por prioridad"""
        suggestion = self.suggestions[suggestion_id]
        priority_order = {
            SuggestionPriority.HIGH: 0,
            SuggestionPriority.MEDIUM: 1,
            SuggestionPriority.LOW: 2,
        }
        sugg_priority = priority_order.get(suggestion.priority, 1)

        insert_pos = len(self.suggestion_queue)
        for i, existing_id in enumerate(self.suggestion_queue):
            existing = self.suggestions[existing_id]
            existing_priority = priority_order.get(existing.priority, 1)
            if sugg_priority < existing_priority:
                insert_pos = i
                break

        self.suggestion_queue.insert(insert_pos, suggestion_id)

    def get_next_suggestion(self) -> Optional[Suggestion]:
        """Obtener la siguiente sugerencia a mostrar"""
        with self._lock:
            if not self._can_show_suggestion():
                return None

            # Buscar la primera sugerencia no mostrada ni descartada
            for sugg_id in self.suggestion_queue:
                suggestion = self.suggestions.get(sugg_id)
                if suggestion and not suggestion.shown and not suggestion.dismissed:
                    suggestion.shown = True
                    self.last_suggestion_time = datetime.now()
                    self.suggestions_shown_count += 1
                    self._save_suggestions()
                    return suggestion

            return None

    def get_pending_suggestions(self, include_shown: bool = False) -> List[Suggestion]:
        """Obtener todas las sugerencias pendientes"""
        with self._lock:
            pending = []
            for sugg_id in self.suggestion_queue:
                suggestion = self.suggestions.get(sugg_id)
                if (
                    suggestion
                    and not suggestion.dismissed
                    and not suggestion.action_taken
                ):
                    if include_shown or not suggestion.shown:
                        pending.append(suggestion)
            return pending

    def dismiss_suggestion(
        self, suggestion_id: str, feedback: Optional[str] = None
    ) -> bool:
        """Descartar una sugerencia"""
        with self._lock:
            if suggestion_id not in self.suggestions:
                return False

            suggestion = self.suggestions[suggestion_id]
            suggestion.dismissed = True
            suggestion.dismissed_at = datetime.now().isoformat()

            # Aprender el patrÃ³n de dismissal
            context_key = suggestion.context.get("key", "general")
            pattern_key = f"{suggestion.type.value}:{context_key}"
            self.dismissed_patterns[pattern_key] = (
                self.dismissed_patterns.get(pattern_key, 0) + 1
            )

            self._save_suggestions()
            self._save_dismissed_patterns()

            logger.info(f"Dismissed suggestion: {suggestion.title}")
            return True

    def mark_action_taken(self, suggestion_id: str) -> bool:
        """Marcar que se tomÃ³ la acciÃ³n sugerida"""
        with self._lock:
            if suggestion_id not in self.suggestions:
                return False

            suggestion = self.suggestions[suggestion_id]
            suggestion.action_taken = True

            self._save_suggestions()

            logger.info(f"Action taken for suggestion: {suggestion.title}")
            return True

    def clear_all(self):
        """Limpiar todas las sugerencias"""
        with self._lock:
            self.suggestions.clear()
            self.suggestion_queue.clear()
            self._save_suggestions()

    def on_suggestion(self, callback: Callable):
        """Registrar callback para nuevas sugerencias"""
        self._on_suggestion_callbacks.append(callback)

    def _notify_new_suggestion(self, suggestion: Suggestion):
        """Notificar nuevas sugerencias"""
        for callback in self._on_suggestion_callbacks:
            try:
                callback(suggestion)
            except Exception as e:
                logger.error(f"Error in suggestion callback: {e}")

    # ===== SUGERENCIAS ESPECÃFICAS =====

    def suggest_docstring(self, file_path: str, function_name: str) -> bool:
        """Sugerir generar docstring"""
        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.DOCUMENTATION,
            priority=SuggestionPriority.LOW,
            title="DocumentaciÃ³n faltante",
            message=f"La funciÃ³n '{function_name}' en '{Path(file_path).name}' no tiene docstring. Â¿La genero?",
            action_command=f"@doc add_docstrings {file_path}",
            action_description="Generar docstring automÃ¡ticamente",
            dismiss_text="Ignorar",
            timestamp=datetime.now().isoformat(),
            context={
                "file": file_path,
                "function": function_name,
                "key": f"docstring:{file_path}",
            },
        )
        return self.add_suggestion(suggestion)

    def suggest_commit(
        self, modified_count: int, suggestion_message: Optional[str] = None
    ) -> bool:
        """Sugerir hacer commit"""
        if modified_count < 5:
            return False

        priority = (
            SuggestionPriority.HIGH
            if modified_count > 20
            else SuggestionPriority.MEDIUM
        )

        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.GIT,
            priority=priority,
            title="Commits pendientes",
            message=f"Tienes {modified_count} archivos modificados sin commit. Â¿Quieres hacer commit ahora?",
            action_command=f"@git commit -m \"{suggestion_message or 'Update files'}\"",
            action_description="Crear commit con archivos staged",
            dismiss_text="MÃ¡s tarde",
            timestamp=datetime.now().isoformat(),
            context={"modified_count": modified_count, "key": "commit_pending"},
        )
        return self.add_suggestion(suggestion)

    def suggest_run_tests(self, modified_test_files: List[str] = None) -> bool:
        """Sugerir ejecutar tests"""
        context_key = (
            "tests:" + ",".join(modified_test_files)
            if modified_test_files
            else "tests:general"
        )

        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.TEST,
            priority=SuggestionPriority.MEDIUM,
            title="Tests pendientes",
            message="Veo que has modificado cÃ³digo. Â¿Quieres ejecutar los tests para verificar que todo funciona?",
            action_command="@run python -m pytest",
            action_description="Ejecutar test suite",
            dismiss_text="Omitir",
            timestamp=datetime.now().isoformat(),
            context={"modified_tests": modified_test_files, "key": context_key},
        )
        return self.add_suggestion(suggestion)

    def suggest_install_dependencies(
        self, dependency_file: str, package_name: Optional[str] = None
    ) -> bool:
        """Sugerir instalar dependencias"""
        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.DEPENDENCY,
            priority=SuggestionPriority.MEDIUM,
            title="Dependencias actualizadas",
            message=f"DetectÃ© cambios en '{dependency_file}'. Â¿Instalar las nuevas dependencias?",
            action_command="@run pip install -r requirements.txt"
            if "requirements" in dependency_file
            else "@run npm install",
            action_description="Instalar dependencias del proyecto",
            dismiss_text="DespuÃ©s",
            timestamp=datetime.now().isoformat(),
            context={
                "file": dependency_file,
                "package": package_name,
                "key": f"deps:{dependency_file}",
            },
        )
        return self.add_suggestion(suggestion)

    def suggest_security_scan(self, file_path: str, issue_type: str) -> bool:
        """Sugerir escanear seguridad"""
        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.SECURITY,
            priority=SuggestionPriority.HIGH,
            title="Posible problema de seguridad",
            message=f"DetectÃ© un posible '{issue_type}' en '{Path(file_path).name}'. Â¿Reviso el archivo?",
            action_command=f"@analyze security {file_path}",
            action_description="Analizar problema de seguridad",
            dismiss_text="Ignorar",
            timestamp=datetime.now().isoformat(),
            context={
                "file": file_path,
                "issue": issue_type,
                "key": f"security:{issue_type}",
            },
        )
        return self.add_suggestion(suggestion)

    def suggest_based_on_pattern(
        self, predicted_action: str, confidence: float
    ) -> bool:
        """Sugerir basado en patrÃ³n aprendido"""
        if confidence < 0.7:  # Solo sugerir si hay alta confianza
            return False

        suggestion = Suggestion(
            suggestion_id=self._generate_id(),
            type=SuggestionType.PATTERN,
            priority=SuggestionPriority.LOW,
            title="Basado en tus hÃ¡bitos",
            message=f"Normalmente despuÃ©s de esto sueles: {predicted_action}. Â¿Quieres ejecutarlo?",
            action_command=predicted_action,
            action_description="Ejecutar acciÃ³n sugerida",
            dismiss_text="No esta vez",
            timestamp=datetime.now().isoformat(),
            context={
                "predicted_action": predicted_action,
                "confidence": confidence,
                "key": f"pattern:{predicted_action}",
            },
        )
        return self.add_suggestion(suggestion)

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadÃ­sticas"""
        with self._lock:
            total = len(self.suggestions)
            shown = sum(1 for s in self.suggestions.values() if s.shown)
            dismissed = sum(1 for s in self.suggestions.values() if s.dismissed)
            action_taken = sum(1 for s in self.suggestions.values() if s.action_taken)

            by_type = {}
            for s in self.suggestions.values():
                by_type[s.type.value] = by_type.get(s.type.value, 0) + 1

            return {
                "total_suggestions": total,
                "shown": shown,
                "dismissed": dismissed,
                "action_taken": action_taken,
                "pending": total - dismissed - action_taken,
                "by_type": by_type,
                "dismissed_patterns": len(self.dismissed_patterns),
                "suggestions_shown_count": self.suggestions_shown_count,
            }


# Singleton
_proactive_suggestions: Optional[ProactiveSuggestions] = None


def get_proactive_suggestions() -> ProactiveSuggestions:
    """Obtener instancia singleton"""
    global _proactive_suggestions
    if _proactive_suggestions is None:
        _proactive_suggestions = ProactiveSuggestions()
    return _proactive_suggestions


# === Testing ===
if __name__ == "__main__":
    print("=" * 60)
    print("ProactiveSuggestions - Test Suite")
    print("=" * 60)

    sugg = get_proactive_suggestions()

    # Test 1: Sugerir docstring
    print("\n[Test 1] Sugerir docstring")
    result = sugg.suggest_docstring("/path/to/file.py", "my_function")
    print(f"âœ“ Suggestion added: {result}")

    # Test 2: Sugerir commit
    print("\n[Test 2] Sugerir commit")
    result = sugg.suggest_commit(15, "Update models and tests")
    print(f"âœ“ Suggestion added: {result}")

    # Test 3: Obtener siguiente sugerencia
    print("\n[Test 3] Obtener sugerencia")
    next_sugg = sugg.get_next_suggestion()
    if next_sugg:
        print(f"âœ“ Next: {next_sugg.title} - {next_sugg.message[:50]}...")

    # Test 4: EstadÃ­sticas
    print("\n[Test 4] EstadÃ­sticas")
    stats = sugg.get_stats()
    print(f"âœ“ Total: {stats['total_suggestions']}, Pending: {stats['pending']}")

    print("\n" + "=" * 60)
    print("Tests completados!")
    print("=" * 60)
