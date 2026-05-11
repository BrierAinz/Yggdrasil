# ComfyUI API LoRA Testing Workflow

Submit LoRA test images via ComfyUI's REST API to systematically evaluate
checkpoints at different strengths and prompts.

## Prerequisites

- ComfyUI running on `http://localhost:8188`
- LoRA files copied to `ComfyUI/models/loras/`
- Checkpoint file in `ComfyUI/models/checkpoints/`

## Node Graph Structure

```
4: CheckpointLoaderSimple  →  10: LoraLoader
                              ↓
10: LoraLoader             →  6: CLIPTextEncode (positive)
10: LoraLoader             →  7: CLIPTextEncode (negative)
5:  EmptyLatentImage       →  3: KSampler
3:  KSampler               →  8: VAEDecode
8:  VAEDecode              →  9: SaveImage
```

## Complete Workflow JSON

```python
import json
import urllib.request
import time

def submit_lora_test(lora_name, lora_strength, positive_prompt,
                     negative_prompt, filename_prefix, seed=42,
                     steps=25, cfg=7, width=1024, height=1024,
                     checkpoint="ponyDiffusionV6XL_v6StartWithThisOne.safetensors"):
    """Submit a LoRA test image to ComfyUI via API."""

    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_prompt, "clip": ["10", 1]}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["10", 1]}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["8", 0]}
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["4", 0],
                "clip": ["4", 1]
            }
        }
    }

    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8188/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read())
```

## Test Matrix Pattern

Test 3 dimensions: checkpoint × strength × outfit.

```python
PONY_NEGATIVE = "score_6, score_5, score_4, source_anime, bad anatomy, extra fingers, blurry, watermark, text, deformed hands, extra limbs, low quality, worst quality"

tests = [
    # Different checkpoints at strength 0.8
    {"lora": "lora_step1000.safetensors", "strength": 0.8, "seed": 42,
     "prefix": "test_step1000_s08",
     "prompt": "score_9, score_8_up, TRIGGER, description, outfit_1, scene, photorealistic"},

    # Final checkpoint at multiple strengths
    {"lora": "lora_final.safetensors", "strength": 0.7, "seed": 55,
     "prefix": "test_final_s07",
     "prompt": "score_9, score_8_up, TRIGGER, description, outfit_2, scene, photorealistic"},

    {"lora": "lora_final.safetensors", "strength": 0.9, "seed": 77,
     "prefix": "test_final_s09",
     "prompt": "score_9, score_8_up, TRIGGER, description, outfit_3, scene, photorealistic"},

    {"lora": "lora_final.safetensors", "strength": 1.0, "seed": 88,
     "prefix": "test_final_s10",
     "prompt": "score_9, score_8_up, TRIGGER, description, outfit_4, scene, photorealistic"},

    # Strength 0.95 — fine-grained sweet spot
    {"lora": "lora_final.safetensors", "strength": 0.95, "seed": 33,
     "prefix": "test_final_s095",
     "prompt": "score_9, score_8_up, TRIGGER, description, outfit_5, scene, photorealistic"},
]

for i, t in enumerate(tests):
    result = submit_lora_test(
        lora_name=t["lora"],
        lora_strength=t["strength"],
        positive_prompt=t["prompt"],
        negative_prompt=PONY_NEGATIVE,
        filename_prefix=t["prefix"],
        seed=t["seed"]
    )
    print(f"[{i+1}] {t['prefix']}: {result.get('prompt_id', '?')}")
    time.sleep(0.5)  # Space out submissions
```

## Polling for Completion

```python
import time, os

output_dir = "/path/to/ComfyUI/output"
expected_count = len(tests)
max_wait = 300  # 5 minutes

while time.time() - start < max_wait:
    resp = urllib.request.urlopen("http://localhost:8188/queue")
    queue = json.loads(resp.read())
    running = len(queue.get("queue_running", []))
    pending = len(queue.get("queue_pending", []))
    
    test_files = [f for f in os.listdir(output_dir) if f.startswith("test_") and f.endswith(".png")]
    
    if running == 0 and pending == 0 and len(test_files) >= expected_count:
        print(f"Done! {len(test_files)} images generated.")
        break
    time.sleep(10)
```

## Evaluation Tips

- **Copy output to organized directory** for side-by-side comparison
- **Generate a grid**: 4-6 images per row with labels (checkpoint + strength)
- **Test diverse outfits**: athletic, casual, formal, swimwear, lingerie
- **For Pony V6 XL**: use `score_9, score_8_up` prefix + `score_6, score_5, score_4` in negative
- **Body LoRA on Pony V6**: strengths below 0.9 look cartoonish — Pony's base anime style dominates at lower LoRA weights
- **Use different seeds** for each test to avoid seed-dependent artifacts
- **Best checkpoint selection**: don't default to the final step. Compare step 1000, 2000, 3000 side-by-side