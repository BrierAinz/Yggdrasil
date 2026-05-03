# Misión 34: Sistema de Aprendizaje de Macros Custom v5.2

> **Versión objetivo**: Lilith v5.2
> **Feature**: Macro Learning & Custom Macros
> **Prioridad**: Alta (expand capabilities)
> **Esfuerzo estimado**: 12-16 horas
> **Dependencias**: v5.0-alpha deployado

---

## 🎯 Objetivo

Permitir que Lilith **aprenda nuevas macros automaticamente** desde patrones de uso repetidos, y que el usuario pueda **crear macros custom** mediante lenguaje natural o edicion directa de config.

**Estado actual**: 6 macros hardcoded en `pc_agent_macros.json`
**Estado deseado**: Sistema de aprendizaje que detecta patrones + API para crear macros custom

---

## 💡 Motivacion

### Problema Actual

```
Usuario ejecuta frecuentemente:
1. "crea carpeta logs"
2. "crea carpeta temp"
3. "copia config.json a logs"
4. "copia config.json a temp"

Sistema: NO aprende que esto es un patron repetido
```

**Issues**:
- Macros limitadas a las 6 predefinidas
- No hay forma de crear macros nuevas sin editar JSON
- Patrones de uso no se capitalizan
- Usuario repite mismas operaciones manualmente

### Solucion Propuesta

```
Sistema detecta patron (3+ ejecuciones similares):
→ "Detecte que ejecutas esto frecuentemente:
   'setup_logs_y_config' (4 veces esta semana)

   Quieres crear una macro para automatizarlo?"

[✅ Si, crear] [❌ No, gracias] [⚙️ Editar]

→ Usuario confirma
→ Macro "setup_logs_y_config" creada y disponible
→ Proxima vez: "setup logs y config" → ejecuta automaticamente
```

---

## 🏗️ Arquitectura

### Componentes Nuevos

#### 1. `MacroLearner`

**Ubicacion**: `Core/Backend/core/macro_learner.py`

```python
class MacroLearner:
    """
    Detecta patrones de uso y sugiere nuevas macros.

    Estrategias de deteccion:
    1. Temporal: Secuencias repetidas en ventana de tiempo
    2. Structural: Operaciones con estructura similar
    3. Frequency: Comandos ejecutados N+ veces
    """

    async def analyze_recent_history(
        self,
        user_id: str,
        window_hours: int = 168  # 1 semana
    ) -> List[MacroSuggestion]:
        """Analiza historial y sugiere macros"""

        # 1. Obtener historial de episodios
        episodes = await self.episodic_store.get_recent(
            user_id=user_id,
            hours=window_hours,
            tool_filter=['pc_operation', 'pc_operation_batch']
        )

        # 2. Extraer secuencias de operaciones
        sequences = self._extract_sequences(episodes)

        # 3. Detectar patrones
        patterns = self.pattern_detector.find_patterns(
            sequences,
            min_frequency=3,
            similarity_threshold=0.8
        )

        # 4. Generar sugerencias
        suggestions = []
        for pattern in patterns:
            template = self._pattern_to_macro_template(pattern)
            suggestion = MacroSuggestion(
                name=self._generate_macro_name(pattern),
                template=template,
                frequency=pattern.count,
                last_seen=pattern.last_timestamp,
                confidence=pattern.confidence
            )
            suggestions.append(suggestion)

        return suggestions
```

#### 2. `PatternDetector`

**Ubicacion**: `Core/Backend/core/pattern_detector.py`

```python
class PatternDetector:
    """
    Detecta patrones en secuencias de operaciones.

    Algoritmos:
    - Longest Common Subsequence (LCS)
    - Edit Distance (Levenshtein)
    - N-gram analysis
    """

    def find_patterns(
        self,
        sequences: List[List[Episode]],
        min_frequency: int = 3,
        similarity_threshold: float = 0.8
    ) -> List[Pattern]:
        """Encuentra patrones repetidos"""

        # Agrupar secuencias similares
        clusters = self._cluster_by_similarity(
            sequences,
            threshold=similarity_threshold
        )

        patterns = []
        for cluster in clusters:
            if len(cluster) >= min_frequency:
                common_pattern = self._extract_common_pattern(cluster)

                patterns.append(Pattern(
                    operations=common_pattern,
                    count=len(cluster),
                    confidence=self._calculate_confidence(cluster),
                    last_timestamp=max(seq[-1].timestamp for seq in cluster)
                ))

        return patterns
```

#### 3. `CustomMacroManager`

**Ubicacion**: `Core/Backend/core/custom_macro_manager.py`

```python
class CustomMacroManager:
    """
    Gestiona macros custom creadas por usuario o aprendidas.

    Features:
    - CRUD de macros custom
    - Validacion de templates
    - Merge con macros predefinidas
    - Versionado de macros
    """

    async def create_macro(
        self,
        name: str,
        description: str,
        operations: List[Dict],
        params: List[MacroParam],
        user_id: str,
        source: str = 'manual'  # 'manual', 'learned', 'suggested'
    ) -> Macro:
        """Crea nueva macro custom"""

        # Validar nombre unico
        if name in self.custom_macros or name in self.predefined_macros:
            raise ValueError(f"Macro '{name}' already exists")

        # Crear macro
        macro = Macro(
            name=name,
            description=description,
            operations=operations,
            params=params,
            created_by=user_id,
            created_at=datetime.now(),
            source=source,
            version=1
        )

        self.custom_macros[name] = macro
        await self._persist()

        return macro
```

#### 4. API Endpoints

**Ubicacion**: `Core/Backend/api/macro_api.py` (nuevo)

```python
@router.post("/macros/suggest")
async def suggest_macros(request: SuggestRequest):
    """Analiza historial y sugiere nuevas macros"""

@router.post("/macros/create")
async def create_macro(request: CreateMacroRequest):
    """Crea macro custom"""

@router.post("/macros/accept_suggestion")
async def accept_suggestion(request: AcceptSuggestionRequest):
    """Acepta sugerencia y crea macro"""

@router.get("/macros/list")
async def list_macros():
    """Lista todas las macros (predefinidas + custom)"""

@router.delete("/macros/{macro_name}")
async def delete_macro(macro_name: str, user_id: str):
    """Elimina macro custom"""
```

---

## 📋 Alcance (Scope)

### ✅ Fase 1: Deteccion de Patrones (v5.2.0)

1. **Pattern Detection**
   - Analisis de episodios recientes
   - Clustering de secuencias similares
   - Deteccion de frecuencia (3+ ejecuciones)

2. **Macro Suggestions**
   - Generacion de sugerencias desde patrones
   - Nombres automaticos inteligentes
   - Extraccion de parametros comunes
   - Confidence scoring

3. **API de Sugerencias**
   - `/macros/suggest` - Analizar y sugerir
   - `/macros/accept_suggestion` - Aceptar sugerencia
   - Notificacion proactiva cuando detecta patron

### ✅ Fase 2: Custom Macros (v5.2.0)

1. **CRUD Completo**
   - Create, Read, Update, Delete macros
   - Validacion de templates
   - Versionado de macros

2. **Macro Editor**
   - Crear macro desde lenguaje natural
   - Editar macro existente
   - Preview antes de guardar

3. **Persistencia**
   - `Core/Data/custom_macros.json`
   - Merge con predefinidas en runtime
   - Backup automatico

### ❌ NO Incluido (v5.3+)

- Editor visual de macros (drag & drop)
- Macros condicionales (if/else)
- Macros con loops
- Sharing de macros entre usuarios
- Macro marketplace

---

## 🎯 Criterios de Éxito

### Tests Unitarios (15 nuevos)

```python
# Core/Tests/test_macro_learner.py (8 tests)
def test_extract_sequences()
def test_pattern_detection()
def test_clustering_similar_sequences()
def test_confidence_scoring()

# Core/Tests/test_custom_macro_manager.py (7 tests)
def test_create_macro()
def test_validate_operations()
def test_unique_name_constraint()
def test_merge_with_predefined()
```

### Smoke Tests (4 criticos)

1. **Deteccion de patron**
   ```
   Ejecutar 3 veces: "crea carpeta logs", "copia config.json a logs"
   → Sistema detecta patron
   → Sugiere macro "setup_logs"
   ```

2. **Crear macro custom**
   ```
   POST /macros/create → Macro creada → Aparece en /macros/list
   ```

3. **Aceptar sugerencia**
   ```
   POST /macros/accept_suggestion → Macro creada desde sugerencia
   ```

4. **Ejecutar macro custom**
   ```
   Telegram: "ejecuta mi_macro con proyecto=Test" → Resultado OK
   ```

---

## 📦 Archivos a Crear/Modificar

### Nuevos (8 archivos)
```
Core/Backend/
├── core/
│   ├── macro_learner.py              # Pattern detection
│   ├── pattern_detector.py           # Clustering & analysis
│   ├── custom_macro_manager.py       # CRUD macros custom
│   └── macro_templates.py            # Template library
├── api/
│   └── macro_api.py                  # REST API
└── Tests/
    ├── test_macro_learner.py         # 8 tests
    └── test_custom_macro_manager.py  # 7 tests

Core/Data/
└── custom_macros.json                # Storage custom macros
```

### Modificados (3 archivos)
```
Core/Backend/
├── core/
│   └── pc_macro_engine.py            # +merge custom macros
└── api/
    └── telegram_api.py               # +macro suggestions

Core/Config/
└── macro_learning.json               # Config (nuevo)
```

---

## ⚙️ Configuracion

```json
{
  "pattern_detection": {
    "enabled": true,
    "window_hours": 168,
    "min_frequency": 3,
    "similarity_threshold": 0.8,
    "confidence_threshold": 0.7
  },
  "auto_suggest": {
    "enabled": true,
    "notify_user": true,
    "min_confidence": 0.8
  },
  "custom_macros": {
    "max_per_user": 50,
    "allow_delete": true,
    "require_approval": false
  }
}
```

---

## 🚀 Plan de Implementacion

| Fase | Tiempo | Tareas |
|------|--------|--------|
| Fase 1 | 6-8h | Pattern Detection, clustering, LCS, tests (8) |
| Fase 2 | 4-5h | Custom Macro Manager, CRUD, validation, tests (7) |
| Fase 3 | 2-3h | API, integracion Telegram, smoke tests (4) |

**Total**: 12-16 horas

---

## 📊 Impacto

### Positivo
- ✅ Sistema aprende desde uso
- ✅ Usuario crea macros sin editar JSON
- ✅ Capitaliza patrones de uso
- ✅ Reduce trabajo repetitivo

### Riesgos
- ⚠️ False positives en deteccion (mitigado: confidence threshold)
- ⚠️ Storage de custom macros (mitigado: max 50 por user)
- ⚠️ Complejidad en clustering (mitigado: DBSCAN probado)

---

## 🎯 Metricas de Éxito

| Metrica | Objetivo |
|---------|----------|
| Tests pasando | 15/15 (100%) |
| Smoke tests | 4/4 pasando |
| Pattern detection accuracy | >80% |
| Macro suggestions accepted | >50% |
| User-created custom macros | >10 en primer mes |

---

*Mision creada: 2026-03-26*
*Estado: 📋 Disenada, pendiente de implementacion*
*Prioridad: Alta (capability expansion)*
