"""
Lilith 4.2 — WebMiningOrchestrator: orquestador del pipeline de minería web.

Coordina el flujo completo: Scraping → Limpieza → Filtrado de calidad →
Estructuración → Almacenamiento en memoria semántica.

Pipeline:
  URL → WebScraperAgent → ContentCleanerAgent → QualityFilterAgent →
  DataStructurerAgent → MemoryStore
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .content_cleaner_agent import ContentCleanerAgent
from .data_structurer_agent import DataStructurerAgent
from .quality_filter_agent import QualityFilterAgent
from .web_mining_models import (
    BatchMiningResult,
    CleanedContent,
    MiningResult,
    ScrapedContent,
    ScrapingStrategy,
    SemanticFact,
    StructuredData,
    classify_source_quality,
)
from .web_scraper_agent import WebScraperAgent

logger = logging.getLogger("WebMiningOrchestrator")


class WebMiningOrchestrator:
    """
    Orquestador del pipeline de minería web.

    Ejecuta el pipeline completo: scrape → clean → filter → structure → store
    """

    def __init__(
        self,
        base_path: Optional[Path] = None,
        scraper: Optional[WebScraperAgent] = None,
        cleaner: Optional[ContentCleanerAgent] = None,
        filter_agent: Optional[QualityFilterAgent] = None,
        structurer: Optional[DataStructurerAgent] = None,
        memory_store=None,
    ):
        """
        Inicializa el orquestador.

        Args:
            base_path: Ruta base del proyecto (para config y data)
            scraper: Instancia de WebScraperAgent (opcional)
            cleaner: Instancia de ContentCleanerAgent (opcional)
            filter_agent: Instancia de QualityFilterAgent (opcional)
            structurer: Instancia de DataStructurerAgent (opcional)
            memory_store: Instancia de MemoryStore (opcional)
        """
        self.base_path = Path(base_path) if base_path else None

        # Inicializar agentes
        self.scraper = scraper or WebScraperAgent(self.base_path)
        self.cleaner = cleaner or ContentCleanerAgent(self.base_path)
        self.filter_agent = filter_agent or QualityFilterAgent(self.base_path)
        self.structurer = structurer or DataStructurerAgent(self.base_path)

        # Memoria
        self._memory_store = memory_store
        if memory_store is None and self.base_path:
            try:
                from .memory_store import MemoryStore

                self._memory_store = MemoryStore(self.base_path)
            except Exception as e:
                logger.warning("Could not initialize MemoryStore: %s", e)

        # Configuración
        self._config = self._load_config()

        # Estadísticas
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "rejected": 0,
            "failed": 0,
            "facts_generated": 0,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración del orquestador."""
        if not self.base_path:
            return {}
        try:
            from .json_safe import safe_load

            path = self.base_path / "Config" / "web_mining.json"
            if not path.exists():
                return {}
            data = safe_load(path, default={})
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def mine(
        self,
        url: str,
        strategy: Optional[ScrapingStrategy] = None,
        store_in_memory: bool = True,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> MiningResult:
        """
        Ejecuta el pipeline completo de minería para una URL.

        Args:
            url: URL a procesar
            strategy: Estrategia de scraping (opcional)
            store_in_memory: Si guardar facts en memoria semántica
            progress_callback: Callback de progreso (etapa, datos)

        Returns:
            MiningResult con el resultado del proceso
        """
        start_time = time.time()
        self._stats["total_processed"] += 1

        def _notify(stage: str, data: Any = None):
            if progress_callback:
                try:
                    progress_callback(stage, data)
                except Exception as e:
                    logger.debug("Progress callback error: %s", e)

        logger.info("[WebMining] Starting pipeline for: %s", url)
        _notify("started", {"url": url})

        # 1. Scrape
        _notify("scraping", {"url": url})
        try:
            scrape_params = {"url": url}
            if strategy:
                scrape_params["strategy"] = strategy.value

            scrape_result = await self.scraper.scrape(scrape_params)

            if scrape_result.get("error"):
                error_msg = scrape_result.get("response", "Unknown scraping error")
                error_type = scrape_result.get("error_type", "unknown")
                logger.error("[WebMining] Scraping failed: %s - %s", url, error_msg)
                self._stats["failed"] += 1
                return MiningResult(
                    url=url,
                    success=False,
                    error=f"[{error_type}] {error_msg}",
                    processing_time=time.time() - start_time,
                )

            scraped = scrape_result.get("scraped_content")
            if not scraped:
                # Crear desde el resultado
                scraped = ScrapedContent(
                    url=url,
                    text=scrape_result.get("response", ""),
                    metadata=scrape_result.get("structured_data", {}),
                )

            logger.info("[WebMining] Scraped: %d chars from %s", len(scraped.text), url)
            _notify("scraped", {"url": url, "chars": len(scraped.text)})

        except Exception as e:
            logger.exception("[WebMining] Scraping exception: %s - %s", url, e)
            self._stats["failed"] += 1
            return MiningResult(
                url=url,
                success=False,
                error=f"Scraping exception: {e}",
                processing_time=time.time() - start_time,
            )

        # 2. Clean
        _notify("cleaning", {"url": url})
        try:
            cleaned = self.cleaner.clean_scraped(scraped)

            # Verificar si es duplicado
            is_dup, similarity = self.cleaner.detect_duplicate(cleaned)
            if is_dup:
                logger.info("[WebMining] Duplicate detected: %s", url)
                self._stats["rejected"] += 1
                return MiningResult(
                    url=url,
                    success=False,
                    error=f"Duplicate content detected (similarity: {similarity:.2f})",
                    processing_time=time.time() - start_time,
                )

            # Verificar si es aceptable
            if not self.cleaner.is_content_acceptable(cleaned):
                logger.info("[WebMining] Content not acceptable: %s", url)
                self._stats["rejected"] += 1
                return MiningResult(
                    url=url,
                    success=False,
                    error="Content does not meet minimum requirements",
                    processing_time=time.time() - start_time,
                )

            reduction = (
                1 - cleaned.cleaned_length / max(1, cleaned.original_length)
            ) * 100
            logger.info(
                "[WebMining] Cleaned: %d → %d chars (%.1f%% reduction)",
                cleaned.original_length,
                cleaned.cleaned_length,
                reduction,
            )
            _notify(
                "cleaned",
                {
                    "url": url,
                    "original": cleaned.original_length,
                    "cleaned": cleaned.cleaned_length,
                    "reduction": round(reduction, 1),
                },
            )

        except Exception as e:
            logger.exception("[WebMining] Cleaning exception: %s - %s", url, e)
            self._stats["failed"] += 1
            return MiningResult(
                url=url,
                success=False,
                error=f"Cleaning exception: {e}",
                processing_time=time.time() - start_time,
            )

        # 3. Filter Quality
        _notify("filtering", {"url": url})
        try:
            quality = self.filter_agent.assess_quality(cleaned)

            if not quality.is_accepted:
                logger.info(
                    "[WebMining] Rejected by quality filter: %s (score: %.2f)",
                    url,
                    quality.score,
                )
                self._stats["rejected"] += 1
                return MiningResult(
                    url=url,
                    success=False,
                    quality_score=quality,
                    error=f"Quality score {quality.score:.2f} below threshold",
                    processing_time=time.time() - start_time,
                )

            logger.info(
                "[WebMining] Quality accepted: %s (score: %.2f)", url, quality.score
            )
            _notify(
                "filtered",
                {
                    "url": url,
                    "score": quality.score,
                    "reasons": quality.reasons,
                },
            )

        except Exception as e:
            logger.exception("[WebMining] Quality filter exception: %s - %s", url, e)
            self._stats["failed"] += 1
            return MiningResult(
                url=url,
                success=False,
                error=f"Quality filter exception: {e}",
                processing_time=time.time() - start_time,
            )

        # 4. Structure
        _notify("structuring", {"url": url})
        try:
            structured = self.structurer.structure(cleaned)
            facts = self.structurer.to_semantic_facts(structured)

            logger.info(
                "[WebMining] Structured: %d entities, %d relations, %d facts",
                len(structured.entities),
                len(structured.relations),
                len(facts),
            )
            _notify(
                "structured",
                {
                    "url": url,
                    "entities": len(structured.entities),
                    "relations": len(structured.relations),
                    "facts": len(facts),
                },
            )

        except Exception as e:
            logger.exception("[WebMining] Structuring exception: %s - %s", url, e)
            self._stats["failed"] += 1
            return MiningResult(
                url=url,
                success=False,
                quality_score=quality,
                error=f"Structuring exception: {e}",
                processing_time=time.time() - start_time,
            )

        # 5. Store in memory
        if store_in_memory and facts:
            _notify("storing", {"url": url, "facts": len(facts)})
            try:
                stored_count = self.structurer.store_facts(
                    facts, memory_store=self._memory_store, base_path=self.base_path
                )
                self._stats["facts_generated"] += stored_count
                logger.info("[WebMining] Stored %d facts in memory", stored_count)
                _notify("stored", {"url": url, "stored": stored_count})

            except Exception as e:
                logger.warning("[WebMining] Failed to store facts: %s", e)
                # No fallar el pipeline por esto

        # Éxito
        self._stats["successful"] += 1
        processing_time = time.time() - start_time

        logger.info(
            "[WebMining] Pipeline completed successfully: %s (%.2fs)",
            url,
            processing_time,
        )
        _notify(
            "completed",
            {
                "url": url,
                "time": processing_time,
                "facts": len(facts),
            },
        )

        return MiningResult(
            url=url,
            success=True,
            facts=facts,
            quality_score=quality,
            processing_time=processing_time,
        )

    async def mine_batch(
        self,
        urls: List[str],
        strategy: Optional[ScrapingStrategy] = None,
        store_in_memory: bool = True,
        delay_seconds: float = 2.0,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> BatchMiningResult:
        """
        Procesa múltiples URLs en batch.

        Args:
            urls: Lista de URLs a procesar
            strategy: Estrategia de scraping (opcional)
            store_in_memory: Si guardar facts en memoria semántica
            delay_seconds: Delay entre requests
            progress_callback: Callback de progreso

        Returns:
            BatchMiningResult con estadísticas
        """
        results = []

        for i, url in enumerate(urls):
            logger.info("[WebMining] Batch progress: %d/%d - %s", i + 1, len(urls), url)

            try:
                result = await self.mine(
                    url,
                    strategy=strategy,
                    store_in_memory=store_in_memory,
                    progress_callback=progress_callback,
                )
                results.append(result)

            except Exception as e:
                logger.exception("[WebMining] Batch error for %s: %s", url, e)
                results.append(
                    MiningResult(
                        url=url,
                        success=False,
                        error=str(e),
                    )
                )

            # Rate limiting entre URLs
            if i < len(urls) - 1 and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        # Calcular estadísticas
        success = sum(1 for r in results if r.success)
        rejected = sum(
            1 for r in results if not r.success and r.quality_score is not None
        )
        failed = sum(1 for r in results if not r.success and r.quality_score is None)
        facts_generated = sum(len(r.facts) for r in results)

        batch_result = BatchMiningResult(
            total=len(urls),
            success=success,
            rejected=rejected,
            failed=failed,
            facts_generated=facts_generated,
            results=results,
        )

        logger.info(
            "[WebMining] Batch completed: %d total, %d success, %d rejected, %d failed, %d facts",
            batch_result.total,
            batch_result.success,
            batch_result.rejected,
            batch_result.failed,
            batch_result.facts_generated,
        )

        return batch_result

    def mine_sync(
        self,
        url: str,
        strategy: Optional[ScrapingStrategy] = None,
        store_in_memory: bool = True,
    ) -> MiningResult:
        """Versión síncrona de mine()."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run, self.mine(url, strategy, store_in_memory)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.mine(url, strategy, store_in_memory)
                )
        except RuntimeError:
            return asyncio.run(self.mine(url, strategy, store_in_memory))

    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas del orquestador."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Resetea las estadísticas."""
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "rejected": 0,
            "failed": 0,
            "facts_generated": 0,
        }

    def classify_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        """
        Clasifica URLs por calidad de fuente.

        Returns:
            Dict con listas de URLs por calidad
        """
        classified = {
            "high": [],
            "medium": [],
            "low": [],
            "unknown": [],
        }

        for url in urls:
            quality = classify_source_quality(url)
            classified[quality].append(url)

        return classified


# Instancia global para uso conveniente
_orchestrator_instance: Optional[WebMiningOrchestrator] = None


def get_orchestrator(base_path: Optional[Path] = None) -> WebMiningOrchestrator:
    """Obtiene o crea la instancia global del orquestador."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = WebMiningOrchestrator(base_path)
    return _orchestrator_instance


def reset_orchestrator() -> None:
    """Resetea la instancia global (útil para testing)."""
    global _orchestrator_instance
    _orchestrator_instance = None
