"""
Ephemeral Memory - Memoria temporal para usuarios públicos.
Almacena facts en RAM con TTL (Time To Live).
No persiste en disco - los datos expiran después del TTL.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger("lilith.ephemeral_memory")


@dataclass
class EphemeralFact:
    """Un fact en memoria ephemeral."""

    user_id: str
    content: str
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def __post_init__(self):
        if self.expires_at == 0.0:
            # Default TTL: 1 hour
            self.expires_at = self.created_at + 3600


class EphemeralMemory:
    """
    Vault de memoria ephemeral para usuarios públicos.
    - Almacena en RAM (dict), no en disco
    - TTL configurable por fact
    - Límites por usuario (max facts)
    - Thread-safe
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, ttl_seconds: int = 3600, max_facts_per_user: int = 20):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, ttl_seconds: int = 3600, max_facts_per_user: int = 20):
        if self._initialized:
            return

        self._storage: Dict[str, List[EphemeralFact]] = {}  # user_id -> facts
        self._ttl_seconds = ttl_seconds
        self._max_facts_per_user = max_facts_per_user
        self._local_lock = threading.RLock()
        self._initialized = True

        # Iniciar thread de limpieza periódica
        self._start_cleanup_thread()

        logger.info(
            "[EphemeralMemory] Inicializado con TTL=%ds, max_facts=%d",
            ttl_seconds,
            max_facts_per_user,
        )

    def _start_cleanup_thread(self) -> None:
        """Inicia thread daemon para limpieza periódica."""

        def cleanup_loop():
            while True:
                time.sleep(300)  # Cada 5 minutos
                try:
                    self._cleanup_expired()
                except Exception as e:
                    logger.debug("[EphemeralMemory] Error en cleanup: %s", e)

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()

    def _cleanup_expired(self) -> int:
        """Limpia facts expirados. Retorna número eliminados."""
        now = time.time()
        removed = 0

        with self._local_lock:
            for user_id, facts in list(self._storage.items()):
                original_count = len(facts)
                self._storage[user_id] = [f for f in facts if f.expires_at > now]
                removed += original_count - len(self._storage[user_id])

                # Limpiar lista vacía
                if not self._storage[user_id]:
                    del self._storage[user_id]

        if removed > 0:
            logger.debug(
                "[EphemeralMemory] Limpieza: %d facts expirados eliminados", removed
            )

        return removed

    def store(
        self,
        user_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Almacena un fact para un usuario.

        Args:
            user_id: ID del usuario Discord
            content: Contenido del fact
            tags: Tags opcionales
            ttl_seconds: TTL específico (usa default si no se especifica)

        Returns:
            True si se almacenó correctamente
        """
        if not user_id or not content:
            return False

        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        now = time.time()

        fact = EphemeralFact(
            user_id=user_id,
            content=content,
            tags=tags or [],
            created_at=now,
            expires_at=now + ttl,
        )

        with self._local_lock:
            if user_id not in self._storage:
                self._storage[user_id] = []

            # Verificar límite
            if len(self._storage[user_id]) >= self._max_facts_per_user:
                # Eliminar el más antiguo (FIFO)
                self._storage[user_id].pop(0)
                logger.debug(
                    "[EphemeralMemory] Fact más antiguo eliminado para user %s", user_id
                )

            self._storage[user_id].append(fact)

        logger.info(
            "[EphemeralMemory] Storing fact for user %s (TTL: %ds, tags: %s)",
            user_id,
            ttl,
            tags or [],
        )
        return True

    def retrieve(
        self, user_id: str, query: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        """
        Recupera facts de un usuario.

        Args:
            user_id: ID del usuario
            query: Query para filtrar (búsqueda simple)
            limit: Máximo de facts a retornar

        Returns:
            Lista de facts como dicts
        """
        self._cleanup_expired()

        with self._local_lock:
            facts = self._storage.get(user_id, [])

            # Filtrar por query si se especifica
            if query:
                query_lower = query.lower()
                facts = [f for f in facts if query_lower in f.content.lower()]

            # Ordenar por más reciente
            facts = sorted(facts, key=lambda f: f.created_at, reverse=True)[:limit]

            return [
                {
                    "content": f.content,
                    "tags": f.tags,
                    "created_at": f.created_at,
                    "expires_at": f.expires_at,
                    "ttl_remaining": max(0, int(f.expires_at - time.time())),
                }
                for f in facts
            ]

    def retrieve_context_block(
        self, user_id: str, query: Optional[str] = None, max_chars: int = 500
    ) -> str:
        """
        Recupera facts formateados como bloque de contexto para prompt.

        Args:
            user_id: ID del usuario
            query: Query para filtrar relevantes
            max_chars: Máximo de caracteres del bloque

        Returns:
            Bloque de texto formateado o string vacío
        """
        facts = self.retrieve(user_id, query, limit=10)

        if not facts:
            return ""

        lines = ["[Contexto reciente de la conversación]"]
        total_chars = len(lines[0])

        for fact in facts:
            tags_str = f" ({', '.join(fact['tags'])})" if fact["tags"] else ""
            line = f"- {fact['content']}{tags_str}"

            if total_chars + len(line) + 1 > max_chars:
                break

            lines.append(line)
            total_chars += len(line) + 1

        return "\n".join(lines) if len(lines) > 1 else ""

    def delete(self, user_id: str, content_substring: str) -> bool:
        """
        Elimina facts que contengan un substring.

        Returns:
            True si se eliminó al menos un fact
        """
        with self._local_lock:
            if user_id not in self._storage:
                return False

            original_count = len(self._storage[user_id])
            self._storage[user_id] = [
                f
                for f in self._storage[user_id]
                if content_substring.lower() not in f.content.lower()
            ]

            removed = original_count - len(self._storage[user_id])

            if not self._storage[user_id]:
                del self._storage[user_id]

        if removed > 0:
            logger.info(
                "[EphemeralMemory] Deleted %d facts for user %s", removed, user_id
            )

        return removed > 0

    def clear_user(self, user_id: str) -> int:
        """Elimina todos los facts de un usuario. Retorna número eliminado."""
        with self._local_lock:
            if user_id not in self._storage:
                return 0

            count = len(self._storage[user_id])
            del self._storage[user_id]

        logger.info("[EphemeralMemory] Cleared %d facts for user %s", count, user_id)
        return count

    def get_stats(self, user_id: Optional[str] = None) -> Dict:
        """Obtiene estadísticas de la memoria ephemeral."""
        self._cleanup_expired()

        with self._local_lock:
            if user_id:
                facts = self._storage.get(user_id, [])
                return {
                    "user_id": user_id,
                    "facts_count": len(facts),
                    "ttl_seconds": self._ttl_seconds,
                    "facts": [
                        {
                            "content": f.content[:100] + "..."
                            if len(f.content) > 100
                            else f.content,
                            "ttl_remaining": max(0, int(f.expires_at - time.time())),
                        }
                        for f in facts
                    ],
                }
            else:
                total_facts = sum(len(facts) for facts in self._storage.values())
                return {
                    "total_users": len(self._storage),
                    "total_facts": total_facts,
                    "ttl_seconds": self._ttl_seconds,
                    "max_facts_per_user": self._max_facts_per_user,
                }

    def is_public_namespace(self) -> bool:
        """Indica que este es un namespace aislado (no comparte con Muninn)."""
        return True


class EphemeralMemoryForCrystal:
    """
    Wrapper específico para Crystal que carga config desde crystal.json.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )
        self._config = self._load_config()
        self._memory = EphemeralMemory(
            ttl_seconds=self._config.get("ttl_seconds", 3600),
            max_facts_per_user=self._config.get("max_facts_per_user", 20),
        )

    def _load_config(self) -> Dict:
        """Carga configuración desde crystal.json."""
        try:
            crystal_path = self.base_path / "Config" / "crystal.json"
            if crystal_path.exists():
                data = json.loads(crystal_path.read_text(encoding="utf-8"))
                return data.get("ephemeral_memory", {})
        except Exception as e:
            logger.warning("[EphemeralMemory] Error cargando config: %s", e)
        return {}

    def store(
        self, user_id: str, content: str, tags: Optional[List[str]] = None
    ) -> bool:
        return self._memory.store(user_id, content, tags)

    def retrieve(
        self, user_id: str, query: Optional[str] = None, limit: int = 10
    ) -> List[Dict]:
        return self._memory.retrieve(user_id, query, limit)

    def retrieve_context_block(
        self, user_id: str, query: Optional[str] = None, max_chars: int = 500
    ) -> str:
        return self._memory.retrieve_context_block(user_id, query, max_chars)

    def clear_user(self, user_id: str) -> int:
        return self._memory.clear_user(user_id)

    def get_stats(self, user_id: Optional[str] = None) -> Dict:
        return self._memory.get_stats(user_id)


# Funciones de conveniencia para uso simple
def store_ephemeral_fact(
    user_id: str,
    content: str,
    tags: Optional[List[str]] = None,
    base_path: Optional[Path] = None,
) -> bool:
    """Almacena un fact ephemeral."""
    crystal_mem = EphemeralMemoryForCrystal(base_path)
    return crystal_mem.store(user_id, content, tags)


def get_ephemeral_context(
    user_id: str,
    query: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> str:
    """Obtiene bloque de contexto ephemeral."""
    crystal_mem = EphemeralMemoryForCrystal(base_path)
    return crystal_mem.retrieve_context_block(user_id, query)


__all__ = [
    "EphemeralMemory",
    "EphemeralMemoryForCrystal",
    "EphemeralFact",
    "store_ephemeral_fact",
    "get_ephemeral_context",
]
