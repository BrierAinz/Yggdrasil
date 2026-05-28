# Horror GameMaster — Roadmap

> BrierStudios — Procedural Terror Engine
> Creado: 2026-05-27

---

## FASE 1 — Fundamentos (Semana 1)

### 1.1 Dataset de Terror
- [x] Recopilar narrativa de terror psicológico (novelas, creepypastas, guiones)
- [x] Clasificar por tipo de miedo (darkness, isolation, psychological, etc.)
- [x] Crear dataset de escenarios procedurales
- [x] Crear dataset de diálogos de NPCs de terror
- [x] Formatear para fine-tuning (JSON/JSONL)

### 1.2 Fine-tuning del LLM
- [x] Seleccionar modelo base (dolphin-mistral, qwen2.5-coder, etc.)
- [x] Preparar dataset en formato Ollama/LM Studio
- [ ] Fine-tune con Unsloth o LM Studio
- [ ] Evaluar calidad de generación de terror
- [x] Crear Modelfile para Ollama

### 1.3 Embeddings y Memoria
- [x] Configurar nomic-embed-text para embeddings
- [x] Crear vector store para patrones del jugador
- [x] Implementar persistencia de perfil entre sesiones
- [x] Crear sistema de "memoria de miedo" (qué asustó al jugador antes)

---

## FASE 2 — Motor de Terror (Semana 2)

### 2.1 Pattern Analyzer v2
- [x] Mejorar detección de patrones (más de 10 acciones)
- [x] Agregar análisis de tiempo entre acciones
- [x] Crear "fingerprint" psicológico del jugador
- [x] Implementar detección de "habituación" (cuando el jugador se acostumbra)

### 2.2 Procedural Generator v2
- [x] Agregar 20+ templates de escenas
- [x] Implementar "chain events" (eventos encadenados)
- [x] Crear sistema de "red herrings" (pistas falsas)
- [x] Implementar "safe rooms" que luego dejan de ser seguras

### 2.3 Tension Manager
- [x] Crear curva de tensión dinámica
- [x] Implementar "cooldown" después de sustos
- [x] Crear "false security" (sensación de seguridad falsa)
- [x] Implementar "escalation ladder" (escalada gradual)

---

## FASE 3 — Integración LLM (Semana 3)

### 3.1 LLM Engine v2
- [ ] Integrar modelo fine-tuned de terror
- [ ] Implementar streaming de respuestas
- [ ] Crear system prompts especializados por tipo de miedo
- [ ] Implementar "narrator voice" consistente

### 3.2 Context Manager
- [ ] Mantener contexto de la sesión actual
- [ ] Implementar "foreshadowing" (anticipación de eventos)
- [ ] Crear "callback system" (referenciar eventos pasados)
- [ ] Implementar "red thread" (hilos narrativos conectados)

### 3.3 NPC Intelligence
- [ ] Crear comportamientos complejos para NPCs
- [ ] Implementar "trust system" (el jugador desconfía de NPCs)
- [ ] Crear NPCs que "aprenden" del jugador
- [ ] Implementar "doppelganger mechanic"

---

## FASE 4 — Frontend (Semana 4)

### 4.1 Terminal UI
- [ ] Crear interfaz de terminal con Rich
- [ ] Implementar "typing effect" para narrativa
- [ ] Crear sistema de elecciones con timer
- [ ] Implementar efectos de sonido (opcional)

### 4.2 Web UI (Opcional)
- [ ] Crear interfaz web con FastAPI + HTMX
- [ ] Implementar "atmospheric effects" (CSS animations)
- [ ] Crear sistema de "ambient sound"
- [ ] Implementar "dark mode" optimizado para terror

---

## FASE 5 — Testing y Polish (Semana 5)

### 5.1 Testing
- [ ] Crear tests unitarios para cada componente
- [ ] Implementar integration tests
- [ ] Crear "stress tests" (sesiones largas)
- [ ] Testear con usuarios reales

### 5.2 Polish
- [ ] Optimizar rendimiento del LLM
- [ ] Mejorar calidad de la narrativa
- [ ] Crear "content warnings" apropiados
- [ ] Documentar API y uso

---

## FASE 6 — Deploy y Distribución (Semana 6)

### 6.1 Packaging
- [ ] Crear paquete pip instalable
- [ ] Crear Docker container
- [ ] Documentar instalación
- [ ] Crear ejemplo de uso

### 6.2 Distribución
- [ ] Publicar en GitHub
- [ ] Crear landing page
- [ ] Escribir blog post
- [ ] Crear video demo

---

## Stack Tecnológico

| Componente | Tecnología | Estado |
|-----------|------------|--------|
| LLM Base | dolphin-mistral / qwen2.5-coder | Disponible |
| Embeddings | nomic-embed-text | Disponible |
| Fine-tuning | Unsloth / LM Studio | Pendiente |
| Framework | Python + FastAPI | Implementado |
| Terminal UI | Rich | Pendiente |
| Web UI | FastAPI + HTMX | Pendiente |
| Database | SQLite + ChromaDB | Pendiente |
| Testing | pytest | Pendiente |

---

## Prioridades Inmediatas

1. **Dataset** — Sin datos, no hay modelo
2. **Fine-tuning** — El corazón del proyecto
3. **Embeddings** — Memoria del jugador
4. **Terminal UI** — Para probar el concepto

---

**BrierStudios** — ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ
