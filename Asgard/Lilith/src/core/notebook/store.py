"""
Fase 4.2 — Cuaderno híbrido: JSONL como fuente de verdad + sync important=true a Muninn.
Mismo id (notebook) usado para localizar en Muninn al borrar/actualizar (§6.3.1).
Ver DISEÑO_FUENTE_CUADERNO_AUTOAPRENDIZAJE.md §2 y §6.3.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("notebook.store")

NOTEBOOK_VAULT = "lilith"


def _default_base_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


class NotebookStore:
    """
    Almacén del cuaderno de Lilith: Data/lilith_notebook.jsonl.
    Ítems con important=true se sincronizan a Muninn (vault lilith); muninn_id se guarda en la línea para poder borrar.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else _default_base_path()
        self._path = self.base_path / "Data" / "lilith_notebook.jsonl"

    def _ensure_data_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all_entries(self) -> List[Dict[str, Any]]:
        from src.core.json_safe import safe_load_lines

        if not self._path.exists():
            return []
        lines = safe_load_lines(self._path, default=[])
        entries = []
        for raw in lines:
            if isinstance(raw, dict):
                entries.append(raw)
            elif isinstance(raw, str):
                try:
                    entries.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        return entries

    def _save_all_entries(self, entries: List[Dict[str, Any]]) -> None:
        self._ensure_data_dir()
        with open(self._path, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def add(
        self,
        content: str,
        important: bool,
        source: str = "",
        source_detail: str = "",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Añade una entrada al cuaderno. Genera id único.
        Si important=true, escribe también en Muninn (vault lilith) y guarda muninn_id en la línea.
        """
        entry_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        tags = list(tags)[:20] if tags else []
        muninn_id: Optional[str] = None

        if important:
            from src.core.memory.muninn_adapter import is_enabled
            from src.core.memory.muninn_adapter import write as muninn_write

            if is_enabled(self.base_path):
                cfg = {}
                try:
                    from src.core.json_safe import safe_load

                    p = self.base_path / "Config" / "muninn.json"
                    if p.exists():
                        cfg = safe_load(p, default={}) or {}
                except Exception:
                    pass
                vault = (cfg.get("muninn_vault") or NOTEBOOK_VAULT).strip()
                concept = (content.strip()[:500]) or "notebook"
                sync_tags = ["cuaderno", "important", f"notebook_id:{entry_id}"]
                muninn_id = muninn_write(
                    self.base_path,
                    vault=vault,
                    concept=concept,
                    content=content.strip()[:4000],
                    tags=sync_tags,
                )

        entry = {
            "id": entry_id,
            "content": content.strip(),
            "important": bool(important),
            "source": (source or "").strip(),
            "source_detail": (source_detail or "").strip(),
            "created_at": now,
            "tags": tags,
            "muninn_id": muninn_id,
        }
        self._ensure_data_dir()
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry_id

    def search(
        self,
        query: Optional[str] = None,
        important_only: bool = False,
        source: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Busca en el cuaderno. query se compara con content y tags (substring).
        important_only filtra por important==true; source por campo source.
        """
        entries = self._load_all_entries()
        if important_only:
            entries = [e for e in entries if e.get("important")]
        if source is not None:
            entries = [e for e in entries if (e.get("source") or "") == source]
        if query and query.strip():
            q = query.strip().lower()
            entries = [
                e
                for e in entries
                if q in (e.get("content") or "").lower()
                or q in " ".join(e.get("tags") or []).lower()
            ]
        # Orden por created_at descendente
        entries.sort(key=lambda e: e.get("created_at") or "", reverse=True)
        return entries[:limit]

    def set_important(self, entry_id: str, important: bool) -> bool:
        """
        Cambia important de una entrada. Si pasa a false y tenía muninn_id, borra el engrama en Muninn.
        Si pasa a true, escribe en Muninn y actualiza muninn_id en la línea (reescribe el archivo).
        """
        entries = self._load_all_entries()
        for i, e in enumerate(entries):
            if (e.get("id")) == entry_id:
                old_important = e.get("important", False)
                old_muninn_id = e.get("muninn_id")
                if not important and old_muninn_id:
                    from src.core.memory.muninn_adapter import delete_engram, is_enabled

                    if is_enabled(self.base_path):
                        try:
                            from src.core.json_safe import safe_load

                            cfg = (
                                safe_load(
                                    self.base_path / "Config" / "muninn.json",
                                    default={},
                                )
                                or {}
                            )
                        except Exception:
                            cfg = {}
                        vault = (cfg.get("muninn_vault") or NOTEBOOK_VAULT).strip()
                        delete_engram(
                            self.base_path, vault=vault, engram_id=old_muninn_id
                        )
                    e["muninn_id"] = None
                elif important and not old_muninn_id:
                    from src.core.memory.muninn_adapter import is_enabled
                    from src.core.memory.muninn_adapter import write as muninn_write

                    if is_enabled(self.base_path):
                        cfg = {}
                        try:
                            from src.core.json_safe import safe_load

                            cfg = (
                                safe_load(
                                    self.base_path / "Config" / "muninn.json",
                                    default={},
                                )
                                or {}
                            )
                        except Exception:
                            pass
                        vault = (cfg.get("muninn_vault") or NOTEBOOK_VAULT).strip()
                        concept = (e.get("content") or "")[:500] or "notebook"
                        muninn_id = muninn_write(
                            self.base_path,
                            vault=vault,
                            concept=concept,
                            content=(e.get("content") or "")[:4000],
                            tags=["cuaderno", "important", f"notebook_id:{entry_id}"],
                        )
                        e["muninn_id"] = muninn_id
                e["important"] = important
                self._save_all_entries(entries)
                return True
        return False
