from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentState:
    status: str  # IDLE | BUSY_INVESTIGATING | BUSY_OTHER
    since_ts: float
    detail: str = ""
    interruptions: List[str] = field(default_factory=list)


class AgentStateManager:
    """
    Gestor de estado en memoria, indexado por user_id (Discord).
    Thread-safe: se usa desde FastAPI + threads del executor.
    """

    _lock = threading.Lock()
    _states: Dict[str, AgentState] = {}
    _max_interruptions = 3

    @classmethod
    def set_state(cls, user_id: str, status: str, detail: str = "") -> None:
        uid = (user_id or "").strip()
        if not uid:
            return
        st = (status or "IDLE").strip().upper()
        with cls._lock:
            prev = cls._states.get(uid)
            interruptions = list(prev.interruptions) if prev else []
            cls._states[uid] = AgentState(
                status=st,
                since_ts=time.time(),
                detail=(detail or "")[:200],
                interruptions=interruptions,
            )

    @classmethod
    def clear(cls, user_id: str) -> None:
        uid = (user_id or "").strip()
        if not uid:
            return
        with cls._lock:
            cls._states.pop(uid, None)

    @classmethod
    def get(cls, user_id: str) -> Optional[AgentState]:
        uid = (user_id or "").strip()
        if not uid:
            return None
        with cls._lock:
            return cls._states.get(uid)

    @classmethod
    def is_busy(cls, user_id: str) -> bool:
        st = cls.get(user_id)
        if not st:
            return False
        return st.status.startswith("BUSY")

    @classmethod
    def push_interruption(cls, user_id: str, note: str) -> None:
        uid = (user_id or "").strip()
        if not uid:
            return
        n = (note or "").strip()
        if not n:
            return
        n = n[:800]
        with cls._lock:
            st = cls._states.get(uid)
            if st is None:
                st = AgentState(
                    status="IDLE", since_ts=time.time(), detail="", interruptions=[]
                )
                cls._states[uid] = st
            st.interruptions.append(n)
            if len(st.interruptions) > cls._max_interruptions:
                st.interruptions = st.interruptions[-cls._max_interruptions :]

    @classmethod
    def pop_interruptions(cls, user_id: str) -> List[str]:
        uid = (user_id or "").strip()
        if not uid:
            return []
        with cls._lock:
            st = cls._states.get(uid)
            if st is None or not st.interruptions:
                return []
            out = list(st.interruptions)
            st.interruptions = []
            return out
