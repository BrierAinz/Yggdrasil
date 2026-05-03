# 13 - Metacognición y Learning

> **Versión:** 4.0  
> **Fecha:** 2026-03-21  
> **Ubicación:** `Lilith/Core/Docs/13_METACOGNICION_LEARNING.md`

---

## 13.1 Visión General

El sistema de **Metacognición** permite a Lilith evaluar su propia confianza en decisiones y solicitar confirmación cuando es necesario. El **Learning Engine** aprende de interacciones pasadas para mejorar futuras decisiones.

```
┌─────────────────────────────────────────────────────────────┐
│                    CICLO DE APRENDIZAJE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Input del Usuario                                         │
│        ↓                                                    │
│   ┌─────────────┐     Umbral no alcanzado                   │
│   │ Metacog     │ ──────────────────────▶ Confirmación      │
│   │ (confianza) │                                          │
│   └─────────────┘     Umbral alcanzado                     │
│        ↓                                                    │
│   Planificación ──▶ Ejecución ──▶ Resultado                 │
│        │                              │                     │
│        │                              ↓                     │
│        │                        Feedback Implícito          │
│        │                              │                     │
│        └──────────────────────────────┘                     │
│                      ↓                                      │
│              Learning Engine                                │
│              (refuerzo/debilitamiento)                      │
│                      ↓                                      │
│              Memoria Procedural                             │
│              (patrones aprendidos)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 13.2 Sistema de Metacognición

### 13.2.1 Concepto

La metacognición es la capacidad de "pensar sobre el pensamiento". En Lilith, se implementa como:

1. **Evaluación de confianza** antes de ejecutar planes
2. **Detección de tools peligrosas** que requieren confirmación
3. **Solicitud de confirmación** al usuario cuando la confianza es baja

### 13.2.2 Configuración

```json
// Core/Config/metacognition.json
{
  "enabled": true,
  "confidence_threshold": 0.7,
  "require_confirmation_on_low": true,
  "low_confidence_message": "Mi mejor plan sería {plan_summary}, pero mi confianza es baja ({confidence:.0%}). ¿Quieres que lo ejecute?",
  "dangerous_tools": [
    "edit_file",
    "system_execute",
    "exec",
    "browser_goto",
    "browser_click",
    "browser_fill",
    "self_improve",
    "delegate_albedo"
  ]
}
```

### 13.2.3 Flujo de Decisión

```python
# Backend/core/metacognition/confidence_evaluator.py

class ConfidenceEvaluator:
    """
    Evalúa confianza de planes antes de ejecución.
    """
    
    def evaluate_plan(self, plan: Plan, context: dict) -> ConfidenceResult:
        """
        Retorna nivel de confianza y justificación.
        """
        scores = []
        
        # 1. Similitud con planes previos exitosos
        similar_plans = self._find_similar_successful_plans(plan)
        if similar_plans:
            scores.append(min(1.0, len(similar_plans) / 3))  # Max con 3+
        
        # 2. Complejidad vs capacidad conocida
        complexity_score = self._assess_complexity(plan)
        scores.append(1.0 - complexity_score * 0.2)  # Penaliza complejidad
        
        # 3. Tools peligrosas involucradas
        dangerous_count = sum(
            1 for step in plan.steps 
            if step.tool in DANGEROUS_TOOLS
        )
        if dangerous_count > 0:
            scores.append(0.5)  # Penalización fija
        
        # 4. Contexto disponible
        if context.get("session_memory"):
            scores.append(0.1)  # Bonus por contexto
        
        # Score final
        final_score = sum(scores) / len(scores) if scores else 0.5
        
        return ConfidenceResult(
            score=final_score,
            requires_confirmation=final_score < CONFIDENCE_THRESHOLD,
            reason=self._generate_reason(scores, plan)
        )
```

### 13.2.4 Interacción con Usuario

```
Usuario: "Borra todos los archivos de logs"

Lilith (Metacognición):
┌────────────────────────────────────────────────────┐
│ ⚠️  Confianza baja (45%)                           │
│                                                    │
│ Mi mejor plan sería:                               │
│ 1. Listar archivos en logs/                        │
│ 2. Eliminar cada archivo                           │
│                                                    │
│ Esto involucra la tool 'delete_file' que es        │
│ potencialmente destructiva.                        │
│                                                    │
│ [Ejecutar] [Cancelar] [Modificar]                  │
└────────────────────────────────────────────────────┘
```

---

## 13.3 Auditoría de Decisiones

### 13.3.1 Registro de Decisiones

Cada decisión importante del Planner se registra para análisis posterior:

```python
# Backend/core/auditor/decision_auditor.py

class DecisionAuditor:
    """
    Registra decisiones del Planner para auditoría.
    """
    
    def log_plan_decision(
        self,
        decision_type: str,      # "plan_generated", "intent_matched", etc.
        decision_source: str,    # "intent_patterns", "classifier", "learned_plan"
        input_data: dict,        # Input original
        output_data: dict,       # Output generado
        reason: str = None,      # Justificación (heurística)
        confidence: float = None,
        latency_ms: int = None
    ):
        """
        Escribe evento de auditoría en JSONL con rotación diaria.
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision_type": decision_type,
            "decision_source": decision_source,
            "input_hash": self._hash_input(input_data),
            "output_summary": self._summarize(output_data),
            "reason": reason or self._derive_reason(decision_source),
            "confidence": confidence,
            "latency_ms": latency_ms,
            "version": LILITH_VERSION
        }
        
        self._append_event(event)
```

### 13.3.2 Estructura de Archivos

```
Data/
├── decision_audit_2026-03-21.jsonl   # Logs del día
├── decision_audit_2026-03-20.jsonl   # Logs previos
└── decision_audit_*.jsonl            # Rotación diaria
```

### 13.3.3 Retención y Rotación

```python
# Rotación por fecha (archivo diario)
# Retención: 30 días por defecto

class DecisionAuditor:
    AUDIT_RETENTION_DAYS = 30
    _WRITE_LOCK = threading.Lock()
    
    def _get_audit_path(self) -> Path:
        """Retorna path del archivo de hoy (UTC)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return Path(f"Data/decision_audit_{today}.jsonl")
    
    def _append_event(self, event: dict):
        """Thread-safe append al archivo del día."""
        with self._WRITE_LOCK:
            path = self._get_audit_path()
            
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
            
            # Poda de archivos viejos (una vez por día)
            self._maybe_prune_old_files()
    
    def _prune_old_files(self):
        """Elimina archivos más antiguos que AUDIT_RETENTION_DAYS."""
        cutoff = datetime.utcnow() - timedelta(days=self.AUDIT_RETENTION_DAYS)
        
        for file in Path("Data").glob("decision_audit_*.jsonl"):
            # Extraer fecha del nombre
            date_str = file.stem.split('_')[-1]
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date < cutoff:
                file.unlink(missing_ok=True)
```

### 13.3.4 Consulta de Auditoría

```python
# API para consultar decisiones

@router.get("/api/audit/decisions")
async def get_audit_decisions(
    date: str = Query(None, description="YYYY-MM-DD, UTC"),
    decision_type: str = None,
    source: str = None,
    limit: int = 100
):
    """
    Recupera decisiones auditadas.
    """
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")
    
    path = f"Data/decision_audit_{date}.jsonl"
    
    decisions = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            event = json.loads(line)
            
            if decision_type and event["decision_type"] != decision_type:
                continue
            if source and event["decision_source"] != source:
                continue
                
            decisions.append(event)
            
            if len(decisions) >= limit:
                break
    
    return {
        "date": date,
        "count": len(decisions),
        "decisions": decisions
    }
```

---

## 13.4 Learning Engine

### 13.4.1 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    LEARNING ENGINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Pattern    │    │   Implicit  │    │  Matching   │     │
│  │  Detection  │    │   Feedback  │    │   Learner   │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                │
│                    ┌─────────────┐                          │
│                    │ Consolidator│                          │
│                    │ (cada 6h)   │                          │
│                    └──────┬──────┘                          │
│                           ▼                                 │
│                    ┌─────────────┐                          │
│                    │  Procedural │                          │
│                    │   Memory    │                          │
│                    └─────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 13.4.2 Configuración

```json
// Core/Config/learning.json
{
  "pattern_detection": {
    "enabled": true,
    "min_occurrences": 3,
    "lookback_days": 30,
    "notify_owner": true
  },
  "suggest_intents_threshold": 5,
  "feedback_reinforce_threshold": 4,
  "auto_apply_suggestions": false,
  "suggest_intent_patterns_limit_entries": 500,
  "matching_learning_enabled": true,
  "matching_learning_min_matches": 2,
  "matching_learning_confidence_threshold": 0.75,
  "implicit_feedback_enabled": true,
  "consolidation_enabled": true,
  "consolidation_interval_hours": 6,
  "consolidation_lookback_hours": 24,
  "reinforce_threshold": 2.0,
  "weaken_threshold": -1.5,
  "min_signals_for_retrain": 50
}
```

### 13.4.3 Pattern Detection

Detecta patrones recurrentes en las interacciones:

```python
# Backend/core/learning/pattern_detector.py

class PatternDetector:
    """
    Detecta patrones recurrentes en interacciones.
    """
    
    def detect_patterns(self, lookback_days: int = 30) -> List[Pattern]:
        """
        Analiza episodios recientes buscando patrones.
        """
        episodes = self._load_episodes(since=datetime.now() - timedelta(days=lookback_days))
        
        patterns = []
        
        # 1. Secuencias de tools frecuentes
        tool_sequences = self._extract_tool_sequences(episodes)
        for seq, count in tool_sequences.items():
            if count >= MIN_OCCURRENCES:
                patterns.append(Pattern(
                    type="tool_sequence",
                    data=seq,
                    occurrences=count,
                    confidence=min(1.0, count / 10)
                ))
        
        # 2. Intents no reconocidos frecuentes
        unknown_inputs = self._extract_unknown_inputs(episodes)
        clusters = self._cluster_similar(unknown_inputs)
        for cluster in clusters:
            if len(cluster) >= MIN_OCCURRENCES:
                patterns.append(Pattern(
                    type="potential_intent",
                    data=cluster[0],  # Representante
                    occurrences=len(cluster),
                    confidence=len(cluster) / 10,
                    examples=cluster[:5]
                ))
        
        return patterns
    
    def _extract_tool_sequences(self, episodes: List[Episode]) -> Counter:
        """Extrae secuencias de tools de episodios."""
        sequences = []
        
        for episode in episodes:
            if episode.plan_executed:
                tools = [step.tool for step in episode.plan_executed.steps]
                if len(tools) >= 2:
                    # Pares consecutivos
                    for i in range(len(tools) - 1):
                        seq = f"{tools[i]} -> {tools[i+1]}"
                        sequences.append(seq)
        
        return Counter(sequences)
```

### 13.4.4 Implicit Feedback

Aprende de señales implícitas del usuario:

```python
# Backend/core/learning/implicit_feedback.py

class ImplicitFeedbackCollector:
    """
    Recolecta feedback implícito de interacciones.
    """
    
    SIGNALS = {
        # Positivos
        'thumbs_up': +2.0,
        'confirmation_given': +1.5,
        'follow_up_similar': +1.0,
        'no_correction': +0.5,
        
        # Negativos
        'thumbs_down': -2.0,
        'immediate_retry': -1.5,
        'correction_given': -1.5,
        'cancellation': -1.0,
        'long_delay': -0.5  # >30s sin respuesta del usuario
    }
    
    def analyze_episode(self, episode: Episode) -> FeedbackResult:
        """
        Analiza un episodio completo extrayendo señales.
        """
        signals = []
        
        # Analizar interacción post-resultado
        if episode.user_followup:
            followup = episode.user_followup.lower()
            
            if any(word in followup for word in ['gracias', 'perfecto', 'excelente']):
                signals.append(('thumbs_up', self.SIGNALS['thumbs_up']))
            
            if any(word in followup for word in ['no', 'incorrecto', 'error', 'mal']):
                signals.append(('correction_given', self.SIGNALS['correction_given']))
            
            if 'reintent' in followup or 'otra vez' in followup:
                signals.append(('immediate_retry', self.SIGNALS['immediate_retry']))
        
        # Verificar tiempo de respuesta
        if episode.user_response_time and episode.user_response_time > 30:
            signals.append(('long_delay', self.SIGNALS['long_delay']))
        
        # Calcular score neto
        total_score = sum(score for _, score in signals)
        
        return FeedbackResult(
            signals=signals,
            net_score=total_score,
            should_reinforce=total_score >= REINFORCE_THRESHOLD,
            should_weaken=total_score <= WEAKEN_THRESHOLD
        )
```

### 13.4.5 Consolidación

Proceso periódico que aplica aprendizajes:

```python
# Backend/core/learning/consolidator.py

class LearningConsolidator:
    """
    Consolida aprendizajes periódicamente.
    Ejecuta cada 6 horas (configurable).
    """
    
    def run_consolidation(self):
        """
        Proceso principal de consolidación.
        """
        since = datetime.now() - timedelta(hours=CONSOLIDATION_LOOKBACK_HOURS)
        
        # 1. Recolectar feedback implícito
        episodes = self._load_episodes_since(since)
        feedback_results = [self.feedback_collector.analyze_episode(ep) for ep in episodes]
        
        # 2. Agrupar por plan/intent
        grouped = self._group_by_intent(episodes, feedback_results)
        
        for intent_key, group in grouped.items():
            net_score = sum(r.net_score for r in group['feedback'])
            
            # 3. Reforzar o debilitar
            if net_score >= REINFORCE_THRESHOLD:
                self._reinforce_pattern(group['episodes'])
                logger.info(f"✅ Patrón reforzado: {intent_key} (score: {net_score})")
                
            elif net_score <= WEAKEN_THRESHOLD:
                self._weaken_pattern(group['episodes'])
                logger.info(f"⚠️ Patrón debilitado: {intent_key} (score: {net_score})")
        
        # 4. Detectar nuevos patrones
        new_patterns = self.pattern_detector.detect_patterns()
        for pattern in new_patterns:
            if pattern.confidence > 0.7:
                self._suggest_new_pattern(pattern)
                
                if AUTO_APPLY_SUGGESTIONS and pattern.confidence > 0.9:
                    self._apply_pattern(pattern)
    
    def _reinforce_pattern(self, episodes: List[Episode]):
        """
        Refuerza un patrón aprendido en memoria procedural.
        """
        # Extraer plan típico
        typical_plan = self._extract_typical_plan(episodes)
        
        # Guardar en procedural memory con peso aumentado
        self.procedural_memory.add_learned_pattern(
            pattern_id=self._generate_id(),
            trigger=episodes[0].user_message,
            plan_template=typical_plan,
            success_rate=0.9,
            weight=min(1.0, len(episodes) / 10)
        )
```

### 13.4.6 Matching Learner

Aprende a hacer mejor matching de intents:

```python
# Backend/core/learning/matching_learner.py

class MatchingLearner:
    """
    Aprende de matches exitosos/fallidos para mejorar clasificación.
    """
    
    def __init__(self):
        self.successful_matches = []  # (input_pattern, matched_intent)
        self.failed_matches = []      # (input_pattern, wrong_intent, correct_intent)
    
    def record_match(
        self,
        input_text: str,
        matched_intent: str,
        success: bool,
        correct_intent: str = None
    ):
        """
        Registra resultado de un match para aprendizaje.
        """
        if success:
            self.successful_matches.append({
                "input": input_text,
                "intent": matched_intent,
                "timestamp": datetime.now()
            })
        else:
            self.failed_matches.append({
                "input": input_text,
                "predicted": matched_intent,
                "correct": correct_intent,
                "timestamp": datetime.now()
            })
    
    def suggest_improvements(self) -> List[Suggestion]:
        """
        Genera sugerencias para mejorar el matching.
        """
        suggestions = []
        
        # Analizar falsos positivos
        fp_patterns = self._analyze_false_positives()
        for pattern, count in fp_patterns.items():
            if count >= MATCHING_LEARNING_MIN_MATCHES:
                suggestions.append(Suggestion(
                    type="add_negative_pattern",
                    description=f"Añadir '{pattern}' como negativo para intent X",
                    priority=count / 10
                ))
        
        # Analizar falsos negativos
        fn_patterns = self._analyze_false_negatives()
        for pattern, intents in fn_patterns.items():
            if len(intents) >= MATCHING_LEARNING_MIN_MATCHES:
                suggestions.append(Suggestion(
                    type="expand_intent_pattern",
                    description=f"Expandir patrón de intent con: {pattern}",
                    priority=len(intents) / 10
                ))
        
        return suggestions
```

---

## 13.5 Integración con Planner

### Ciclo Completo

```python
# Backend/core/planner.py

class Planner:
    def plan(self, message: str, context: dict) -> Plan:
        """
        Planificación con metacognición y aprendizaje.
        """
        # 1. Buscar plan aprendido
        learned = self.procedural_memory.find_matching_pattern(message)
        if learned and learned.confidence > 0.75:
            plan = self._instantiate_learned_plan(learned, message)
            decision_source = "learned_plan"
        
        # 2. Detectar intent
        else:
            intent_result = self.detect_intent(message)
            plan = self._generate_plan_from_intent(intent_result)
            decision_source = intent_result.source
        
        # 3. Evaluar confianza (metacognición)
        confidence = self.confidence_evaluator.evaluate_plan(plan, context)
        
        # 4. Registrar decisión (auditoría)
        self.auditor.log_plan_decision(
            decision_type="plan_generated",
            decision_source=decision_source,
            input_data={"message": message},
            output_data=plan.to_dict(),
            reason=f"{decision_source}: {intent_result.matched if intent_result else 'learned'}",
            confidence=confidence.score
        )
        
        # 5. Solicitar confirmación si es necesario
        if confidence.requires_confirmation:
            return self._request_confirmation(plan, confidence)
        
        return plan
```

---

## 13.6 Referencias

| Módulo | Ubicación |
|--------|-----------|
| Confidence Evaluator | `Backend/core/metacognition/` |
| Decision Auditor | `Backend/core/auditor/decision_auditor.py` |
| Learning Engine | `Backend/core/learning/` |
| Config Metacognición | `Core/Config/metacognition.json` |
| Config Learning | `Core/Config/learning.json` |

---

*Documento 13 del índice - Metacognición y Learning*
