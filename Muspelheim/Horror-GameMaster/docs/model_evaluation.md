# Horror GameMaster — Evaluacion de Modelos para Fine-Tuning

> Evaluado: 2026-05-27
> Target GPU: RTX 3060 12GB VRAM
> Objetivo: Narrativa de terror procedural de alta calidad

---

## Modelos Evaluados

### Tier 1 — Recomendados

| Modelo | Params | VRAM (QLoRA) | Licencia | Narrativa | Notas |
|--------|--------|-------------|----------|-----------|-------|
| **Qwen2.5-7B-Instruct** | 7B | ~6GB | Apache 2.0 | Excelente | Mejor ratio calidad/recursos. Bueno para narrativa creativa. |
| **Mistral-Nemo-12B** | 12B | ~8GB | Apache 2.0 | Excelente | Contexto 128K. Cabe en 12GB con QLoRA 4-bit. |
| **Phi-4 (14B)** | 14B | ~9GB | MIT | Muy bueno | Sorprendente calidad para su tamano. |

### Tier 2 — Viables

| Modelo | Params | VRAM (QLoRA) | Licencia | Narrativa | Notas |
|--------|--------|-------------|----------|-----------|-------|
| Dolphin-Mistral-7B | 7B | ~6GB | Apache 2.0 | Bueno | Sin refusal, util para contenido horror. |
| Llama-3.1-8B-Instruct | 8B | ~6GB | Llama 3.1 | Bueno | Meta ecosystem, bien documentado. |
| Qwen2.5-Coder-7B | 7B | ~6GB | Apache 2.0 | Regular | Mejor para codigo que narrativa. |

### Tier 3 — No Recomendados (limitaciones de VRAM)

| Modelo | Params | VRAM | Razon |
|--------|--------|------|-------|
| Llama-3.1-70B | 70B | >40GB | Excede VRAM incluso con QLoRA |
| Qwen2.5-72B | 72B | >40GB | Idem |
| Mistral-Large | 123B | >48GB | Idem |

---

## Frameworks de Fine-Tuning

### Unsloth (RECOMENDADO)

- **Velocidad**: 2x mas rapido que HF Trainer
- **Memoria**: 60% menos VRAM
- **Soporte**: QLoRA 4-bit y 2-bit
- **Limitacion**: Solo Linux, requiere CUDA
- **Instalacion**: `pip install unsloth`
- **Ideal para**: RTX 3060 con 12GB

```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
    max_seq_length=4096,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj","k_proj","v_proj","o_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
)
```

### HuggingFace TRL + PEFT

- **Velocidad**: Estandar
- **Memoria**: Requiere mas VRAM que Unsloth
- **Flexibilidad**: Maxima, ecosistema HF completo
- **Ideal para**: Cuando necesitas control fino del entrenamiento

### Axolotl

- **Velocidad**: Buena
- **Memoria**: Similar a TRL
- **Config**: YAML-based, facil de versionar
- **Ideal para**: Pipelines automatizados

### LM Studio

- **Velocidad**: Estandar
- **Memoria**: Similar a TRL
- **UI**: Grafica, facil para principiantes
- **Limitacion**: Menos control programatico
- **Ideal para**: Experimentacion rapida, no para produccion

---

## Recomendacion Final

**Primera opcion**: Qwen2.5-7B-Instruct + Unsloth

- Cabe comodamente en RTX 3060 (6GB entrenamiento, 4GB inferencia)
- Apache 2.0 — sin restricciones de licencia
- Excelente capacidad narrativa demostrada
- Fine-tuning en ~2 horas para 1000 ejemplos con Unsloth
- Despliegue via Ollama para inferencia local

**Segunda opcion**: Mistral-Nemo-12B + Unsloth

- Si necesitas mas capacidad y puedes ajustar hyperparametros
- 128K contexto es ideal para sesiones largas de juego
- Requiere QLoRA agresivo (4-bit, r=8) para caber en 12GB

---

## Pipeline de Fine-Tuning Propuesto

```
1. Preparar dataset (JSONL) → formato Alpaca/ShareGPT
2. Cargar modelo con Unsloth (4-bit quantized)
3. Configurar LoRA (r=16, alpha=16, dropout=0)
4. Entrenar (3 epochs, lr=2e-4, batch_size=2)
5. Evaluar (generar samples de terror, revisar calidad)
6. Exportar a GGUF (para Ollama)
7. Crear Modelfile para Ollama
8. Testear en loop con el GameMaster
```

---

## Referencias

- [Unsloth Docs](https://github.com/unslothai/unsloth)
- [Qwen2.5 Technical Report](https://arxiv.org/abs/2412.15115)
- [HuggingFace PEFT](https://huggingface.co/docs/peft)
- [Ollama Modelfile](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
