from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PendingApproval:
    decision_id: str
    created_at: float
    expires_at: float
    request_payload: Dict[str, Any]
    event: threading.Event
    result: Optional[bool] = None  # True=approve, False=deny, None=pending


class PendingApprovalsRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._pending: Dict[str, PendingApproval] = {}

    def create(
        self, decision_id: str, timeout_sec: int, request_payload: Dict[str, Any]
    ) -> PendingApproval:
        now = time.time()
        pa = PendingApproval(
            decision_id=decision_id,
            created_at=now,
            expires_at=now + max(1, int(timeout_sec)),
            request_payload=request_payload,
            event=threading.Event(),
            result=None,
        )
        with self._lock:
            self._pending[decision_id] = pa
        return pa

    def resolve(self, decision_id: str, approved: bool) -> bool:
        with self._lock:
            pa = self._pending.get(decision_id)
            if not pa:
                return False
            pa.result = bool(approved)
            pa.event.set()
            # We don't delete immediately? The thread waiting on event consumes it.
            # But we should cleanup. If thread consumes, it's fine.
            # If we delete here, the thread might already have the `pa` object ref.
            del self._pending[decision_id]
            return True

    def expire_due(self) -> List[PendingApproval]:
        now = time.time()
        expired: List[PendingApproval] = []
        with self._lock:
            for decision_id, pa in list(self._pending.items()):
                if now >= pa.expires_at:
                    pa.result = False
                    pa.event.set()
                    expired.append(pa)
                    del self._pending[decision_id]
        return expired

    def has_any(self) -> bool:
        with self._lock:
            return bool(self._pending)

    def count(self) -> int:
        with self._lock:
            return len(self._pending)
