# Visión: Minería y Refinería Web

**Objetivo:** Que Lilith pueda actuar como **refinería de datos**: extraer materia prima caótica de la web, limpiarla, validarla y estructurarla hasta convertirla en conocimiento utilizable (memoria semántica, hechos, índices). No se busca un dataset limpio ya hecho; Lilith **produce** el oro a partir de la minería web.

**Encaje con 4.0:** Los agentes de dominio (WebScraperAgent, ContentCleanerAgent, etc.) encajan en el ecosistema de agentes autónomos y en el AgentRegistry. Este documento define la estrategia de alto nivel y las tácticas de implementación por fases.

---

## Nivel 1: Estrategia — El flujo de refinería

| Fase | Nombre | Descripción |
|------|--------|-------------|
| 1 | **Extracción (Mining)** | Lilith extrae texto crudo de diversas fuentes web. |
| 2 | **Limpieza y normalización (Cleaning)** | Elimina ruido, HTML, anuncios, boilerplate. |
| 3 | **Validación y filtrado (Filtering)** | Descarta información de baja calidad, propaganda o irrelevante. |
| 4 | **Estructuración y almacenamiento (Structuring)** | Convierte el texto limpio en formato estructurado (JSON, grafo) para uso eficiente. |
| 5 | **Indexación (Indexing)** | Crea índices (full-text, embeddings) para que los datos limpios sean recuperables. |

---

## Nivel 2: Fuentes de datos (las minas)

No todas las minas son iguales. Lilith debe operar según el tipo de fuente.

| Tipo | Ejemplos | Calidad | Estrategia |
|------|----------|---------|------------|
| **Alta calidad (vetas puras)** | Wikis (Wikipedia, wikis especializadas), documentación oficial (MDN, W3C), artículos científicos (arXiv, PubMed), foros técnicos moderados (Stack Overflow) | Muy alta | Extracción profunda y estructurada. Ideal para conocimiento base. |
| **Media calidad (minerales mixtos)** | Blogs técnicos de reputación, noticias de medios serios, repos (READMEs), papers y blogs de investigación | Media | Extracción selectiva y validación cruzada. Fuerte filtrado. |
| **Baja calidad (roca y escombros)** | Redes sociales (X, Reddit), foros no moderados, comentarios, contenido IA a gran escala | Baja | Extracción superficial o evitar. Coste de limpieza alto. Solo para tendencias o sentimiento. |

---

## Nivel 3: Arsenal de herramientas (agentes de dominio)

Cada agente es una pieza del equipo de minería. Encajan como **tools** o **agentes** en el ecosistema 4.0.

### WebScraperAgent

| Aspecto | Descripción |
|---------|-------------|
| **Función** | Navegar por sitios web y extraer el contenido textual principal. |
| **Stack** | `requests` + BeautifulSoup4 (o Scrapy para proyectos grandes). |
| **Config** | Lista de dominios permitidos (whitelist), reglas de extracción (selectores CSS, qué ignorar), respeto a robots.txt. |
| **Salida** | Texto crudo limpio de HTML. |

### ContentCleanerAgent

| Aspecto | Descripción |
|---------|-------------|
| **Función** | Tomar el texto crudo del scraper y limpiarlo. |
| **Procesos** | Eliminar HTML/XML residual; anuncios, menús, pies de página; normalizar espacios y caracteres; detección y eliminación de boilerplate. |
| **Salida** | Párrafos de texto limpios. |

### QualityFilterAgent ✅ (4.0 Fase 3b — implementado)

| Aspecto | Descripción |
|---------|-------------|
| **Función** | Evaluar calidad y relevancia del texto limpio. |
| **Criterios** | Longitud (`min_length`, `ideal_min_length`); densidad de información (palabras sustantivas vs. stopwords ES/EN); umbral `min_score` en `Config/quality_filter.json`. Opcional futuro: LLM local para coherencia; validación cruzada. |
| **Salida** | Texto validado con prefijo `[Calidad validada: score]` o mensaje de filtrado si no supera el umbral. |

### DataStructurerAgent ✅ (4.0 Fase 4 — implementado)

| Aspecto | Descripción |
|---------|-------------|
| **Función** | Convertir párrafos validados en formato estructurado. |
| **Procesos** | Extracción de entidades (ALL_CAPS, CamelCase, términos técnicos); resumen extractivo; clasificación por tópico (keywords → Base de datos/PostgreSQL, ML, etc.). Config: `Config/data_structurer.json`. |
| **Salida** | Texto formateado `[Minería web] Tópico: … Resumen: … Conceptos: …` listo para guardar con la tool `store_semantic_fact`. |

---

## Nivel 4: Flujo de trabajo en la práctica

**Ejemplo de orden (owner):** *"Lilith, investiga sobre optimización de consultas en PostgreSQL. Busca en la web, filtra solo fuentes de alta calidad y guárdalo estructurado en mi memoria."*

**Plan interno (Planner + agentes):**

| Paso | Agente | Acción |
|------|--------|--------|
| 1 | WebScraperAgent | Buscar en postgresql.org/docs, wiki.postgresql.org, blogs de referencia. |
| 2 | ContentCleanerAgent | Limpiar el contenido extraído. |
| 3 | QualityFilterAgent | Evaluar y descartar contenido de baja calidad o sin fundamento. |
| 4 | DataStructurerAgent | Extraer conceptos clave (EXPLAIN ANALYZE, VACUUM, índices, JOIN strategies), resumir y clasificar. |
| 5 | StoreSemanticFact / memoria | Guardar los hechos estructurados en memoria semántica (o MuninnDB, grafo). |

**Resultado:** Memoria enriquecida con datos limpios, estructurados y validados sobre el tema, extraídos de fuentes de alta calidad.

---

## Nivel 5: Arquitectura de soporte (escala)

Para operar a escala:

| Componente | Propósito |
|------------|-----------|
| **Cola de tareas** | No bloquear a Lilith mientras se descargan y procesan páginas. Ej.: Celery o cola simple con Redis. |
| **Base de datos de conocimiento** | Almacenar datos estructurados. Base de grafos (Neo4j) ideal para conectar conceptos (ej. "PostgreSQL" → TIENE → "Índice" → OPTIMIZA → "Rendimiento"). |
| **Caché de contenido** | Evitar redescargan. Ej.: requests-cache o capa propia. |
| **Manejo de errores y reintentos** | Robustez ante 404, 500, timeouts, cambios de estructura de página. |

---

## Recomendación de implementación

**Empezar pequeño e iterar:**

1. **Fase A — WebScraperAgent básico**  
   Extraer texto de una sola fuente de alta calidad (ej. documentación oficial de PostgreSQL). Dominios permitidos en config; respeto a robots.txt; salida texto crudo.

2. **Fase B — ContentCleanerAgent**  
   Segunda capa: recibir salida del scraper, limpiar HTML residual, boilerplate y normalizar. Salida: párrafos limpios.

3. **Fase C — QualityFilterAgent**  
   Evaluar y filtrar por longitud, densidad, coherencia (heurísticos o LLM local). Añadir `quality_score` y umbral mínimo.

4. **Fase D — DataStructurerAgent**  
   Extracción de entidades, resumen, clasificación por tópico. Salida: JSON estructurado listo para memoria.

5. **Fase E — Integración con memoria**  
   Conectar la salida estructurada a memoria semántica / MuninnDB / StoreSemanticFact para que Lilith “aprenda” lo extraído.

6. **Escala**  
   Cuando el flujo esté probado: cola de tareas, caché, y (opcional) base de grafos para conocimiento conectado.

---

## Relación con el resto del roadmap

- **Misión 4.0 Fase 1 (AgentRegistry):** Implementado. WebScraperAgent, ContentCleanerAgent, etc. se registrarán como nuevas clases `Agent` en `AgentRegistry` (ver `Backend/core/agent_registry.py`).
- **Horizonte 4.0 (memoria en grafo):** El DataStructurerAgent y el almacenamiento estructurado pueden alimentar una futura base de grafos.
- **Config / seguridad:** Dominios permitidos, rate limiting y respeto a robots.txt deben vivir en config (ej. `security.json` o `web_sources.json`).

---

*Documento de visión. Priorización y fases concretas según necesidad del proyecto y disponibilidad de recursos.*
