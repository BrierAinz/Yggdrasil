"""
Secrets Vault - B.6: Encrypted secrets management with Fernet.

Features:
- Fernet symmetric encryption (AES-128 + SHA256 HMAC)
- Automatic key rotation
- Access audit logging
- Rate limiting per secret
- Migration from .env files
"""
import base64
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.secrets")

# Intentar importar cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("[SecretsVault] cryptography no disponible. Usando modo dummy.")


class SecretsVault:
    """
    Vault cifrado para secrets con rotación automática.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, base_path: Optional[Path] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, base_path: Optional[Path] = None):
        if self._initialized:
            return

        if not CRYPTO_AVAILABLE:
            raise ImportError(
                "cryptography es requerido para SecretsVault. Instalar: pip install cryptography"
            )

        self.base_path = (
            Path(base_path) if base_path else Path(__file__).resolve().parents[3]
        )

        # Configuración
        self.config = self._load_config()
        self.vault_path = self.base_path / self.config.get(
            "vault_path", "Core/Config/secrets.vault"
        )
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)

        # Master key
        self._master_key = self._load_master_key()
        self._fernet = Fernet(self._master_key)

        # Cache de secrets desencriptados
        self._cache: Dict[str, str] = {}
        self._cache_lock = threading.RLock()

        # Acceso tracking para rate limiting y auditoría
        self._access_log_db = self.base_path / "Data" / "secrets_access.db"
        self._access_log_db.parent.mkdir(parents=True, exist_ok=True)
        self._init_access_db()

        # Cargar vault existente
        self._secrets: Dict[str, dict] = {}
        self._load_vault()

        self._initialized = True
        logger.info(
            "[SecretsVault] Inicializado. Secrets cargados: %d", len(self._secrets)
        )

    def _load_config(self) -> dict:
        """Carga configuración desde secrets.json."""
        config_path = self.base_path / "Config" / "secrets.json"
        return safe_load(
            config_path,
            default={
                "vault_path": "Core/Config/secrets.vault",
                "auto_rotate": True,
                "rotation_interval_days": 90,
            },
        )

    def _load_master_key(self) -> bytes:
        """Carga o genera master key."""
        # 1. Intentar desde variable de entorno
        env_key = os.getenv(self.config.get("master_key_env", "LILITH_MASTER_KEY"))
        if env_key:
            # Derivar key de 32 bytes desde password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"lilith_secrets_salt_v1",  # Salt fijo para consistencia
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(env_key.encode()))
            return key

        # 2. Intentar cargar desde archivo
        key_path = self.base_path / "Config" / ".master_key"
        if key_path.exists():
            return key_path.read_bytes()

        # 3. Generar nueva key
        key = Fernet.generate_key()
        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key)
            # Set restrictive permissions
            import stat

            os.chmod(str(key_path), stat.S_IRUSR | stat.S_IWUSR)
            logger.warning(
                "[SecretsVault] Nueva master key generada. GUARDAR EN LUGAR SEGURO."
            )
        except Exception as e:
            logger.error("[SecretsVault] No se pudo guardar master key: %s", e)

        return key

    def _init_access_db(self) -> None:
        """Inicializa base de datos de accesos."""
        try:
            with sqlite3.connect(str(self._access_log_db), timeout=10) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS secret_accesses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        secret_key TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        module TEXT,
                        function TEXT,
                        user_id TEXT
                    )
                """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_access_secret
                    ON secret_accesses(secret_key, timestamp)
                """
                )
                conn.commit()
        except Exception as e:
            logger.error("[SecretsVault] Error inicializando access DB: %s", e)

    def _load_vault(self) -> None:
        """Carga secrets desde vault cifrado."""
        if not self.vault_path.exists():
            self._secrets = {}
            return

        try:
            encrypted_data = self.vault_path.read_bytes()
            if not encrypted_data:
                self._secrets = {}
                return

            decrypted = self._fernet.decrypt(encrypted_data)
            self._secrets = json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            logger.error("[SecretsVault] Error cargando vault: %s", e)
            self._secrets = {}

    def _save_vault(self) -> bool:
        """Guarda secrets en vault cifrado."""
        try:
            data = json.dumps(self._secrets, ensure_ascii=False).encode("utf-8")
            encrypted = self._fernet.encrypt(data)
            self.vault_path.write_bytes(encrypted)
            return True
        except Exception as e:
            logger.error("[SecretsVault] Error guardando vault: %s", e)
            return False

    def _log_access(
        self, secret_key: str, module: str = "", function: str = "", user_id: str = ""
    ) -> None:
        """Loguea acceso a secret."""
        if not self.config.get("access_logging", True):
            return

        try:
            with sqlite3.connect(str(self._access_log_db), timeout=5) as conn:
                conn.execute(
                    "INSERT INTO secret_accesses (secret_key, timestamp, module, function, user_id) VALUES (?, ?, ?, ?, ?)",
                    (secret_key, time.time(), module, function, user_id),
                )
                conn.commit()
        except Exception as e:
            logger.debug("[SecretsVault] Error logueando acceso: %s", e)

    def _check_rate_limit(self, secret_key: str) -> bool:
        """Verifica rate limit de accesos a secret."""
        limit_config = self.config.get("access_rate_limit", {})
        max_accesses = limit_config.get("max_accesses_per_minute", 100)

        try:
            minute_ago = time.time() - 60
            with sqlite3.connect(str(self._access_log_db), timeout=5) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM secret_accesses WHERE secret_key = ? AND timestamp > ?",
                    (secret_key, minute_ago),
                )
                count = cursor.fetchone()[0]
                return count < max_accesses
        except Exception:
            return True

    def set_secret(self, key: str, value: str, metadata: Optional[dict] = None) -> bool:
        """
        Guarda un secret en el vault.

        Args:
            key: Nombre del secret
            value: Valor a guardar
            metadata: Metadata opcional (descripción, fecha creación, etc.)
        """
        try:
            self._secrets[key] = {
                "value": value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

            # Limpiar cache
            with self._cache_lock:
                self._cache.pop(key, None)

            if self._save_vault():
                logger.info("[SecretsVault] Secret guardado: %s", key)
                return True
            return False
        except Exception as e:
            logger.error("[SecretsVault] Error guardando secret: %s", e)
            return False

    def get_secret(
        self,
        key: str,
        default: Optional[str] = None,
        module: str = "",
        function: str = "",
    ) -> Optional[str]:
        """
        Obtiene un secret del vault.

        Args:
            key: Nombre del secret
            default: Valor por defecto si no existe
            module: Módulo que solicita (para auditoría)
            function: Función que solicita (para auditoría)
        """
        # Verificar rate limit
        if not self._check_rate_limit(key):
            logger.warning("[SecretsVault] Rate limit excedido para %s", key)
            return default

        # Intentar cache primero
        with self._cache_lock:
            if key in self._cache:
                self._log_access(key, module, function)
                return self._cache[key]

        # Buscar en vault
        secret_data = self._secrets.get(key)
        if not secret_data:
            return default

        value = secret_data.get("value")

        # Guardar en cache
        with self._cache_lock:
            self._cache[key] = value

        # Log acceso
        self._log_access(key, module, function)

        return value

    def delete_secret(self, key: str) -> bool:
        """Elimina un secret."""
        if key in self._secrets:
            del self._secrets[key]

            with self._cache_lock:
                self._cache.pop(key, None)

            if self._save_vault():
                logger.info("[SecretsVault] Secret eliminado: %s", key)
                return True
        return False

    def list_secrets(self) -> List[str]:
        """Lista nombres de secrets (sin valores)."""
        return list(self._secrets.keys())

    def get_secret_info(self, key: str) -> Optional[dict]:
        """Obtiene metadata de un secret (sin valor)."""
        secret = self._secrets.get(key)
        if secret:
            return {
                "created_at": secret.get("created_at"),
                "updated_at": secret.get("updated_at"),
                "metadata": secret.get("metadata", {}),
            }
        return None

    def rotate_secret(self, key: str, new_value: str) -> bool:
        """
        Rota un secret (actualiza valor y guarda historial).

        Args:
            key: Nombre del secret
            new_value: Nuevo valor
        """
        if key not in self._secrets:
            return False

        # Guardar valor anterior en historial
        old_value = self._secrets[key].get("value")
        if "rotation_history" not in self._secrets[key]:
            self._secrets[key]["rotation_history"] = []

        # Solo guardar hash del valor anterior
        old_hash = hashlib.sha256(old_value.encode()).hexdigest()[:16]
        self._secrets[key]["rotation_history"].append(
            {"hash": old_hash, "rotated_at": datetime.now(timezone.utc).isoformat()}
        )

        # Limitar historial
        self._secrets[key]["rotation_history"] = self._secrets[key]["rotation_history"][
            -10:
        ]

        # Actualizar valor
        self._secrets[key]["value"] = new_value
        self._secrets[key]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._secrets[key]["last_rotated"] = datetime.now(timezone.utc).isoformat()

        # Limpiar cache
        with self._cache_lock:
            self._cache.pop(key, None)

        if self._save_vault():
            logger.info("[SecretsVault] Secret rotado: %s", key)

            # Log auditoría
            try:
                from src.core.audit_logger import audit_log

                audit_log("secret_rotated", {"secret_key": key}, "info")
            except:
                pass

            return True
        return False

    def needs_rotation(self, key: str) -> bool:
        """Verifica si un secret necesita rotación."""
        if not self.config.get("auto_rotate", True):
            return False

        secret = self._secrets.get(key)
        if not secret:
            return False

        # Verificar si está en lista de auto-rotate
        auto_rotate_list = self.config.get("auto_rotate_secrets", [])
        if key not in auto_rotate_list:
            return False

        # Calcular fecha de rotación
        last_rotated = secret.get("last_rotated") or secret.get("created_at")
        if not last_rotated:
            return True

        try:
            last_dt = datetime.fromisoformat(last_rotated.replace("Z", "+00:00"))
            interval_days = self.config.get("rotation_interval_days", 90)
            next_rotation = last_dt + timedelta(days=interval_days)
            return datetime.now(timezone.utc) > next_rotation
        except:
            return True

    def check_all_rotations(self) -> List[Tuple[str, bool]]:
        """Verifica todos los secrets y retorna los que necesitan rotación."""
        needs_rotation = []
        for key in self._secrets:
            if self.needs_rotation(key):
                needs_rotation.append((key, True))
        return needs_rotation

    def migrate_from_env(
        self, env_file: Optional[Path] = None, secret_keys: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Migra secrets desde archivo .env al vault.

        Args:
            env_file: Path al archivo .env (default: .env en root)
            secret_keys: Lista de keys a migrar (si None, migra todo)

        Returns:
            Dict con resultado de cada migración
        """
        if env_file is None:
            env_file = self.base_path / ".env"

        results = {}

        if not env_file.exists():
            logger.warning("[SecretsVault] Archivo .env no encontrado: %s", env_file)
            return results

        try:
            # Parsear .env
            env_vars = {}
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip("\"'")

            # Migrar secrets
            for key, value in env_vars.items():
                if secret_keys and key not in secret_keys:
                    continue

                # Detectar si parece un secret
                if any(
                    s in key.upper()
                    for s in ["KEY", "TOKEN", "SECRET", "PASSWORD", "API"]
                ):
                    success = self.set_secret(key, value, {"migrated_from": ".env"})
                    results[key] = success

                    if success:
                        logger.info("[SecretsVault] Migrado: %s", key)

            logger.info(
                "[SecretsVault] Migración completada. %d secrets migrados.",
                sum(1 for v in results.values() if v),
            )

        except Exception as e:
            logger.error("[SecretsVault] Error migrando desde .env: %s", e)

        return results

    def get_access_log(
        self, secret_key: Optional[str] = None, hours: int = 24
    ) -> List[dict]:
        """Obtiene log de accesos a secrets."""
        try:
            since = time.time() - (hours * 3600)

            with sqlite3.connect(str(self._access_log_db), timeout=10) as conn:
                if secret_key:
                    cursor = conn.execute(
                        """SELECT secret_key, timestamp, module, function, user_id
                           FROM secret_accesses
                           WHERE secret_key = ? AND timestamp > ?
                           ORDER BY timestamp DESC""",
                        (secret_key, since),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT secret_key, timestamp, module, function, user_id
                           FROM secret_accesses
                           WHERE timestamp > ?
                           ORDER BY timestamp DESC
                           LIMIT 1000""",
                        (since,),
                    )

                return [
                    {
                        "secret_key": r[0],
                        "timestamp": datetime.fromtimestamp(
                            r[1], timezone.utc
                        ).isoformat(),
                        "module": r[2],
                        "function": r[3],
                        "user_id": r[4],
                    }
                    for r in cursor.fetchall()
                ]
        except Exception as e:
            logger.error("[SecretsVault] Error obteniendo access log: %s", e)
            return []

    def backup(self) -> Optional[Path]:
        """Crea backup del vault."""
        backup_config = self.config.get("backup", {})
        if not backup_config.get("enabled", True):
            return None

        try:
            backup_dir = self.base_path / backup_config.get(
                "path", "Core/Data/secrets_backup"
            )
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"secrets_backup_{timestamp}.vault"

            # Copiar vault
            import shutil

            shutil.copy2(self.vault_path, backup_path)

            # Limpiar backups antiguos
            retain = backup_config.get("retain_backups", 3)
            backups = sorted(backup_dir.glob("secrets_backup_*.vault"))
            for old_backup in backups[:-retain]:
                old_backup.unlink()

            logger.info("[SecretsVault] Backup creado: %s", backup_path)
            return backup_path

        except Exception as e:
            logger.error("[SecretsVault] Error creando backup: %s", e)
            return None


# Singleton
_secrets_vault_instance: Optional[SecretsVault] = None


def get_secrets_vault(base_path: Optional[Path] = None) -> SecretsVault:
    """Obtiene instancia singleton del SecretsVault."""
    global _secrets_vault_instance
    if _secrets_vault_instance is None:
        _secrets_vault_instance = SecretsVault(base_path)
    return _secrets_vault_instance


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Función conveniencia para obtener secret."""
    vault = get_secrets_vault()
    return vault.get_secret(key, default)


def set_secret(key: str, value: str) -> bool:
    """Función conveniencia para guardar secret."""
    vault = get_secrets_vault()
    return vault.set_secret(key, value)


__all__ = ["SecretsVault", "get_secrets_vault", "get_secret", "set_secret"]
