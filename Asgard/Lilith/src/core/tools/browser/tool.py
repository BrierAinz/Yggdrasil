import asyncio
import logging
from typing import Any, Dict, List

from src.core.tools_v3.base import ToolV3  # ajusta si la ruta difiere

from .browser_engine import BrowserEngine

logger = logging.getLogger(__name__)


def _try_screenshot(engine: BrowserEngine, filename: str = "fatal.png") -> str:
    """Intenta capturar screenshot y devuelve screenshot_id o ''."""
    try:
        if not getattr(engine, "initialized", False) or not getattr(
            engine, "loop", None
        ):
            return ""
        fut = asyncio.run_coroutine_threadsafe(
            engine.screenshot_bytes(filename), engine.loop
        )
        res = fut.result(timeout=5.0)
        if isinstance(res, dict):
            return (res.get("screenshot_id") or "").strip()
    except Exception:
        return ""
    return ""


def _run_on_engine(coro, engine: BrowserEngine, timeout: float) -> Dict[str, Any]:
    if not getattr(engine, "initialized", False) or not getattr(engine, "loop", None):
        return {
            "error": "browser_engine_not_initialized",
            "message": "BrowserEngine no está inicializado (Playwright no disponible).",
            "fatal_error": True,
        }
    if not BrowserEngine.try_acquire_lease():
        return {
            "error": "resource_locked",
            "message": "El navegador está ocupado con otra tarea. Intenta de nuevo en unos segundos o usa el carril rápido sin web.",
            "fatal_error": False,
        }
    future = asyncio.run_coroutine_threadsafe(coro, engine.loop)
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        try:
            future.cancel()
        except Exception:
            pass
        logger.error("Timeout en BrowserTool")
        screenshot_id = _try_screenshot(engine, "timeout.png")
        out: Dict[str, Any] = {
            "error": "timeout",
            "message": "La operación web excedió el tiempo límite.",
            "fatal_error": True,
        }
        if screenshot_id:
            out["screenshot_id"] = screenshot_id
        return out
    except Exception as e:
        logger.error("Error threadsafe en BrowserTool: %s", e)
        screenshot_id = _try_screenshot(engine, "thread_failed.png")
        out: Dict[str, Any] = {
            "error": "thread_execution_failed",
            "message": str(e),
            "fatal_error": True,
        }
        if screenshot_id:
            out["screenshot_id"] = screenshot_id
        return out
    finally:
        BrowserEngine.release_lease()


class BrowserGotoTool(ToolV3):
    name = "browser_goto"
    description = (
        "Navega a una URL y devuelve el estado de la página (acciones y contenido)."
    )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = (params.get("url") or "").strip()
        if not url:
            return {"error": "missing_param", "message": "Falta el parámetro 'url'."}
        engine = BrowserEngine()
        if not getattr(engine, "initialized", False) or not getattr(
            engine, "loop", None
        ):
            return {"error": "browser_engine_not_initialized"}
        return _run_on_engine(engine.goto(url), engine, timeout=20.0)


class BrowserClickTool(ToolV3):
    name = "browser_click"
    description = "Hace clic en un elemento web usando su action_id."

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action_id = params.get("action_id")
        if action_id is None:
            return {
                "error": "missing_param",
                "message": "Falta el parámetro 'action_id'.",
            }
        try:
            aid = int(action_id)
        except ValueError:
            return {"error": "invalid_param", "message": "action_id debe ser entero."}
        engine = BrowserEngine()
        if not getattr(engine, "initialized", False) or not getattr(
            engine, "loop", None
        ):
            return {"error": "browser_engine_not_initialized"}
        return _run_on_engine(engine.click(aid), engine, timeout=15.0)


class BrowserFillTool(ToolV3):
    name = "browser_fill"
    description = "Escribe texto en un campo de entrada identificado por action_id."

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action_id = params.get("action_id")
        text = params.get("text") or ""
        if action_id is None:
            return {"error": "missing_param", "message": "Falta 'action_id'."}
        engine = BrowserEngine()
        try:
            aid = int(action_id)
        except ValueError:
            return {"error": "invalid_param", "message": "action_id debe ser entero."}
        if not getattr(engine, "initialized", False) or not getattr(
            engine, "loop", None
        ):
            return {"error": "browser_engine_not_initialized"}
        return _run_on_engine(engine.fill(aid, text), engine, timeout=10.0)


class BrowserScrollTool(ToolV3):
    name = "browser_scroll"
    description = (
        "Desplaza el viewport hacia arriba o abajo y devuelve el nuevo estado."
    )

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        direction = (params.get("direction") or "down").strip().lower()
        if direction not in ("up", "down"):
            direction = "down"
        engine = BrowserEngine()
        if not getattr(engine, "initialized", False) or not getattr(
            engine, "loop", None
        ):
            return {"error": "browser_engine_not_initialized"}
        return _run_on_engine(engine.scroll(direction), engine, timeout=10.0)


class BrowserExtractTool(ToolV3):
    name = "browser_extract"
    description = "Extrae información heurística del content_markdown proporcionado."

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        content = params.get("content_markdown") or ""
        lines = content.splitlines()
        query = params.get("query") or []
        if isinstance(query, str):
            query = [w.strip().lower() for w in query.split() if w.strip()]
        else:
            query = [str(w).lower().strip() for w in query if str(w).strip()]

        if not lines or not query:
            return {"found": False, "extracted_data": "", "hint": "no_query_or_content"}

        matches: List[int] = []
        for idx, line in enumerate(lines):
            lower = line.lower()
            if any(k in lower for k in query):
                matches.append(idx)

        if not matches:
            return {
                "found": False,
                "extracted_data": "",
                "hint": "no_match_in_viewport",
            }

        window = 2
        selected_lines: List[str] = []
        seen = set()
        for idx in matches:
            start = max(0, idx - window)
            end = min(len(lines), idx + window + 1)
            for i in range(start, end):
                if i not in seen:
                    seen.add(i)
                    selected_lines.append(lines[i])

        snippet = "\n".join(selected_lines)
        return {"found": True, "extracted_data": snippet[:2000]}
