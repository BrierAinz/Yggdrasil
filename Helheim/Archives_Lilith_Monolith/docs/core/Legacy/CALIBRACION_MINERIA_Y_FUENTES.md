# Calibración de la minería — Investigador de profundidad

Documento de referencia para afinar **qué** extraer y **de dónde**, antes de fijar objetivos concretos. Incluye las tres preguntas de calibración (con respuestas orientativas) y el catálogo de fuentes y tácticas recomendadas.

---

## 1. Preguntas de calibración

Estas respuestas orientan el tipo de contenido que debe priorizar la pipeline de minería. **Ajusta o sustituye** según tus prioridades reales.

### Sobre programación

| Opción A | Opción B | Calibración sugerida |
|----------|----------|------------------------|
| Tutoriales y sintaxis pura (referencia rápida, ejemplos de código) | Debates de arquitectura de sistemas y patrones de diseño | **Ambos, con énfasis configurable.** Para modelos de código y contexto técnico: sintaxis y tutoriales (GitHub .md, documentación oficial). Para decisiones de diseño y contexto a largo plazo: arquitectura y patrones (blogs, post-mortems, artículos). La configuración de fuentes y tópicos en DataStructurerAgent puede incluir ambos; los dominios y las URLs semilla definen el balance. |

**Si tuvieras que elegir uno primero:** sintaxis y documentación estructurada (.md, docs oficiales) alimentan mejor la memoria semántica y el RAG; la arquitectura y los patrones son el siguiente nivel una vez la base técnica está poblada.

---

### Sobre rol y lore

| Opción A | Opción B | Calibración sugerida |
|----------|----------|------------------------|
| Mecánicas y estadísticas (reglas D&D, tablas, loot, hechizos) para partidas | Mitología, simbolismo y worldbuilding complejo para poblar narrativamente los reinos de Yggdrasil | **Depende del uso.** Si el objetivo es asistencia en mesa (Dungeon Master asistente, consultas de reglas): priorizar mecánicas y datos estructurados (5eTools, Roll20, compendios). Si el objetivo es narrativa, atmósfera y coherencia de mundo en Yggdrasil: priorizar mitología, simbolismo y worldbuilding (wikis Fandom, lore profundo). Ambos pueden coexistir; las fuentes y el etiquetado por tópico (ej. "rol_mecanicas" vs "rol_lore") permiten enrutar después. |

**Si tuvieras que elegir uno primero:** para "poblar narrativamente los reinos de Yggdrasil" el worldbuilding y la mitología son el núcleo; las mecánicas son complemento para partidas o para cruzar datos (estadísticas de bestias, etc.) con ese lore.

---

### Sobre lenguaje de videojuegos

| Opción A | Opción B | Calibración sugerida |
|----------|----------|------------------------|
| Documentación técnica de motores (arquitectura de nodos, scripting, APIs) | Teoría de diseño de juegos (flujo de dificultad, diseño de niveles, game feel) | **Ambos, con rutas distintas.** Motores concretos (Unreal, Godot, tModLoader): documentación técnica y wikis de modding para "cómo se hace por dentro". Diseño de juegos (dificultad, niveles, feel): Game Developer, TIGSource, post-mortems. La minería puede etiquetar por tópico (ej. "motor_scripting" vs "diseno_niveles") para que Lilith o un sub-agente respondan según la pregunta. |

**Si tuvieras que elegir uno primero:** teoría de diseño (game feel, post-mortems) es más portable y narrativa; la documentación de motores es más técnica y específica. El orden puede ser: primero diseño y post-mortems para visión global; después motores y modding para implementación.

---

## 2. Fuentes recomendadas por dominio

Catálogo para configurar **allowed_domains**, URLs semilla y, cuando exista, **prioridad de APIs frente a scraping HTML**.

### 2.1 Programación y arquitectura (código y lógica)

| Fuente | Táctica | Notas |
|--------|---------|--------|
| **GitHub (repos y wikis)** | Extraer archivos **.md** (Markdown) de repositorios. No scraping de código fuente crudo (el QualityFilter puede penalizarlo). | Documentación técnica estructurada; ideal para memoria semántica. |
| **Stack Exchange / Stack Overflow** | **No** scraping en vivo (riesgo de bloqueo de IP). Usar **Data Dumps oficiales** de Stack Exchange (p. ej. en Internet Archive). XML masivo con preguntas y respuestas limpias. | Información pura sin pelear con el DOM. |
| **Dev.to / Hashnode** | Blogs de desarrolladores; HTML limpio y semántico. | Facilita el scraper y reduce falsos positivos en el filtro de densidad. |

### 2.2 Rol, lore y worldbuilding (narrativa y sistemas)

| Fuente | Táctica | Notas |
|--------|---------|--------|
| **Fandom / Wikia** | Usar **MediaWiki API**. La mayoría de wikis Fandom la exponen. Contenido en JSON o wikitexto; se evita HTML, anuncios y menús. | Evita todo el trabajo que haría el ContentCleaner sobre HTML. |
| **5eTools / Roll20 Compendium** | Datos muy estructurados (estadísticas de monstruos, hechizos, tablas de loot). | Ideal para un Dungeon Master asistente o consultas de reglas. |
| **Reddit** (r/worldbuilding, r/DnDBehindTheScreen, etc.) | Añadir **.json** al final de la URL del hilo; Reddit devuelve el hilo en JSON estructurado. | Sin parsear HTML complejo. |

### 2.3 Lenguaje de videojuegos (diseño y desarrollo)

| Fuente | Táctica | Notas |
|--------|---------|--------|
| **Game Developer** (antes Gamasutra) | Artículos, post-mortems, matemáticas aplicadas a mecánicas, narrativa interactiva. | Estándar de la industria. |
| **TIGSource Forums** | DevLogs (diarios de desarrollo); flujos de trabajo 2D/3D y resolución de problemas técnicos en desarrollo indie. | Cuna del indie. |
| **Documentación de modding** (p. ej. tModLoader) | Wikis de creadores de mods; puente entre programación y diseño de juegos (cómo alterar la lógica del motor). | Útil para motores concretos y comunidades. |

---

## 3. Nota de campo (realidad técnica)

> El scraping crudo de HTML es frágil: las páginas cambian y rompen los scripts.

**Prioridad de extracción:**

1. **APIs públicas** y **endpoints JSON** (ej. Reddit con `.json`, MediaWiki API).
2. **Data Dumps** oficiales (Stack Exchange, etc.) cuando estén disponibles.
3. Scraping HTML solo cuando no haya alternativa; restringir a dominios con estructura estable y contenido semántico (p. ej. Dev.to, documentación en .md vía GitHub).

Configurar `web_sources.json` (y futuras listas de URLs semilla) siguiendo esta prioridad reduce mantenimiento y mejora la calidad de la entrada al ContentCleaner y al QualityFilter.

---

## 4. Uso en el proyecto

- **Calibración:** Ajusta las respuestas de la sección 1 según si priorizas sintaxis vs arquitectura, mecánicas vs lore, motores vs diseño. Eso define qué fuentes y tópicos se añaden primero a DataStructurerAgent y a las URLs semilla.
- **Fuentes:** La sección 2 sirve para poblar `allowed_domains`, listas de URLs por dominio (programación, rol, juegos) y, cuando se implemente, adaptadores por fuente (API vs scraper).
- **Tácticas:** La sección 3 es la regla de oro para el pipeline: preferir API/JSON/dumps; usar scraping HTML con dominios curados y contenido en .md o HTML semántico cuando no haya otra opción.

---

*Documento de calibración para el Investigador de profundidad. Actualizar cuando se fijen objetivos concretos o nuevas fuentes.*
