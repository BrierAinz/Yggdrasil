from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from .distiller import distill_html_to_markdown

logger = logging.getLogger(__name__)


class BrowserEngine:
    _instance: Optional["BrowserEngine"] = None
    _lease_lock = threading.Lock()

    def __new__(cls) -> "BrowserEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
            cls._instance._loop = None
        return cls._instance

    @classmethod
    def try_acquire_lease(cls) -> bool:
        """Fail-fast: True si se adquirió el lease del navegador."""
        try:
            return bool(cls._lease_lock.acquire(blocking=False))
        except Exception:
            return False

    @classmethod
    def release_lease(cls) -> None:
        try:
            cls._lease_lock.release()
        except Exception:
            pass

    async def start(self) -> None:
        """Inicializa Playwright de forma persistente. Llamar en lifespan FastAPI."""
        if self.initialized:
            return

        self._loop = asyncio.get_running_loop()
        try:
            self._playwright = await async_playwright().start()
        except Exception as e:
            # En algunos entornos Windows el loop no soporta subprocess_exec (NotImplementedError).
            # Para V1 permitimos que la API arranque sin BrowserEngine; las browser tools fallarán si se usan.
            logger.exception(
                "No se pudo iniciar Playwright en BrowserEngine.start(): %s", e
            )
            self.initialized = False
            return

        user_data_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "Data"
            / "browser_profile"
        )
        user_data_dir.mkdir(parents=True, exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        self.initialized = True
        logger.info("BrowserEngine iniciado de forma persistente.")

    async def stop(self) -> None:
        if not self.initialized:
            return
        try:
            await self._context.close()
            await self._playwright.stop()
        finally:
            self.initialized = False
            logger.info("BrowserEngine detenido.")

    async def _get_current_state(
        self, include_markdown: bool = False
    ) -> Dict[str, Any]:
        """Inyecta dom_tagger.js y devuelve BrowserState."""
        tagger_js_path = Path(__file__).parent / "dom_tagger.js"
        tagger_code = tagger_js_path.read_text(encoding="utf-8")

        tree_data = await self._page.evaluate(tagger_code)

        state: Dict[str, Any] = {
            "page_id": "v1-single-tab",
            "current_url": self._page.url,
            "title": await self._page.title(),
            "meta": tree_data.get("meta") or {},
            "actions_tree": tree_data.get("actions_tree") or [],
        }

        if include_markdown:
            raw_html = await self._page.content()
            state["content_markdown"] = distill_html_to_markdown(raw_html)

        return state

    async def goto(self, url: str) -> Dict[str, Any]:
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(800)
            return await self._get_current_state(include_markdown=True)
        except Exception as e:
            logger.error("Error en goto(%s): %s", url, e)
            shot = await self.screenshot_bytes("navigation_failed.png")
            out: Dict[str, Any] = {
                "error": "navigation_failed",
                "message": str(e),
                "fatal_error": True,
            }
            if isinstance(shot, dict) and shot.get("screenshot_id"):
                out["screenshot_id"] = shot["screenshot_id"]
            return out

    async def click(self, action_id: int) -> Dict[str, Any]:
        selector = f'[lilith-id="{action_id}"]'
        try:
            await self._page.click(selector, timeout=5000, force=False)
            await self._page.wait_for_timeout(500)
            return await self._get_current_state(include_markdown=False)
        except PlaywrightError as e:
            error_msg = str(e).lower()
            if "intercepted" in error_msg or "obscured" in error_msg:
                return {
                    "error": "element_blocked",
                    "message": "El elemento está bloqueado por un overlay (modal/banner). "
                    "Intenta buscar un botón de cerrar o hacer scroll.",
                    "browser_state": await self._get_current_state(
                        include_markdown=False
                    ),
                }
            logger.error("Error click (%s): %s", selector, e)
            shot = await self.screenshot_bytes("click_failed.png")
            out: Dict[str, Any] = {
                "error": "click_failed",
                "message": "Elemento no encontrado o no interactuable.",
                "fatal_error": True,
            }
            if isinstance(shot, dict) and shot.get("screenshot_id"):
                out["screenshot_id"] = shot["screenshot_id"]
            return out
        except Exception as e:
            logger.error("Error click (%s): %s", selector, e)
            shot = await self.screenshot_bytes("click_failed.png")
            out: Dict[str, Any] = {
                "error": "click_failed",
                "message": str(e),
                "fatal_error": True,
            }
            if isinstance(shot, dict) and shot.get("screenshot_id"):
                out["screenshot_id"] = shot["screenshot_id"]
            return out

    async def fill(self, action_id: int, text: str) -> Dict[str, Any]:
        selector = f'[lilith-id="{action_id}"]'
        try:
            await self._page.fill(selector, text, timeout=5000)
            return {"status": "filled_success", "actions_tree_status": "unchanged"}
        except Exception as e:
            logger.error("Error fill (%s): %s", selector, e)
            shot = await self.screenshot_bytes("fill_failed.png")
            out: Dict[str, Any] = {
                "error": "fill_failed",
                "message": str(e),
                "fatal_error": True,
            }
            if isinstance(shot, dict) and shot.get("screenshot_id"):
                out["screenshot_id"] = shot["screenshot_id"]
            return out

    async def scroll(self, direction: str) -> Dict[str, Any]:
        amount = 600 if direction == "down" else -600
        await self._page.evaluate(f"window.scrollBy(0, {amount})")
        await self._page.wait_for_timeout(500)
        return await self._get_current_state(include_markdown=False)

    async def screenshot_bytes(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Captura un screenshot de la página actual y lo guarda en Core/Data/temp_screenshots/.
        Devuelve {"screenshot_id": "<archivo.png>", "file_path": "<ruta>"} o {"error": "..."}.
        """
        if not self.initialized:
            return {"error": "browser_engine_not_initialized"}
        try:
            base_dir = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "Data"
                / "temp_screenshots"
            )
            base_dir.mkdir(parents=True, exist_ok=True)

            # Sanitizar nombre para evitar path traversal
            if filename:
                safe_name = Path(str(filename)).name
                if not safe_name.lower().endswith(".png"):
                    safe_name = safe_name + ".png"
            else:
                safe_name = f"panic_{int(asyncio.get_running_loop().time()*1000)}.png"

            out_path = base_dir / safe_name
            # playwright devuelve bytes, pero aquí nos basta con el archivo en disco
            await self._page.screenshot(path=str(out_path), full_page=True)
            return {"screenshot_id": safe_name, "file_path": str(out_path)}
        except Exception as e:
            logger.error("Error al capturar screenshot: %s", e)
            return {"error": "screenshot_failed", "message": str(e)}

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        return self._loop
