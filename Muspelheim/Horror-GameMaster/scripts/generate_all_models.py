#!/usr/bin/env python3
"""
Generate horror dataset with ALL available BytePlus models.
Rotates between models to maximize token usage.
Stops when ALL models are exhausted.
"""

from openai import OpenAI
import json, time, sys, os

client = OpenAI(
    api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    timeout=60.0,
)

BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
OUTFILE = f"{BASE}/dataset_generated.jsonl"

MODELS = [
    "seed-2-0-mini-260428",       # 500K tokens, cheapest
    "seed-2-0-lite-260428",       # 495K tokens
    "seed-2-0-pro-260328",        # 499K tokens
    "seed-2-0-code-preview-260328", # 500K tokens
    "seed-1-8-251228",            # 500K tokens
    "deepseek-v3-2-251201",       # 500K tokens
]

# Track which models are exhausted
exhausted = set()

# Load existing to deduplicate
seen = set()
for fname in ["dataset_final.jsonl", "dataset_entities.jsonl", "dataset_generated.jsonl"]:
    fpath = f"{BASE}/{fname}"
    if os.path.exists(fpath):
        with open(fpath) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    seen.add(obj.get("output", "")[:100])
                except:
                    pass

print(f"Starting with {len(seen)} existing entries", flush=True)
print(f"Models: {len(MODELS)}", flush=True)

FEAR_TYPES = [
    "psychological", "darkness", "isolation", "body_horror",
    "paranoia", "loss_of_control", "jumpscare", "false_security",
]

ENTITY_TYPES = [
    "lovecraftian", "junji_ito", "unknown", "flesh", "shadow",
    "mimic", "memetic", "temporal", "geometric", "nature",
    "parasitic", "recursive",
]

SCENARIOS = [
    "a subway tunnel at 3am", "a parking garage", "a laundromat",
    "a public library after hours", "a swimming pool", "a cruise ship",
    "a shopping mall at night", "a factory", "a courtroom",
    "a church confessional", "a morgue", "a greenhouse",
    "a rooftop", "an elevator", "a sewer system",
    "a lighthouse", "a submarine", "a space station",
    "an abandoned theater", "a mirror maze", "an infinite library",
    "a corrupted garden", "a frozen lake", "a mine shaft",
    "a radio tower", "a barn", "a silo", "a phone booth",
    "a bridge", "a tunnel", "a well", "a clock tower",
    "a prison cell", "a hospital ward", "a school gymnasium",
    "a server room", "a boiler room", "a cathedral", "a catacomb",
    "a train station", "a cemetery", "a carnival", "a warehouse",
    "a hotel lobby", "a restaurant kitchen", "a bank vault",
    "a planetarium", "a greenhouse", "a greenhouse",
]

total_new = 0
total_calls = 0
consecutive_errors = 0
batch_num = 0

print(f"Generating until all models exhausted...", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

while len(exhausted) < len(MODELS):
    # Pick next available model
    available = [m for m in MODELS if m not in exhausted]
    if not available:
        print("All models exhausted!", flush=True)
        break

    model = available[batch_num % len(available)]
    ft = FEAR_TYPES[batch_num % len(FEAR_TYPES)]
    scenario = SCENARIOS[batch_num % len(SCENARIOS)]
    batch_num += 1

    # Alternate between scenario entries and entity entries
    if batch_num % 4 == 0:
        etype = ENTITY_TYPES[batch_num % len(ENTITY_TYPES)]
        prompt = (
            f"Generate 3 horror ENTITY entries. Type: \"{etype}\". "
            f"Setting: {scenario}. "
            "JSON: instruction, input, output, fear_type. "
            "output=150-300 words: appearance, behavior, origin, horror, encounter. "
            "UNIQUE entities. Think SCP/Silent Hill/Junji Ito/Lovecraft. "
            "3 JSON lines only."
        )
    else:
        prompt = (
            f"Generate 5 horror entries. Fear: \"{ft}\". "
            f"Setting: {scenario}. "
            "JSON: instruction, input, output, fear_type. "
            "output=100-250 words second-person horror narration. "
            "Vary scenarios. No filler. "
            "ONLY 5 JSON lines."
        )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output ONLY valid JSONL. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
            max_tokens=4000,
        )

        content = resp.choices[0].message.content.strip()
        count = 0

        for line in content.split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if all(k in obj for k in ["instruction", "input", "output", "fear_type"]):
                    key = obj["output"][:100]
                    if len(obj["output"]) > 80 and key not in seen:
                        seen.add(key)
                        outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        outf.flush()
                        count += 1
                        total_new += 1
            except json.JSONDecodeError:
                pass

        total_calls += 1
        consecutive_errors = 0

        # Short model name for display
        short = model.replace("seed-2-0-", "s20-").replace("seed-1-8-", "s18-").replace("deepseek-v3-2-", "ds3-")

        print(
            f"#{total_calls:3d} {short:20s} {ft:18s} {scenario:22s} "
            f"+{count:2d} new={total_new:4d} seen={len(seen)}",
            flush=True,
        )

        time.sleep(2)

    except Exception as e:
        err = str(e)
        consecutive_errors += 1

        if "429" in err or "SetLimitExceeded" in err:
            print(f"  {model}: EXHAUSTED (429)", flush=True)
            exhausted.add(model)
            print(f"  Models remaining: {len(MODELS) - len(exhausted)}/{len(MODELS)}", flush=True)
        elif "insufficient" in err.lower() or "quota" in err.lower():
            print(f"  {model}: QUOTA EXHAUSTED", flush=True)
            exhausted.add(model)
        else:
            print(f"  Error ({model}): {err[:80]}", flush=True)
            time.sleep(5)

        if consecutive_errors >= len(MODELS) * 2:
            print(f"All models failing. Stopping.", flush=True)
            break

outf.close()

# Final stats
print(f"\n{'='*60}", flush=True)
print(f"GENERATION COMPLETE", flush=True)
print(f"  Total new entries: {total_new}", flush=True)
print(f"  Total unique entries: {len(seen)}", flush=True)
print(f"  Total API calls: {total_calls}", flush=True)
print(f"  Models exhausted: {len(exhausted)}/{len(MODELS)}", flush=True)
print(f"  Output: {OUTFILE}", flush=True)
print(f"{'='*60}", flush=True)
