#!/usr/bin/env python3
"""Auto-caption Ehyra dataset for Z-Image LoRA training using Qwen3-VL-4B-Instruct."""

import gc
import glob
import os

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration


# --- Config ---
INPUT_DIR = os.path.expanduser("~/comfy/ai-toolkit/dataset/images/ehyra_dataset")
TRIGGER_WORD = "ehyra"  # MUST match LoRA training trigger word
QUANTIZE = True          # 4-bit quantization for 12GB VRAM
MAX_NEW_TOKENS = 200    # Detailed captions for Z-Image

# --- Load Model ---
print("[INFO] Loading Qwen3-VL-4B-Instruct...")
model_kwargs = {
    "torch_dtype": "auto",
    "device_map": "auto",
}
if QUANTIZE:
    from transformers import BitsAndBytesConfig
    model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)

model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    **model_kwargs,
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")
print("[INFO] Model loaded successfully.")

# --- Gather Images ---
extensions = ("*.jpg", "*.jpeg", "*.png")
image_paths = []
for ext in extensions:
    image_paths.extend(glob.glob(os.path.join(INPUT_DIR, ext)))
image_paths.sort()
print(f"[INFO] Found {len(image_paths)} images in {INPUT_DIR}")

# --- Caption Loop ---
captioned = 0
skipped = 0
errors = 0

for i, img_path in enumerate(image_paths):
    txt_path = os.path.splitext(img_path)[0] + ".txt"

    # Resume: skip already-captioned images
    if os.path.exists(txt_path):
        print(f"[SKIP] ({i+1}/{len(image_paths)}) {os.path.basename(txt_path)} already exists")
        skipped += 1
        continue

    try:
        image = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"[ERROR] Cannot open {img_path}: {e}")
        errors += 1
        continue

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": img_path,  # plain path, NOT file:// URI
                },
                {
                    "type": "text",
                    "text": (
                        "Describe this anime/manga character illustration in detail "
                        "for a training dataset. Include: hair color and style, eye color, "
                        "skin tone, clothing details, pose, expression, background/setting, "
                        "lighting, art style, and any distinctive features. "
                        "Write a natural descriptive caption, not a list."
                    ),
                },
            ],
        }
    ]

    text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(
        text=[text_prompt],
        images=[image],
        return_tensors="pt",
    ).to(model.device)

    output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
    # IMPORTANT: use batch_decode(), NOT batch_text_decoder (removed in newer transformers)
    caption = processor.batch_decode(
        output_ids[:, inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )[0].strip()

    # Write caption with trigger word prefix
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{TRIGGER_WORD} {caption}")

    captioned += 1
    print(f"[OK] ({i+1}/{len(image_paths)}) {os.path.basename(txt_path)}: {TRIGGER_WORD} {caption[:80]}...")

# --- Cleanup ---
del model
del processor
gc.collect()
torch.cuda.empty_cache()

print(f"\n[DONE] Captioned: {captioned}, Skipped: {skipped}, Errors: {errors}")
print("[INFO] GPU memory freed. Safe to launch training.")
