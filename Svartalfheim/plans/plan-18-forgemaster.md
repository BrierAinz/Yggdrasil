# ForgeMaster — Gestión de Recursos de Niflheim

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** CLI que gestiona los recursos de Niflheim: modelos LLM, datasets, checkpoints, VRAM monitoring, disk usage. Sabe qué modelos tienes, cuánto espacio ocupan, y cuánta VRAM necesitas para correrlos.

**Architecture:** Scanner de directorios → metadata extraction → SQLite catalog → optimization suggestions → Rich CLI. Integrado con ComfyUI (modelos de imagen) y LM Studio/KoboldCpp (modelos de texto).

**Tech Stack:** Python 3.11+, Typer, Rich, SQLite, psutil, httpx, safetensors (para metadata).

**Realm:** Niflheim/ForgeMaster/

---

## Task 1: Scaffold del proyecto

Files: `Niflheim/ForgeMaster/`, pyproject.toml con typer, rich, psutil, httpx, safetensors, pyyaml.

**Commit:** `feat(forgemaster): scaffold project`

---

## Task 2: Model scanner y catalog

Escanea directorios de modelos y extrae metadata:
- LM Studio models: `~/.cache/lm-studio/models/`
- ComfyUI models: `~/comfy/ComfyUI/models/`
- HuggingFace cache: `~/.cache/huggingface/`

```python
@dataclass
class ModelInfo:
    name: str
    path: str
    size_bytes: int
    format: str  # gguf, safetensors, pt, onnx
    architecture: str  # llama, stable-diffusion, whisper...
    parameters: str | None  # "7B", "13B", "70B"
    context_length: int | None
    quantization: str | None  # Q4_K_M, Q5_K_M, FP16...
    vram_required_gb: float | None
    download_date: date | None
    source: str  # lm_studio, huggingface, manual

class ModelScanner:
    def scan(self, paths: list[str]) -> list[ModelInfo]:
        """Scan directories for model files."""
        ...

    def extract_metadata(self, model_path: str) -> ModelInfo:
        """Extract metadata from model file/directory."""
        ...
```

**Commit:** `feat(forgemaster): model scanner and catalog`

---

## Task 3: SQLite catalog

```sql
CREATE TABLE models (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,
    size_bytes INTEGER NOT NULL,
    format TEXT,
    architecture TEXT,
    parameters TEXT,
    context_length INTEGER,
    quantization TEXT,
    vram_required_gb REAL,
    download_date DATE,
    source TEXT,
    tags TEXT,  -- JSON array
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE gpu_profiles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,  -- "RTX 3060 12GB"
    vram_total_gb REAL NOT NULL,
    vram_available_gb REAL  -- after system allocation
);
```

**Commit:** `feat(forgemaster): SQLite catalog`

---

## Task 4: VRAM calculator

Calcula VRAM necesaria para un modelo:
- GGUF: overhead por quantization level
- Safetensors: tamaño del tensor × precision
- KV cache: context_length × batch_size × precision
- ComfyUI: estimación para SDXL, Flux, etc.

```python
class VRAMCalculator:
    def calculate(self, model: ModelInfo, context_length: int = 4096, batch_size: int = 1) -> VRAMEstimate:
        """Calculate VRAM needed to run a model."""
        ...

    def can_run(self, model: ModelInfo, gpu: GPUProfile) -> bool:
        """Check if model fits in GPU VRAM."""
        ...

    def suggest_offload(self, model: ModelInfo, gpu: GPUProfile) -> OffloadStrategy:
        """Suggest GPU/CPU offload strategy if model doesn't fit."""
        ...
```

**Commit:** `feat(forgemaster): VRAM calculator`

---

## Task 5: Disk usage y cleanup

```bash
forgemaster scan                     # scanar modelos
forgemaster list                     # listar todos los modelos
forgemaster list --type llm          # solo LLMs
forgemaster list --type diffusion    # solo modelos de imagen
forgemaster stats                    # disk usage, count by type
forgemaster duplicates              # encontrar modelos duplicados/parecidos
forgemaster cleanup                  # sugerir modelos para eliminar
forgemaster check llama-7b-q5        # ¿puedo correr este modelo?
```

**Commit:** `feat(forgemaster): disk usage and cleanup suggestions`

---

## Task 6: GPU monitoring

Integración con nvidia-smi para RTX 3060:
- VRAM usage actual
- Running processes en GPU
- Temperature
- Disponibilidad para correr nuevos modelos

```python
class GPUMonitor:
    def status(self) -> GPUStatus:
        """Current GPU status."""
        ...

    def available_vram(self) -> float:
        """Available VRAM in GB."""
        ...
```

**Commit:** `feat(forgemaster): GPU monitoring (nvidia-smi)`

---

## Task 7: Model download helper

Ayuda a descargar modelos de HuggingFace:
```bash
forgemaster download "TheBloke/Llama-2-7B-GGUF" --quant Q5_K_M
forgemaster download "stabilityai/stable-diffusion-xl-base-1.0"
forgemaster recommend --vram 12 --type llm   # recomienda modelos para tu GPU
```

**Commit:** `feat(forgemaster): model download helper`

---

## Task 8: Rich CLI con tablas coloreadas

Rich output para todas las operaciones:
- Tabla de modelos con colores por formato
- Barra de VRAM con uso/disponible
- Disk usage pie chart (ASCII)
- Warning si modelo excede VRAM

**Commit:** `feat(forgemaster): Rich CLI with colored output`

---

## Task 9: Tests + CI

**Commit:** `ci(forgemaster): add test workflow`
