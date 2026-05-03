# Misión 37: Knowledge Mining Pipeline v2 - v5.5

> **Versión objetivo**: Lilith v5.5
> **Feature**: Advanced Knowledge Mining & Curation
> **Prioridad**: Alta (intelligence expansion)
> **Esfuerzo estimado**: 24-30 horas
> **Dependencias**: v5.4 (Browser Automation), MuninnDB

---

## 🎯 Objetivo

Implementar un pipeline avanzado de **mineria y curacion de conocimiento** que permita a Lilith:
- Descubrir fuentes de informacion de alta calidad automaticamente
- Extraer conocimiento estructurado desde multiples formatos
- Curar y validar informacion antes de almacenarla
- Mantener un grafo de conocimiento actualizado
- Detectar contradicciones y actualizar creencias

**Estado actual**: Scraping basico, memoria reactiva
**Estado deseado**: Pipeline inteligente de knowledge mining con curacion proactiva

---

## 💡 Motivacion

### Problemas Actuales

```
Usuario: "Investiga sobre X tecnologia"
Sistema actual:
→ Web search → Extraer texto
→ Guardar en memoria sin validacion
→ No detecta fuentes de baja calidad
→ No actualiza informacion obsoleta

Resultado: Memoria contaminada con info de calidad variable
```

**Issues**:
- No hay validacion de fuentes
- Informacion obsoleta no se actualiza
- No detecta contradicciones
- No hay curacion de calidad
- Knowledge graph estatico

### Solucion: Knowledge Mining Pipeline v2

```
Usuario: "Investiga sobre X tecnologia"

Pipeline v2:
→ 1. Source Discovery (encuentra fuentes confiables)
→ 2. Multi-format Extraction (docs, videos, papers)
→ 3. Quality Scoring (evalua credibilidad)
→ 4. Fact Extraction (triples RDF)
→ 5. Contradiction Detection (vs knowledge graph)
→ 6. Curation (humano-en-el-loop para conflictos)
→ 7. Knowledge Graph Update (edges + metadata)
→ 8. Obsolescence Detection (marca info vieja)

Resultado: Knowledge graph curado y actualizado
```

---

## 🏗️ Arquitectura

### Pipeline Completo

```
┌─────────────────────────────────────────────────────────┐
│                 Knowledge Mining Pipeline v2             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. SOURCE DISCOVERY                                    │
│     ├─ Seed URLs                                        │
│     ├─ Related page crawling                            │
│     ├─ Authority detection (PageRank-like)              │
│     └─ Source quality scoring                           │
│                                                         │
│  2. MULTI-FORMAT EXTRACTION                             │
│     ├─ Web pages (Playwright + Readability)             │
│     ├─ PDFs (pdfplumber + OCR)                          │
│     ├─ Videos (YouTube transcripts)                     │
│     └─ Academic papers (arXiv, PubMed)                  │
│                                                         │
│  3. CONTENT PROCESSING                                  │
│     ├─ Chunking (semantico, no fijo)                    │
│     ├─ Entity extraction (NER)                          │
│     ├─ Fact extraction (triple extraction)              │
│     └─ Summarization (multi-level)                      │
│                                                         │
│  4. QUALITY CURATION                                    │
│     ├─ Source credibility scoring                       │
│     ├─ Fact verification (cross-reference)              │
│     ├─ Contradiction detection                          │
│     ├─ Recency scoring                                  │
│     └─ Human-in-the-loop (conflictos)                   │
│                                                         │
│  5. KNOWLEDGE GRAPH UPDATE                              │
│     ├─ MuninnDB edge creation                           │
│     ├─ Metadata enrichment                              │
│     ├─ Obsolescence marking                             │
│     └─ Graph queries optimizadas                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Componentes Nuevos

#### 1. `SourceDiscoveryEngine`

**Ubicacion**: `Core/Backend/core/knowledge/source_discovery.py`

```python
class SourceDiscoveryEngine:
    """
    Descubre fuentes de informacion de alta calidad.

    Estrategias:
    - Seed expansion (crawl related pages)
    - Authority detection (domain reputation)
    - Citation analysis (papers citando papers)
    - Social signals (Reddit, HN mentions)
    """

    async def discover_sources(
        self,
        topic: str,
        seed_urls: Optional[List[str]] = None,
        max_sources: int = 50
    ) -> List[Source]:
        """Descubre fuentes relevantes para un topic"""

        sources = []

        # 1. Buscar seeds si no hay
        if not seed_urls:
            seed_urls = await self._search_initial_seeds(topic)

        # 2. Expandir desde seeds
        for seed in seed_urls:
            related = await self._crawl_related_pages(
                url=seed,
                max_depth=2,
                same_domain_only=False
            )
            sources.extend(related)

        # 3. Score por calidad
        scored_sources = [
            Source(
                url=url,
                title=title,
                quality_score=await self._score_source_quality(url),
                authority_score=await self._calculate_authority(url),
                relevance_score=await self._score_relevance(url, topic)
            )
            for url, title in sources
        ]

        # 4. Filtrar y rankear
        filtered = [s for s in scored_sources if s.quality_score > 0.6]
        ranked = sorted(filtered, key=lambda s: s.composite_score(), reverse=True)

        return ranked[:max_sources]

    async def _score_source_quality(self, url: str) -> float:
        """Score calidad de fuente"""

        factors = {
            'domain_reputation': await self._check_domain_reputation(url),
            'https': 1.0 if url.startswith('https') else 0.5,
            'has_author': await self._has_author_info(url),
            'has_date': await self._has_publication_date(url),
            'no_ads': await self._check_ad_presence(url),
            'mobile_friendly': await self._check_mobile_friendly(url)
        }

        weights = {
            'domain_reputation': 0.4,
            'https': 0.1,
            'has_author': 0.2,
            'has_date': 0.15,
            'no_ads': 0.1,
            'mobile_friendly': 0.05
        }

        score = sum(factors[k] * weights[k] for k in factors)
        return min(max(score, 0.0), 1.0)
```

#### 2. `MultiFormatExtractor`

**Ubicacion**: `Core/Backend/core/knowledge/multi_format_extractor.py`

```python
class MultiFormatExtractor:
    """
    Extrae contenido de multiples formatos.

    Soporta:
    - Web pages (HTML)
    - PDFs (text + OCR)
    - Videos (transcripts)
    - Academic papers
    """

    async def extract_content(
        self,
        url: str,
        format: Optional[str] = None
    ) -> ExtractedContent:
        """Extrae contenido detectando formato automaticamente"""

        if not format:
            format = self._detect_format(url)

        if format == 'html':
            return await self._extract_webpage(url)
        elif format == 'pdf':
            return await self._extract_pdf(url)
        elif format == 'video':
            return await self._extract_video_transcript(url)
        elif format == 'paper':
            return await self._extract_academic_paper(url)
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def _extract_webpage(self, url: str) -> ExtractedContent:
        """Extrae contenido de webpage usando Playwright + Readability"""

        from readability import Document

        browser = PlaywrightBrowser()
        page_content = await browser.navigate_and_extract(url)

        doc = Document(page_content['html'])

        return ExtractedContent(
            url=url,
            title=doc.title(),
            content=doc.summary(),
            text=self._html_to_text(doc.summary()),
            metadata={
                'author': self._extract_author(page_content['html']),
                'date': self._extract_date(page_content['html']),
                'format': 'html'
            }
        )

    async def _extract_pdf(self, url: str) -> ExtractedContent:
        """Extrae contenido de PDF con OCR fallback"""

        import pdfplumber
        from pdf2image import convert_from_bytes
        import pytesseract

        pdf_bytes = await self._download_file(url)

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text = '\n'.join(page.extract_text() for page in pdf.pages)

            if len(text.strip()) < 100:
                images = convert_from_bytes(pdf_bytes)
                text = '\n'.join(pytesseract.image_to_string(img) for img in images)

        except Exception as e:
            return ExtractedContent(url=url, error=str(e))

        return ExtractedContent(
            url=url,
            title=self._extract_pdf_title(text),
            content=text,
            text=text,
            metadata={'format': 'pdf'}
        )

    async def _extract_video_transcript(self, url: str) -> ExtractedContent:
        """Extrae transcript de video (YouTube)"""

        from youtube_transcript_api import YouTubeTranscriptApi

        video_id = self._extract_youtube_id(url)

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = ' '.join([entry['text'] for entry in transcript])

            return ExtractedContent(
                url=url,
                title=await self._get_youtube_title(video_id),
                content=text,
                text=text,
                metadata={
                    'format': 'video',
                    'duration': sum(entry['duration'] for entry in transcript)
                }
            )

        except Exception as e:
            return ExtractedContent(url=url, error=str(e))
```

#### 3. `FactExtractor`

**Ubicacion**: `Core/Backend/core/knowledge/fact_extractor.py`

```python
class FactExtractor:
    """
    Extrae facts estructurados (triples RDF) desde texto.

    Triple format: (subject, predicate, object)
    Ejemplo: ("Python", "is_a", "programming language")
    """

    async def extract_facts(
        self,
        text: str,
        context: Optional[Dict] = None
    ) -> List[Fact]:
        """Extrae triples desde texto"""

        # 1. NER (Named Entity Recognition)
        entities = await self._extract_entities(text)

        # 2. Dependency parsing
        dependencies = await self._parse_dependencies(text)

        # 3. Pattern matching
        patterns = await self._apply_patterns(text)

        # 4. LLM-based extraction
        llm_facts = await self._llm_extract(text, entities)

        # 5. Merge y score
        all_facts = entities + dependencies + patterns + llm_facts
        scored_facts = [
            Fact(
                subject=f.subject,
                predicate=f.predicate,
                object=f.object,
                confidence=self._score_fact_confidence(f, text),
                source=context.get('url') if context else None,
                timestamp=datetime.now()
            )
            for f in all_facts
        ]

        return [f for f in scored_facts if f.confidence > 0.7]
```

#### 4. `ContradictionDetector`

**Ubicacion**: `Core/Backend/core/knowledge/contradiction_detector.py`

```python
class ContradictionDetector:
    """
    Detecta contradicciones entre facts nuevos y knowledge graph.
    """

    async def detect_contradictions(
        self,
        new_facts: List[Fact],
        knowledge_graph: KnowledgeGraph
    ) -> List[Contradiction]:
        """Detecta contradicciones"""

        contradictions = []

        for fact in new_facts:
            existing = await knowledge_graph.query_facts(
                subject=fact.subject,
                predicate=fact.predicate
            )

            for ex_fact in existing:
                if self._are_contradictory(fact.object, ex_fact.object):
                    contradiction = Contradiction(
                        fact1=fact,
                        fact2=ex_fact,
                        type=self._classify_contradiction(fact, ex_fact),
                        confidence=self._score_contradiction(fact, ex_fact),
                        resolution_strategy=self._suggest_resolution(fact, ex_fact)
                    )
                    contradictions.append(contradiction)

        return contradictions

    def _are_contradictory(self, obj1: str, obj2: str) -> bool:
        """Determina si dos objects son contradictorios"""

        if obj1 == obj2:
            return False

        if self._is_number(obj1) and self._is_number(obj2):
            diff_pct = abs(float(obj1) - float(obj2)) / max(float(obj1), float(obj2))
            return diff_pct > 0.1

        if obj1 in ['true', 'false'] and obj2 in ['true', 'false']:
            return obj1 != obj2

        return await self._llm_compare_contradiction(obj1, obj2)
```

#### 5. `KnowledgeCurator`

**Ubicacion**: `Core/Backend/core/knowledge/knowledge_curator.py`

```python
class KnowledgeCurator:
    """
    Cura knowledge graph con human-in-the-loop.

    Workflow:
    1. Detecta contradicciones
    2. Genera opciones de resolucion
    3. Pide input a usuario (para conflictos)
    4. Actualiza graph con decision
    """

    async def curate_facts(
        self,
        facts: List[Fact],
        contradictions: List[Contradiction],
        auto_resolve: bool = False
    ) -> CurationResult:
        """Cura facts con resolucion de conflictos"""

        accepted_facts = []
        rejected_facts = []
        pending_review = []

        for fact in facts:
            fact_contradictions = [
                c for c in contradictions
                if c.fact1 == fact or c.fact2 == fact
            ]

            if not fact_contradictions:
                accepted_facts.append(fact)
            elif auto_resolve:
                resolution = self._auto_resolve(fact, fact_contradictions)
                if resolution == 'accept':
                    accepted_facts.append(fact)
                else:
                    rejected_facts.append(fact)
            else:
                pending_review.append({
                    'fact': fact,
                    'contradictions': fact_contradictions,
                    'suggested_resolution': self._suggest_resolution(
                        fact,
                        fact_contradictions
                    )
                })

        return CurationResult(
            accepted=accepted_facts,
            rejected=rejected_facts,
            pending_review=pending_review
        )
```

---

## 📋 Alcance (Scope)

### ✅ Fase 1: Source Discovery & Extraction (v5.5.0)

1. **Source Discovery**
   - Seed expansion
   - Quality scoring
   - Authority detection

2. **Multi-format Extraction**
   - Web pages (Playwright + Readability)
   - PDFs (pdfplumber + OCR)
   - Videos (YouTube transcripts)

3. **Content Processing**
   - Semantic chunking
   - Entity extraction (NER)
   - Summarization

### ✅ Fase 2: Curation & Graph (v5.5.0)

1. **Fact Extraction**
   - Triple extraction (RDF)
   - LLM-based extraction
   - Confidence scoring

2. **Quality Curation**
   - Contradiction detection
   - Human-in-the-loop
   - Auto-resolution heuristics

3. **Knowledge Graph Update**
   - MuninnDB edge creation
   - Metadata enrichment
   - Obsolescence marking

### ❌ NO Incluido (v5.6+)

- Academic paper deep analysis
- Image content extraction
- Audio processing
- Real-time knowledge updates
- Multi-language support

---

## 🎯 Criterios de Éxito

| Metrica | Objetivo |
|---------|----------|
| Source quality avg | >0.75 |
| Fact extraction accuracy | >85% |
| Contradiction detection | >90% precision |
| Tests pasando | 24/24 (100%) |

---

## 📦 Archivos a Crear

### Nuevos (15 archivos)
```
Core/Backend/core/knowledge/
├── __init__.py
├── source_discovery.py           # Source discovery engine
├── multi_format_extractor.py     # Multi-format extraction
├── fact_extractor.py             # Fact extraction (RDF triples)
├── contradiction_detector.py     # Contradiction detection
├── knowledge_curator.py          # Human-in-the-loop curation
└── knowledge_graph_manager.py    # Graph operations

Core/Tests/knowledge/
├── test_source_discovery.py      # 8 tests
├── test_fact_extractor.py        # 10 tests
└── test_contradiction_detector.py # 6 tests
```

---

## 🚀 Plan de Implementacion

**Total**: 24-30 horas

| Fase | Tiempo | Tareas |
|------|--------|--------|
| Fase 1 | 10-12h | Discovery & Extraction |
| Fase 2 | 8-10h | Fact Extraction |
| Fase 3 | 6-8h | Curation & Graph |

---

*Mision creada: 2026-03-26*
*Estado: 📋 Disenada, pendiente de implementacion*
*Prioridad: Alta (intelligence expansion)*
