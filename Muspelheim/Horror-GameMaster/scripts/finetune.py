#!/usr/bin/env python3
"""
Horror GameMaster — QLoRA Fine-tuning with Unsloth
Model: Qwen2.5-7B-Instruct (4-bit quantized)
GPU: RTX 3060 12GB
"""

import json

import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel


# ═══════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LEN = 2048
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
BATCH_SIZE = 2
GRAD_ACCUM = 4  # effective batch = 8
LEARNING_RATE = 2e-4
EPOCHS = 3
OUTPUT_DIR = "./lora-horror-gamemaster"
DATASET_PATH = "data/dataset_unified.jsonl"

# ═══════════════════════════════════════════
#  SYSTEM PROMPT
# ═══════════════════════════════════════════
SYSTEM_PROMPT = """You are the Horror GameMaster — a procedural terror engine that generates psychological horror narratives.

Your role:
- Analyze the player's fear profile and adapt your narrative accordingly
- Generate atmospheric, immersive horror descriptions
- Create tension through psychological dread, not cheap jumpscares
- Maintain narrative consistency across the session
- Use the player's fear_type to craft personalized horror

Fear types you specialize in:
- darkness: fear of the unknown in shadows, sensory deprivation
- isolation: being alone, cut off, forgotten
- jumpscare: sudden shocking moments (use sparingly)
- psychological: guilt, trauma, existential dread, manipulation
- paranoia: being watched, followed, betrayed
- body_horror: physical transformation, violation of the body
- loss_of_control: losing agency, being puppeteered
- false_security: safety that betrays, trust that traps

Always respond in second person ("you") for immersion. Be visceral but literate."""

# ═══════════════════════════════════════════
#  LOAD MODEL
# ═══════════════════════════════════════════
print(f"Loading {MODEL_NAME} with 4-bit quantization...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,  # auto-detect
    load_in_4bit=True,
)

print(f"Applying LoRA (r={LORA_R}, alpha={LORA_ALPHA})...")
model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_R,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ═══════════════════════════════════════════
#  LOAD & FORMAT DATASET
# ═══════════════════════════════════════════
print(f"Loading dataset from {DATASET_PATH}...")
entries = []
with open(DATASET_PATH) as f:
    for line in f:
        if line.strip():
            entries.append(json.loads(line))

print(f"  {len(entries)} entries loaded")


def format_entry(entry):
    """Format as Qwen2.5 chat template."""
    instruction = entry.get("instruction", "")
    inp = entry.get("input", "")
    output = entry.get("output", "")
    fear_type = entry.get("fear_type", "psychological")

    # Build the user message with context
    user_msg = f"[Fear Type: {fear_type}]\n{instruction}"
    if inp:
        user_msg += f"\n\nContext: {inp}"

    return {
        "conversations": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": output},
        ]
    }


formatted = [format_entry(e) for e in entries]
dataset = Dataset.from_list(formatted)


def apply_chat_template(example):
    text = tokenizer.apply_chat_template(
        example["conversations"],
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


dataset = dataset.map(apply_chat_template, remove_columns=["conversations"])
print(f"  Formatted dataset: {len(dataset)} examples")
print(f"  Sample length: {len(dataset[0]['text'])} chars")

# ═══════════════════════════════════════════
#  TRAINER
# ═══════════════════════════════════════════
print("Setting up trainer...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    dataset_num_proc=4,
    packing=True,
    args=TrainingArguments(
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_steps=50,
        num_train_epochs=EPOCHS,
        learning_rate=LEARNING_RATE,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=42,
        output_dir=OUTPUT_DIR,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=3,
        report_to="none",
    ),
)

# ═══════════════════════════════════════════
#  TRAIN
# ═══════════════════════════════════════════
print(
    f"\nStarting training: {EPOCHS} epochs, batch={BATCH_SIZE}x{GRAD_ACCUM}={BATCH_SIZE * GRAD_ACCUM}"
)
print(f"  LoRA rank: {LORA_R}, alpha: {LORA_ALPHA}")
print(f"  LR: {LEARNING_RATE}, max_seq_len: {MAX_SEQ_LEN}")
print()

gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1e9
print(f"  GPU: {torch.cuda.get_device_name(0)} ({gpu_mem:.1f} GB)")
print()

stats = trainer.train()
print("\nTraining complete!")
print(f"  Total steps: {stats.global_step}")
print(f"  Training loss: {stats.training_loss:.4f}")

# ═══════════════════════════════════════════
#  SAVE
# ═══════════════════════════════════════════
print(f"\nSaving LoRA adapters to {OUTPUT_DIR}/final...")
model.save_pretrained(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

# Also save merged 16-bit for easy inference
print("Saving merged 16-bit model...")
model.save_pretrained_merged(
    f"{OUTPUT_DIR}/merged-16bit",
    tokenizer,
    save_method="merged_16bit",
)

print(f"\nDone! Files in {OUTPUT_DIR}/")
print("  final/        — LoRA adapters (small, for loading on top of base)")
print("  merged-16bit/ — Full merged model (ready for inference)")
