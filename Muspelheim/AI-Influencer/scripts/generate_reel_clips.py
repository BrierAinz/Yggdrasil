#!/usr/bin/env python3
"""Generate vertical Reel clips via ComfyUI API — batch mode."""
import json, time, random, shutil, urllib.request
from pathlib import Path

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer")
OUTPUT_DIR = PROJECT_DIR / "outputs/reel_clips"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load content plan
with open(PROJECT_DIR / "config/prompts/eir_content_plan.json") as f:
    plan = json.load(f)

base_char = plan["prompt_templates"]["base_character"]
quality = plan["prompt_templates"]["quality_tags"]
neg = plan["negative_prompts"]["master"]

# 3 reels x 3 clips each = 9 clips total
clip_prompts = [
    # Reel 1: "Northern Mystique" (aurora + temple + snow)
    (f"{base_char}, dark flowing robes with silver embroidery, standing before northern lights aurora borealis, ethereal green and purple sky, cinematic slow pan, mystical atmosphere, {quality}", "reel1_aurora"),
    (f"{base_char}, ornate dark plate armor with runic etchings, ancient temple with crystal pillars, ethereal blue glow, dramatic lighting, camera slowly zooming in, {quality}", "reel1_temple"),
    (f"{base_char}, white fur-trimmed cloak, snowy forest at golden hour, gentle snowfall, dreamy warm light, slow motion gaze, {quality}", "reel1_snow"),

    # Reel 2: "Dark Elegance" (candle + armor + mirror)
    (f"{base_char}, black velvet dress with silver clasp, candlelit chamber, warm firelight, soft shadows, intimate close-up, gentle breathing, {quality}", "reel2_candle"),
    (f"{base_char}, full ceremonial armor with ice crystal tiara, grand hall, cinematic side lighting, powerful stance, slow turn, {quality}", "reel2_armor"),
    (f"{base_char}, dark hooded cape, looking into ornate mirror, reflection showing mysterious gaze, purple mist, slow reveal, {quality}", "reel2_mirror"),

    # Reel 3: "Wild Spirit" (forest + huntress + aurora)
    (f"{base_char}, leather hunting outfit with fur accents, dense frozen forest, morning frost, bow in hand, alert gaze, tracking movement, {quality}", "reel3_huntress"),
    (f"{base_char}, oversized cream knit sweater, cozy log cabin window, hot mug, frost on glass, warm firelight, gentle content smile, {quality}", "reel3_cozy"),
    (f"{base_char}, shimmering ice crown, aurora borealis reflected in frozen lake, standing at waters edge, wind catching hair, epic landscape, {quality}", "reel3_lake"),
]

def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]

def wait_for_prompt(prompt_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except Exception:
            pass
        time.sleep(3)

# Load vertical workflow
with open(PROJECT_DIR / "workflows/eir_reel_vertical_api.json") as f:
    base_workflow = json.load(f)

# Queue all 9 clips
print("Queueing 9 vertical clips (3 reels x 3 clips)...")
prompt_ids = []
for i, (prompt, name) in enumerate(clip_prompts):
    seed = random.randint(10000, 99999)
    workflow = json.loads(json.dumps(base_workflow))  # deep copy
    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = neg
    workflow["3"]["inputs"]["noise_seed"] = seed
    workflow["5"]["inputs"]["filename_prefix"] = f"eir_reel_{name}"

    pid = queue_prompt(workflow)
    prompt_ids.append((pid, name, seed, i))
    print(f"  [{i+1}/9] Queued: {name} (seed={seed}, pid={pid[:8]})")
    time.sleep(0.5)  # small delay between queue

# Wait for all to complete
print("\nWaiting for all clips to generate (this may take 15-20 minutes)...")
results = {}
for pid, name, seed, idx in prompt_ids:
    print(f"  Waiting for {name}...", end=" ", flush=True)
    history = wait_for_prompt(pid, timeout=600)

    # Find output file
    comfy_out = Path.home() / "comfy/ComfyUI/output"
    found = None
    for nid, nout in history.get("outputs", {}).items():
        if "images" in nout:
            for img in nout["images"]:
                src = comfy_out / img["filename"]
                if src.exists():
                    dest = OUTPUT_DIR / f"{name}.webp"
                    shutil.copy2(src, dest)
                    found = dest
                    break
        if found:
            break

    if found:
        results[name] = found
        print(f"OK -> {found.name}")
    else:
        print("FAILED (no output found)")

print(f"\nDone! Generated {len(results)}/9 clips.")
print(f"Output: {OUTPUT_DIR}")
for name, path in results.items():
    print(f"  {name}: {path.name} ({path.stat().st_size / 1024:.0f} KB)")
