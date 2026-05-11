---
name: auto-captioning
description: Generic image captioning using Qwen3-VL for LoRA training datasets. Batch-process images, generate trigger-word-prefixed captions, resume-safe, VRAM-aware.
version: 1.0.0
tags: [captioning, qwen3-vl, lora, dataset, image, vlm]
related_skills:
  - lora-training-pipeline
---

# Auto-Captioning with Qwen3-VL

Generate descriptive captions for LoRA training images using Qwen3-VL-4B-Instruct. Output `.txt` files alongside each image, prefixed with a trigger word matching your LoRA config.

## Setup

```bash
pip install transformers accelerate torch pillow qwen-vl-utils
```

**PITFALL**: The `qwen-vl-utils` package is required by Qwen3-VL for image preprocessing. Without it, model loading may fail with an import error. Install it even if `transformers` is already present.

The model `Qwen/Qwen3-VL-4B-Instruct` auto-downloads from HuggingFace Hub on first run. No manual download needed. Ensure you have ~8GB VRAM available (quantized) and adequate disk space for the model weights.

## Directory Structure

```
input_dir/
├── image001.jpg
├── image001.txt      ← generated caption
├── image002.png
├── image002.txt      ← generated caption
├── image003.jpeg      ← no .txt yet = will be captioned
└── ...
```

- **Input**: A directory of images (`.jpg`, `.jpeg`, `.png`).
- **Output**: One `.txt` file per image, same basename, same directory.
- **Resume**: Skip any image that already has a companion `.txt` file.

## Caption Format

Each caption `.txt` file contains a single line:

```
<trigger_word> <descriptive caption>
```

- `<trigger_word>` must match the trigger word used in your LoRA training config (e.g. `shsdog`, `xyzperson`).
- Example output: `shsdog a golden retriever sitting on a wooden deck in afternoon sunlight`

## Script Pattern

```python
import os
import glob
from PIL import Image
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

# --- Config ---
input_dir = "/path/to/images"
trigger_word = "shsdog"  # MUST match your LoRA training trigger word
quantize = True           # Use quantization for lower VRAM
low_vram = True

# --- Load Model ---
model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    torch_dtype="auto",
    device_map="auto",
    **({"quantization_config": {"load_in_4bit": True}} if quantize else {}),
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")

# --- Gather Images ---
extensions = ("*.jpg", "*.jpeg", "*.png")
image_paths = []
for ext in extensions:
    image_paths.extend(glob.glob(os.path.join(input_dir, ext)))

# --- Caption Loop ---
for img_path in image_paths:
    txt_path = os.path.splitext(img_path)[0] + ".txt"

    # Resume: skip already-captioned images
    if os.path.exists(txt_path):
        print(f"[SKIP] {txt_path} already exists")
        continue

    try:
        image = Image.open(img_path).convert("RGB")
    except Exception as e:
        print(f"[ERROR] Cannot open {img_path}: {e}")
        continue

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": img_path},  # plain path, NOT file:// URI
                {"type": "text", "text": "Describe this image in detail for a training dataset. Be specific about subject, pose, setting, lighting, and style."},
            ],
        }
    ]

    text_prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(
        text=[text_prompt],
        images=[image],
        return_tensors="pt",
    ).to(model.device)

    output_ids = model.generate(**inputs, max_new_tokens=128)
    # IMPORTANT: use batch_decode(), NOT batch_text_decoder (removed in newer transformers)
    caption = processor.batch_decode(output_ids[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0].strip()

    with open(txt_path, "w") as f:
        f.write(f"{trigger_word} {caption}")

    print(f"[OK] {txt_path}: {trigger_word} {caption}")

# --- Cleanup ---
del model
del processor
import gc, torch
gc.collect()
torch.cuda.empty_cache()
print("GPU memory freed. Safe to launch ComfyUI or other GPU tasks.")
```

## Batch Processing

- Processes all images in a directory; no batch-size limit beyond iteration speed.
- Resume is automatic: any image with an existing `.txt` file is skipped.
- For very large datasets (thousands of images), consider processing in subdirectory batches.
- Log progress to `caption_log.txt` if you want a persistent record:

```python
import logging
logging.basicConfig(filename=os.path.join(input_dir, "caption_log.txt"), level=logging.INFO)
```

## VRAM Management

| Config | Approx. VRAM |
|--------|-------------|
| Qwen3-VL-4B + 4-bit quant | ~8 GB |
| Qwen3-VL-4B + FP16 (no quant) | ~16 GB |

**Critical constraints:**

- On a **12 GB GPU**, you CANNOT run Qwen3-VL alongside ComfyUI. Kill ComfyUI first:

```bash
# Check what's using GPU
nvidia-smi
# Kill ComfyUI process
pkill -f comfyui || taskkill /F /IM python.exe  # Windows host
```

- After captioning completes, the script frees GPU memory. Only then is it safe to relaunch ComfyUI.
- If you get OOM errors, ensure no other GPU processes are running (`nvidia-smi`).

## Post-Captioning Cleanup (CRITICAL)

Qwen3-VL frequently injects **refusal prefixes** and **meta-commentary** into captions, especially for anime/illustration images where it tries to "correct" the style description. These poison training data if not removed. Detected patterns in real usage (affected ~25% of captions):

### Refusal patterns (replace everything before the actual description):
- `"Actually, this image is not an anime or manga character illustration — it's a real-life photograph of..."`
- `"Actually, this is not an anime or manga character illustration — it's a real-life photograph of..."`
- `"Actually, this isn't an anime or manga character illustration — it's a real-life selfie of..."`

**Fix**: Strip the entire refusal prefix, keeping only the description after `"it's a/an "`. Capitalize the first letter. Result: `"ehyra Real-life photograph of..."` → acceptable training caption.

### Meta-commentary patterns (strip entire first line, keep description):
- `"Here's a detailed description of this image, crafted for a training dataset:\n\n<actual description>"`
- `"Here's a detailed description of the character in this image, crafted for a training dataset:\n\n<actual description>"`
- `"Here's a detailed description of the image for a training dataset:\n\n<actual description>"`

**Fix**: Remove first line entirely, join remaining lines as the caption.

### Cleanup script pattern:
```python
import os, glob, re

os.chdir('/path/to/images')
trigger_word = "ehyra"  # MUST match your training trigger word

for f in sorted(glob.glob('*.txt')):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read().strip()
    original = content

    # Remove refusal prefix — uses Unicode em-dash (U+2014) and smart apostrophe (U+2019)
    # PITFALL: Python source files may mangle smart quotes. Use the actual Unicode escapes.
    pattern = r"^" + re.escape(trigger_word) + r" Actually, this (?:image )?(?:is not|isn\u2019t) an anime or manga character illustration \u2014 it\u2019s (?:a |an )"
    content = re.sub(pattern, trigger_word + " ", content, flags=re.IGNORECASE)

    # Remove meta-commentary first line (uses ASCII apostrophe)
    if any(x in content for x in ["Here's a detailed", "crafted for a training dataset"]):
        lines = content.split('\n')
        real_lines = [l for l in lines if "Here's" not in l and "crafted for" not in l]
        content = ' '.join(real_lines).strip()

    # Capitalize first letter after trigger word
    if content.startswith(trigger_word + ' ') and content[len(trigger_word)+1].islower():
        content = trigger_word + ' ' + content[len(trigger_word)+1].upper() + content[len(trigger_word)+2:]

    if content != original:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(content + '\n')
```

**PITFALL — Smart quotes in refusal prefixes**: Qwen3-VL uses Unicode characters for punctuation in refusal prefixes: em-dash `—` (U+2014) and smart apostrophe `'` (U+2019). A simple string replace with ASCII `'` or `-` will NOT match. Use Unicode escapes (`\u2014`, `\u2019`) in regex patterns, or use `unidecode`/`.replace()` to normalize the text to ASCII first. Shell heredocs and Python string literals can silently mangle these characters — always write them as `\u2014` and `\u2019` to avoid encoding issues.

**IMPORTANT**: Always verify captions after running Qwen3-VL. Run `grep -rl "Actually" *.txt` and `grep -rl "Here's" *.txt` to find contaminated files. The cleanup MUST run before training begins or your LoRA will learn refusal language.

## Pitfalls

1. **Qwen3-VL refusal/meta-commentary in captions**: Qwen3-VL frequently injects refusal prefixes ("Actually, this is not an anime...") and meta-commentary ("Here's a detailed description... crafted for a training dataset") into captions. These are EXTREMELY harmful to LoRA training. Always run post-captioning cleanup. See "Post-Captioning Cleanup" section above.

2. **`batch_decode` vs `batch_text_decoder`**: Always use `processor.batch_decode()`. The `batch_text_decoder` method was removed in newer transformers versions and will raise `AttributeError`.

3. **Image paths**: Use plain filesystem paths (`/path/to/image.jpg`), **NOT** `file:///path/to/image.jpg` URIs. The processor rejects `file://` prefixes for local images.

4. **PIL Image.open()**: Always open local files with `PIL.Image.open()`. Do **not** pass image paths directly to the model — you must pass a PIL Image object to the processor.

5. **Skip non-image files**: Your input directory may contain `.txt`, `.json`, sidecar files, etc. Filter by `.jpg/.jpeg/.png` extensions only.

6. **Corrupted images**: Wrap `Image.open()` in `try/except`. Corrupted or zero-byte files will raise `UnidentifiedImageError` or similar. Log and skip.

7. **Trigger word consistency**: The trigger word in captions MUST exactly match the trigger word in your LoRA training config (e.g., in Kohya SS or similar trainers). A mismatch means your LoRA won't activate properly.

8. **GPU memory after completion**: The cleanup block (`del model; torch.cuda.empty_cache()`) is essential. Without it, GPU memory stays reserved even after the script exits, blocking ComfyUI from starting.

9. **`skip_special_tokens=True`**: Always pass this to `batch_decode()` to strip `<|im_end|>` and other model tokens from the output.

## Verification

After running, verify your captions:

```bash
# Count captioned vs uncaptioned
echo "Captioned: $(find /path/to/images -name '*.txt' | wc -l)"
echo "Total images: $(find /path/to/images \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) | wc -l)"

# Spot-check a few captions
head -5 /path/to/images/*.txt

# Ensure all captions start with the trigger word
grep -L "^shsdog " /path/to/images/*.txt  # should return nothing
```