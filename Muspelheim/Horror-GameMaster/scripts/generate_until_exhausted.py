#!/usr/bin/env python3
"""
Generate horror dataset entries until BytePlus V4-flash tokens exhausted.
Handles rate limits with exponential backoff.
Saves incrementally to avoid data loss.
"""

from openai import OpenAI
import json, time, sys, os

client = OpenAI(
    api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    timeout=60.0,
)

MODEL = "deepseek-v4-flash-260425"
BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
OUTFILE = f"{BASE}/dataset_generated.jsonl"

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

print(f"Existing entries: {len(seen)}", flush=True)

# Fear types and prompts
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
    "a radio tower", "a barn", "a silo", "a lighthouse",
    "a phone booth", "a bridge", "a tunnel", "a well",
    "a clock tower", "a prison cell", "a hospital ward",
    "a school gymnasium", "a server room", "a boiler room",
    "a cathedral", "a catacomb", "a lighthouse",
]

total_new = 0
consecutive_errors = 0
backoff = 5
batch_num = 0

print(f"Starting generation. Target: until tokens exhausted.", flush=True)
print(f"Rate limit backoff: {backoff}s initial, doubles on 429", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

while True:
    # Pick fear type and scenario
    ft = FEAR_TYPES[batch_num % len(FEAR_TYPES)]
    scenario = SCENARIOS[batch_num % len(SCENARIOS)]
    batch_num += 1

    # Alternate between scenario entries and entity entries
    if batch_num % 3 == 0:
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
            "Vary scenarios and techniques. No filler. "
            "ONLY 5 JSON lines."
        )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
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

        # Check token usage
        usage = resp.usage
        remaining_estimate = 500000 - (usage.total_tokens * batch_num)  # Rough estimate

        print(
            f"#{batch_num:3d} {ft:18s} {scenario:25s} "
            f"+{count:2d} new={total_new:4d} "
            f"tokens={usage.total_tokens:5d} "
            f"seen={len(seen)}",
            flush=True,
        )

        consecutive_errors = 0
        backoff = 5
        time.sleep(3)

    except Exception as e:
        err = str(e)
        consecutive_errors += 1

        if "429" in err:
            print(f"  Rate limit hit. Backoff: {backoff}s (attempt {consecutive_errors})", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)  # Max 5 min
        elif "insufficient" in err.lower() or "quota" in err.lower() or "exceeded" in err.lower():
            print(f"\n  TOKENS EXHAUSTED: {err[:100]}", flush=True)
            print(f"  Total new entries: {total_new}", flush=True)
            print(f"  Total unique entries: {len(seen)}", flush=True)
            break
        else:
            print(f"  Error: {err[:80]}", flush=True)
            time.sleep(10)

        if consecutive_errors >= 20:
            print(f"\n  Too many consecutive errors ({consecutive_errors}). Stopping.", flush=True)
            break

outf.close()

print(f"\n{'='*60}", flush=True)
print(f"GENERATION COMPLETE", flush=True)
print(f"  New entries: {total_new}", flush=True)
print(f"  Total unique: {len(seen)}", flush=True)
print(f"  Output: {OUTFILE}", flush=True)
print(f"{'='*60}", flush=True)
