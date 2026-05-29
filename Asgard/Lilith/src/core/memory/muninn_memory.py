"""
MuninnDB — Wrapper cognitivo.
Mejoras MuninnDB: per-agent vaults, Why en activate(), write() genérico con metadata,
ensure_vaults(), search() genérico.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.core.json_safe import safe_load

logger = logging.getLogger("lilith.muninn")


def _normalize_muninn_token(raw: str) -> str:
    """Quita espacios y un posible prefijo 'Bearer ' duplicado (tokens copiados mal)."""
    t = (raw or "").strip()
    if t.lower().startswith("bearer "):
        t = t[7:].strip()
    return t


# ── Per-agent vaults ──────────────────────────────────────────────────────────

AGENT_VAULTS: Dict[str, str] = {
    "lilith": "lilith",
    "odin": "odin",
    "eva": "eva",
    "adan": "adan",
    "crystal": "crystal",
    "shalltear": "shalltear",
    "telegram": "telegram",
}

# ── Transport-based vaults (F.16) ─────────────────────────────────────────────
TRANSPORT_VAULTS: Dict[str, str] = {
    "discord": "default",
    "telegram": "telegram",
}


def _run_coro_fire_and_forget(coro) -> None:
    """
    Ejecuta una coroutine de forma segura desde sync code.
    - Si hay event loop corriendo: schedule y salir (fire-and-forget).
    - Si no: asyncio.run.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        try:
            asyncio.run(coro)
        except Exception:
            pass


class MuninnMemory:
    """Wrapper sobre MuninnDB. Soporta per-agent vaults, transport vaults, Why, metadata y ensure_vaults."""

    def __init__(
        self,
        base_path: Path,
        vault_name: Optional[str] = None,
        transport: Optional[str] = None,
    ):
        cfg = safe_load(Path(base_path) / "Config" / "muninn.json", default={})
        cfg = cfg if isinstance(cfg, dict) else {}
        self.base_path = Path(base_path)
        self.url = cfg.get("url", "http://127.0.0.1:8475")
        # Prioridad: muninn.json (muninn_token / token) evita basura en mcp.token o env;
        # luego env; luego ~/.muninn/mcp.token. Todo se .strip() para quitar \n/espacios.
        _cfg_tok = (
            cfg.get("muninn_token") or cfg.get("token") or cfg.get("api_key") or ""
        )
        self.token = _normalize_muninn_token(
            _cfg_tok
            or (os.getenv("MUNINN_TOKEN") or "")
            or (MuninnMemory._read_token_file() or "")
        )
        self.enabled = bool(cfg.get("enabled", True))
        # vault_map soporta los vaults lógicos legacy ("facts", "episodes", "projects")
        self.vault_map: Dict[str, str] = (
            cfg.get("vault_map") if isinstance(cfg.get("vault_map"), dict) else {}
        )
        # agent_memory config
        muninn_vaults = cfg.get("muninn_vaults") or {}
        if isinstance(muninn_vaults, dict):
            # Actualizar AGENT_VAULTS con config real si se definen
            for k, v in muninn_vaults.items():
                if k and v:
                    AGENT_VAULTS[str(k)] = str(v)
        self.agent_memory_top_k: int = int(cfg.get("agent_memory_top_k") or 3)
        self.agent_memory_max_chars: int = int(
            cfg.get("agent_memory_max_content_chars") or 300
        )

        # F.16: Transport-based vault selection
        self.vault_name = vault_name
        self.transport = transport
        self._transport_vaults: Dict[str, str] = {}
        raw_tv = cfg.get("transport_vaults")
        if isinstance(raw_tv, dict):
            for k, v in raw_tv.items():
                if k is not None and v is not None:
                    self._transport_vaults[str(k).lower()] = str(v).strip()

        # Determinar vault a usar basado en transporte o nombre explícito
        if vault_name:
            self.active_vault = vault_name
            logger.debug("[MuninnMemory] Using explicit vault: %s", vault_name)
        elif transport:
            self.active_vault = self._transport_vaults.get(transport.lower(), "default")
            logger.debug(
                "[MuninnMemory] Using transport vault: %s (transport=%s)",
                self.active_vault,
                transport,
            )
        else:
            self.active_vault = "default"

        if transport or vault_name:
            logger.info(
                "[MuninnMemory] Using vault: %s (transport=%s, explicit=%s)",
                self.active_vault,
                transport,
                vault_name,
            )
        # Nombre de vault físico → token mk_ (cada clave en Muninn autoriza un vault concreto).
        self.vault_tokens: Dict[str, str] = {}
        raw_vt = cfg.get("vault_tokens")
        if isinstance(raw_vt, dict):
            for k, v in raw_vt.items():
                if k is None or v is None:
                    continue
                ks, vs = str(k).strip(), str(v).strip()
                if ks and vs:
                    self.vault_tokens[ks] = vs
        self._clients_by_token: Dict[str, Any] = {}

    @staticmethod
    def _read_token_file() -> str:
        """Fallback: lee token desde ~/.muninn/mcp.token (igual que el SDK y MCP)."""
        try:
            home = Path.home()
            for name in (".muninn", "muninn"):
                p = home / name / "mcp.token"
                if p.exists():
                    t = p.read_text(encoding="utf-8", errors="ignore").strip()
                    if t:
                        return t.split()[0].strip()
        except Exception:
            pass
        return ""

    def _map_vault(self, vault: str) -> str:
        """Resuelve vault lógico a vault real. Soporta legacy y per-agent."""
        v = (vault or "").strip() or "facts"
        # Legacy vault_map primero
        if v in self.vault_map:
            return str(self.vault_map[v]).strip()
        # Per-agent vaults
        if v in AGENT_VAULTS:
            return AGENT_VAULTS[v]
        return v

    def _token_for_vault(self, mapped_physical_vault: Optional[str]) -> str:
        """Token mk_ para un vault físico; si no hay entrada, usa el token global."""
        name = (mapped_physical_vault or "").strip()
        if not name:
            return self.token
        if name in self.vault_tokens:
            return _normalize_muninn_token(self.vault_tokens[name])
        lower_map = {str(k).lower(): v for k, v in self.vault_tokens.items()}
        if name.lower() in lower_map:
            return _normalize_muninn_token(lower_map[name.lower()])
        return self.token

    async def _get_client(self, mapped_physical_vault: Optional[str] = None):
        """Un AsyncClient por token distinto (Authorization distinta por vault)."""
        import httpx

        tok = self._token_for_vault(mapped_physical_vault)
        cache_key = tok if tok else "__no_token__"
        if cache_key not in self._clients_by_token:
            headers: Dict[str, str] = {}
            if tok:
                headers["Authorization"] = f"Bearer {tok}"
            self._clients_by_token[cache_key] = httpx.AsyncClient(
                base_url=self.url.rstrip("/") + "/api",
                headers=headers,
                timeout=10.0,
            )
        return self._clients_by_token[cache_key]

    async def _rest_post(
        self,
        endpoint: str,
        payload: dict,
        mapped_physical_vault: Optional[str] = None,
    ) -> dict:
        try:
            client = await self._get_client(mapped_physical_vault)
            r = await client.post(endpoint, json=payload)
            res_tok = self._token_for_vault(mapped_physical_vault)
            tok_ok = bool(res_tok)
            if r.status_code in (200, 201):
                return r.json() if r.content else {}
            body_preview = (getattr(r, "text", None) or "")[:400].replace("\n", " ")
            if r.status_code in (401, 403):
                logger.warning(
                    "MuninnDB POST %s → %s (vault=%s token=%s). Cuerpo: %s",
                    endpoint,
                    r.status_code,
                    mapped_physical_vault or "(global)",
                    "SET" if tok_ok else "EMPTY",
                    body_preview or "(vacío)",
                )
            else:
                logger.warning(
                    "MuninnDB POST %s → %s (vault=%s token=%s)",
                    endpoint,
                    r.status_code,
                    mapped_physical_vault or "(global)",
                    "SET" if tok_ok else "EMPTY",
                )
            return {}
        except Exception as e:
            logger.debug("MuninnDB POST %s error: %s", endpoint, e)
            return {}

    async def _rest_get(
        self,
        endpoint: str,
        params: dict = None,
        mapped_physical_vault: Optional[str] = None,
    ) -> dict:
        try:
            client = await self._get_client(mapped_physical_vault)
            r = await client.get(endpoint, params=params or {})
            if r.status_code == 200:
                return r.json() if r.content else {}
            return {}
        except Exception as e:
            logger.debug("MuninnDB GET %s error: %s", endpoint, e)
            return {}

    # ── Vaults ───────────────────────────────────────────────────────────────

    async def ensure_vaults(self) -> None:
        """
        Mejora-1: crea todos los per-agent vaults al arranque si no existen.
        Silencioso si la API no soporta creación explícita.
        """
        if not self.enabled:
            return
        skip_ensure = False
        for vault_name in set(AGENT_VAULTS.values()):
            if skip_ensure:
                break
            try:
                client = await self._get_client(vault_name)
                r = await client.post("/vaults", json={"name": vault_name})
                if r.status_code in (200, 201):
                    logger.debug("MuninnDB: vault '%s' ensured", vault_name)
                elif r.status_code == 405:
                    logger.debug(
                        "MuninnDB: POST /vaults no existe en este servidor (405); "
                        "crea vaults desde la UI/consola de Muninn. No reintentar."
                    )
                    skip_ensure = True
                else:
                    logger.debug(
                        "MuninnDB: ensure vault '%s' → HTTP %s",
                        vault_name,
                        r.status_code,
                    )
            except Exception:
                pass

    # ── Escritura ─────────────────────────────────────────────────────────────

    async def write(
        self,
        vault: str,
        concept: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mejora-1/3: escritura genérica a cualquier vault con metadata opcional.
        """
        if not self.enabled:
            return
        try:
            mapped = self._map_vault(vault)
            payload: Dict[str, Any] = {
                "vault": mapped,
                "concept": (concept or "")[:200],
                "content": (content or "")[:2000],
                "tags": tags or [],
            }
            if metadata:
                payload["metadata"] = {k: str(v)[:200] for k, v in metadata.items()}
            await self._rest_post("/engrams", payload, mapped_physical_vault=mapped)
        except Exception as e:
            logger.debug("MuninnDB write error: %s", e)

    async def write_fact(
        self, concept: str, content: str, tags: Optional[List[str]] = None
    ):
        await self.write("facts", concept, content, tags)

    async def write_episode(
        self, concept: str, content: str, tags: Optional[List[str]] = None
    ):
        await self.write("episodes", concept, content, tags)

    # ── Activación con Why ────────────────────────────────────────────────────

    async def activate(
        self,
        context: Union[List[str], str],
        vault: Optional[str] = None,
        max_results: int = 5,
        log_why: bool = True,
    ) -> List[dict]:
        """
        Recupera memorias cognitivamente relevantes.
        Mejora-2: extrae y expone campo Why de cada activación.
        context puede ser List[str] o str.
        F.16: Usa vault de transporte si no se especifica vault explícito.
        """
        if not self.enabled:
            return []
        ctx = [context] if isinstance(context, str) else (context or [])
        # F.16: Usar active_vault como default si no se especifica vault
        vault_to_use = vault if vault else self.active_vault
        mapped = self._map_vault(vault_to_use)
        res_tok = self._token_for_vault(mapped)
        logger.info(
            "MuninnDB activate: token=%s, url=%s, vault=%s (mapped=%s, transport=%s)",
            "SET" if res_tok else "EMPTY",
            self.url,
            vault_to_use,
            mapped,
            self.transport or "none",
        )
        try:
            payload = {
                "vault": mapped,
                "context": ctx,
                "max_results": max_results,
            }
            r_data = await self._rest_post(
                "/activate", payload, mapped_physical_vault=mapped
            )
            acts_raw = r_data.get("activations") if isinstance(r_data, dict) else None
            if not isinstance(acts_raw, list):
                return []
            out = []
            for a in acts_raw:
                if not isinstance(a, dict):
                    continue
                why = a.get("why") or {}
                entry = {
                    "concept": a.get("concept"),
                    "content": a.get("content"),
                    "score": a.get("score"),
                    "tags": a.get("tags") or [],
                    "why": why,  # Mejora-2: propagar Why
                }
                out.append(entry)
                # Log Why si hay datos
                if log_why and why:
                    self._log_why(
                        vault, ctx[0][:100] if ctx else "", a.get("concept") or "", why
                    )
            return out
        except Exception as e:
            logger.debug("MuninnDB activate error: %s", e)
            return []

    def _log_why(
        self, vault: str, context_preview: str, concept: str, why: dict
    ) -> None:
        """Mejora-2: log del Why de activación en el audit logger."""
        try:
            from src.core.meta_report import get_audit_logger

            audit = get_audit_logger()
            audit.log(
                "muninn_activation",
                {
                    "vault": vault,
                    "context": context_preview,
                    "concept": concept,
                    "score_bm25": why.get("bm25") or why.get("text") or 0,
                    "score_hebbian": why.get("hebbian") or 0,
                    "score_temporal": why.get("temporal") or 0,
                    "score_total": why.get("total") or why.get("score") or 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            pass  # Audit no crítico

    # ── Calidad de memoria (Mejora-2) ─────────────────────────────────────────

    @staticmethod
    def assess_memory_quality(muninn_results: List[dict]) -> float:
        """
        Mejora-2: evalúa calidad de los recuerdos activados para calibrar confianza del planner.
        Score alto = buena base para decidir. Score bajo = recuerdos débiles.
        """
        if not muninn_results:
            return 0.5
        scores = []
        for r in muninn_results:
            why = r.get("why") or {}
            hebbian = float(why.get("hebbian") or 0)
            temporal = float(why.get("temporal") or 0)
            bm25 = float(why.get("bm25") or why.get("text") or 0)
            if hebbian > 0.3 and temporal > 0.3:
                scores.append(1.0)
            elif bm25 > 0.5 and (hebbian > 0.1 or temporal > 0.1):
                scores.append(0.7)
            else:
                scores.append(0.3)
        return sum(scores) / len(scores)

    # ── Búsqueda ──────────────────────────────────────────────────────────────

    async def search(
        self, query: str, vault: str = "facts", limit: int = 10
    ) -> List[dict]:
        """Busca memorias por concepto exacto o cercano."""
        return await self.activate([query], vault=vault, max_results=limit)

    async def query(self, concept: str, vault: str = "facts") -> List[dict]:
        """Alias legacy."""
        return await self.activate([concept], vault=vault, max_results=10)

    # ── Agent memory helpers ──────────────────────────────────────────────────

    async def get_agent_memory(self, agent_name: str, task: str) -> str:
        """
        Mejora-1: recupera memoria previa del vault propio del agente e
        la formatea como bloque de texto para inyectar en el prompt.
        """
        vault = AGENT_VAULTS.get(agent_name, "lilith")
        results = await self.activate(
            context=task,
            vault=vault,
            max_results=self.agent_memory_top_k,
        )
        if not results:
            return ""
        lines = [f"[Memoria de {agent_name.capitalize()} — contexto previo relevante]"]
        for r in results:
            concept = (r.get("concept") or "").strip()
            content = (r.get("content") or "").strip()[: self.agent_memory_max_chars]
            if concept or content:
                lines.append(f"- {concept}: {content}" if concept else f"- {content}")
        return "\n".join(lines) if len(lines) > 1 else ""

    async def write_agent_output(
        self,
        agent_name: str,
        task: str,
        output: str,
        intent: str = "default",
        extra_tags: Optional[List[str]] = None,
    ) -> None:
        """
        Mejora-1: escribe el output de un agente en su vault propio.
        Fire-and-forget desde sync o async.
        """
        import hashlib

        vault = AGENT_VAULTS.get(agent_name, "lilith")
        concept = f"{agent_name}:{task[:100]}"
        tags = [intent, f"{agent_name}_output"] + (extra_tags or [])
        metadata = {
            "task_hash": hashlib.md5(task.encode()).hexdigest()[:12],
            "intent": intent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
        }
        await self.write(
            vault=vault,
            concept=concept,
            content=output[:2000],
            tags=tags,
            metadata=metadata,
        )

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def close(self):
        for c in list(self._clients_by_token.values()):
            try:
                await c.aclose()
            except Exception:
                pass
        self._clients_by_token.clear()


__all__ = ["MuninnMemory", "_run_coro_fire_and_forget", "AGENT_VAULTS"]
