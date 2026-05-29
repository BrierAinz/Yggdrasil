#!/usr/bin/env python3
"""
Generate horror dataset v3 — MAXIMUM MODELS.
BytePlus (17 models) + MiMo (2 models) = 19 models total.
Deduplicates against unified dataset.
"""

from openai import OpenAI
import json, time, sys, os, random

BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
UNIFIED = f"{BASE}/dataset_unified.jsonl"
OUTFILE = f"{BASE}/dataset_generated_v3.jsonl"

# --- Providers ---

providers = {
    "byteplus": OpenAI(
        api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
        base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
        timeout=90.0,
    ),
    "mimo": OpenAI(
        api_key="tp-siky3g42t4i563ttw3o6nqkm67fevv2jzp8b5ahh3gqejv8w",
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        timeout=90.0,
    ),
}

# (provider, model_id, display_name, tokens_remaining)
MODELS = [
    ("byteplus", "seed-2-0-pro-260328",        "s20-pro",     415918),
    ("byteplus", "deepseek-v3-2-251201",        "ds3.2",       448161),
    ("byteplus", "seed-2-0-lite-260428",        "s20-lite",    372063),
    ("byteplus", "seed-1-8-251228",             "s1.8",        359485),
    ("byteplus", "seed-2-0-mini-260428",        "s20-mini",    295395),
    ("byteplus", "seed-2-0-code-preview-260328","s20-code",    140534),
    ("byteplus", "glm-4-7-251222",             "glm4.7",      500000),
    ("byteplus", "gpt-oss-120b-250805",        "gpt-oss",     500000),
    ("byteplus", "seed-1-6-250915",            "s1.6",        500000),
    ("byteplus", "seed-1-6-flash-250715",      "s1.6f",       500000),
    ("byteplus", "kimi-k2-250905",             "kimi",        500000),
    ("byteplus", "deepseek-v3-1-250821",       "ds3.1",       500000),
    ("byteplus", "skylark-pro-250215",         "sky-pro",     500000),
    ("byteplus", "skylark-lite-250215",        "sky-lite",    500000),
    ("byteplus", "deepseek-r1-250528",         "r1",          500000),
    ("byteplus", "seed-2-0-mini-260215",       "s20m-0215",   500000),
    ("byteplus", "seed-2-0-lite-260228",       "s20l-0228",   500000),
    ("mimo",     "MiMo-V2.5",                  "mimo",        999999),
    ("mimo",     "MiMo-V2.5-Pro",              "mimo-pro",    999999),
]

exhausted = set()

# --- Load existing for dedup ---
seen = set()
for fname in ["dataset_unified.jsonl", "dataset_generated_v2.jsonl"]:
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
print(f"Models available: {len(MODELS)}", flush=True)

# --- Content ---

FEAR_TYPES = [
    "psychological", "darkness", "isolation", "body_horror",
    "paranoia", "loss_of_control", "jumpscare", "false_security",
]
FEAR_WEIGHTS = [1, 1, 1, 2, 1, 1, 1, 4]

SCENARIOS = [
    "a subway tunnel at 3am", "a parking garage", "a laundromat at midnight",
    "a public library after hours", "an empty swimming pool", "a cruise ship at night",
    "a shopping mall after closing", "an abandoned factory", "a courtroom at night",
    "a church confessional", "a morgue", "a greenhouse at dusk",
    "a rooftop in fog", "a broken elevator", "a sewer system",
    "a lighthouse in a storm", "a submarine", "a derelict space station",
    "an abandoned theater", "a mirror maze", "an infinite library",
    "a corrupted garden", "a frozen lake", "a flooded mine shaft",
    "a radio tower", "a barn at midnight", "a silo", "a phone booth in the rain",
    "a suspension bridge", "a road tunnel", "a dry well", "a clock tower",
    "a prison cell", "a hospital ward", "a school gymnasium at night",
    "a server room", "a boiler room", "a cathedral crypt", "a catacomb",
    "a train station at 4am", "a cemetery in fog", "a traveling carnival",
    "a warehouse district", "a hotel lobby at 3am", "a restaurant kitchen after hours",
    "a bank vault", "a planetarium with the lights off", "a meat locker",
    "an attic", "a basement", "a walk-in closet", "a motel room",
    "a construction site at night", "a water treatment plant", "a power station",
    "a quarantine ward", "an asylum hallway", "a doll factory",
    "a wax museum after hours", "a taxidermy shop", "a funeral home",
    "a children's playground at midnight", "an empty school hallway",
    "a dark forest", "an old bridge over a ravine", "a shipwreck",
    "an underground parking level B3", "a hospital basement",
    "a hallway that keeps repeating", "a room with no doors",
]

PROMPT_TEMPLATES = [
    lambda ft, sc: (
        f"Generate 5 horror SCENE entries. Fear: \"{ft}\". Setting: {sc}. "
        "JSON: instruction, input, output, fear_type. "
        "output=100-250 words, second-person narration, atmospheric. "
        "ONLY valid JSON lines, no markdown."
    ),
    lambda ft, sc: (
        f"Generate 5 NPC DIALOGUE entries. Fear: \"{ft}\". Setting: {sc}. "
        "JSON: instruction (NPC description), input (player speaks), "
        "output (unsettling NPC reply, 100-200 words), fear_type. "
        "ONLY valid JSON lines."
    ),
    lambda ft, sc: (
        f"Generate 5 ENVIRONMENTAL EVENT entries. Fear: \"{ft}\". Setting: {sc}. "
        "JSON: instruction (environment), input (player action), "
        "output (unsettening event, 100-200 words), fear_type. "
        "Sounds, temperature, objects moving, reality shifting. ONLY JSON lines."
    ),
    lambda ft, sc: (
        f"Generate 5 FORESHADOWING entries. Fear: \"{ft}\". Setting: {sc}. "
        "JSON: instruction (setup), input (player investigates), "
        "output (hints at worse things, 100-200 words), fear_type. "
        "Mix real threats with false leads. ONLY JSON lines."
    ),
    lambda ft, sc: (
        f"Generate 3 ENTITY entries. Fear: \"{ft}\". Setting: {sc}. "
        "JSON: instruction (entity description), input (encounter), "
        "output (150-300 words, visceral, SCP/Silent Hill style), fear_type. "
        "ONLY JSON lines."
    ),
]

# --- Stats ---
total_new = 0
total_calls = 0
errors_by_model = {}
batch_num = 0

print(f"Generating...", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

while len(exhausted) < len(MODELS):
    available = [(p, m, n, t) for p, m, n, t in MODELS if f"{p}:{m}" not in exhausted]
    if not available:
        print("All models exhausted!", flush=True)
        break

    provider_name, model, short, tokens = available[batch_num % len(available)]
    client = providers[provider_name]

    ft = random.choices(FEAR_TYPES, weights=FEAR_WEIGHTS, k=1)[0]
    scenario = random.choice(SCENARIOS)
    template = random.choice(PROMPT_TEMPLATES)
    prompt = template(ft, scenario)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output ONLY valid JSONL. No markdown, no fences. Raw JSON objects, one per line."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
            max_tokens=4000,
        )

        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = "\n".join(content.split("\n")[1:])
        if content.endswith("```"):
            content = "\n".join(content.split("\n")[:-1])
        content = content.strip()

        count = 0
        for line in content.split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if all(k in obj for k in ["instruction", "input", "output"]):
                    if "fear_type" not in obj:
                        obj["fear_type"] = ft
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
        errors_by_model.pop(f"{provider_name}:{model}", None)

        print(
            f"#{total_calls:3d} {short:12s} {ft:18s} {scenario[:22]:22s} "
            f"+{count:2d} new={total_new:4d} total={len(seen)}",
            flush=True,
        )

        time.sleep(1.5)

    except Exception as e:
        err = str(e)
        key = f"{provider_name}:{model}"
        errors_by_model[key] = errors_by_model.get(key, 0) + 1

        if any(x in err for x in ["429", "SetLimitExceeded", "insufficient", "quota"]):
            print(f"  {short}: EXHAUSTED", flush=True)
            exhausted.add(key)
        elif errors_by_model[key] >= 3:
            print(f"  {short}: 3 errors, skipping", flush=True)
            exhausted.add(key)
        else:
            print(f"  {short}: {err[:80]}", flush=True)
            time.sleep(3)

        if len(exhausted) >= len(MODELS):
            break

outf.close()

# Merge into unified
print(f"\nMerging into unified dataset...", flush=True)
all_entries = {}
for fname in ["dataset_unified.jsonl", OUTFILE.split("/")[-1]]:
    fpath = f"{BASE}/{fname}"
    if os.path.exists(fpath):
        with open(fpath) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    key = obj.get("output", "")[:100]
                    if key and len(obj.get("output", "")) > 80:
                        all_entries[key] = obj
                except:
                    pass

with open(UNIFIED, "w") as f:
    for entry in all_entries.values():
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print(f"\n{'='*60}", flush=True)
print(f"GENERATION COMPLETE", flush=True)
print(f"  New entries this run: {total_new}", flush=True)
print(f"  Total unique entries: {len(all_entries)}", flush=True)
print(f"  API calls: {total_calls}", flush=True)
print(f"  Models exhausted: {len(exhausted)}/{len(MODELS)}", flush=True)
print(f"  Output: {UNIFIED}", flush=True)
print(f"{'='*60}", flush=True)
