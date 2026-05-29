#!/usr/bin/env python3
"""
Generate horror dataset v2 — multi-provider rotation.
BytePlus + MiMo models. Deduplicates against unified dataset.
Targets underrepresented fear types.
"""

import json
import os
import random
import time

from openai import OpenAI


BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
UNIFIED = f"{BASE}/dataset_unified.jsonl"
OUTFILE = f"{BASE}/dataset_generated_v2.jsonl"

# --- Providers ---

providers = {
    "byteplus": OpenAI(
        api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
        base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
        timeout=60.0,
    ),
    "mimo": OpenAI(
        api_key="tp-siky3g42t4i563ttw3o6nqkm67fevv2jzp8b5ahh3gqejv8w",
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
        timeout=60.0,
    ),
}

MODELS = [
    ("byteplus", "seed-2-0-mini-260428"),
    ("byteplus", "seed-2-0-lite-260428"),
    ("byteplus", "seed-2-0-pro-260328"),
    ("byteplus", "seed-1-8-251228"),
    ("byteplus", "deepseek-v3-2-251201"),
    ("mimo", "MiMo-V2.5"),
    ("mimo", "MiMo-V2.5-Pro"),
]

exhausted = set()

# --- Load existing for dedup ---
seen = set()
if os.path.exists(UNIFIED):
    with open(UNIFIED) as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                seen.add(obj.get("output", "")[:100])
            except:
                pass

print(f"Starting with {len(seen)} existing entries in unified dataset", flush=True)

# --- Content ---

FEAR_TYPES = [
    "psychological",
    "darkness",
    "isolation",
    "body_horror",
    "paranoia",
    "loss_of_control",
    "jumpscare",
    "false_security",
]

# Weight underrepresented types more heavily
FEAR_WEIGHTS = [1, 1, 1, 2, 1, 1, 1, 4]  # false_security gets 4x weight

SCENARIOS = [
    "a subway tunnel at 3am",
    "a parking garage",
    "a laundromat at midnight",
    "a public library after hours",
    "an empty swimming pool",
    "a cruise ship at night",
    "a shopping mall after closing",
    "an abandoned factory",
    "a courtroom at night",
    "a church confessional",
    "a morgue",
    "a greenhouse at dusk",
    "a rooftop in fog",
    "a broken elevator",
    "a sewer system",
    "a lighthouse in a storm",
    "a submarine",
    "a derelict space station",
    "an abandoned theater",
    "a mirror maze",
    "an infinite library",
    "a corrupted garden",
    "a frozen lake",
    "a flooded mine shaft",
    "a radio tower",
    "a barn at midnight",
    "a silo",
    "a phone booth in the rain",
    "a suspension bridge",
    "a road tunnel",
    "a dry well",
    "a clock tower",
    "a prison cell",
    "a hospital ward",
    "a school gymnasium at night",
    "a server room",
    "a boiler room",
    "a cathedral crypt",
    "a catacomb",
    "a train station at 4am",
    "a cemetery in fog",
    "a traveling carnival",
    "a warehouse district",
    "a hotel lobby at 3am",
    "a restaurant kitchen after hours",
    "a bank vault",
    "a planetarium with the lights off",
    "a meat locker",
    "an attic",
    "a basement",
    "a walk-in closet",
    "a motel room",
    "a construction site at night",
    "a water treatment plant",
    "a power station",
    "a quarantine ward",
    "an asylum hallway",
    "a doll factory",
    "a wax museum after hours",
    "a taxidermy shop",
    "a funeral home",
    "a children's playground at midnight",
    "an empty school hallway",
]

ENTITY_TYPES = [
    "lovecraftian",
    "junji_ito",
    "flesh",
    "shadow",
    "mimic",
    "memetic",
    "temporal",
    "geometric",
    "nature",
    "parasitic",
    "recursive",
    "uncanny_valley",
]

PROMPT_TEMPLATES = [
    # Scene descriptions
    lambda ft, sc: (
        f'Generate 5 horror SCENE entries. Fear type: "{ft}". '
        f"Setting: {sc}. "
        "JSON format: instruction, input, output, fear_type. "
        "output = 100-250 words, second-person horror narration. "
        "Make each entry UNIQUE — different angles, different details. "
        "No filler, pure atmosphere. ONLY 5 JSON lines."
    ),
    # NPC dialogues
    lambda ft, sc: (
        f'Generate 5 horror NPC DIALOGUE entries. Fear: "{ft}". '
        f"Setting: {sc}. "
        "JSON: instruction (describe NPC), input (player says something), "
        "output (NPC reply that is unsettling, 100-200 words), fear_type. "
        "NPCs should seem normal at first, then something is wrong. "
        "ONLY 5 JSON lines."
    ),
    # Environmental events
    lambda ft, sc: (
        f'Generate 5 ENVIRONMENTAL EVENT entries. Fear: "{ft}". '
        f"Setting: {sc}. "
        "JSON: instruction (describe the environment), input (player action), "
        "output (what happens next — unsettling, 100-200 words), fear_type. "
        "Events: sounds, temperature changes, objects moving, reality shifting. "
        "ONLY 5 JSON lines."
    ),
    # Foreshadowing / red herrings
    lambda ft, sc: (
        f'Generate 5 FORESHADOWING entries. Fear: "{ft}". '
        f"Setting: {sc}. "
        "JSON: instruction (setup), input (player investigates), "
        "output (what they find — hints at worse things, 100-200 words), fear_type. "
        "Mix real threats with false leads. ONLY 5 JSON lines."
    ),
    # Entity encounters
    lambda ft, sc: (
        f'Generate 3 ENTITY ENCOUNTER entries. Type: "{ft}". '
        f"Setting: {sc}. "
        "JSON: instruction (entity description), input (player encounters it), "
        "output (the encounter — 150-300 words, visceral, atmospheric), fear_type. "
        "Think SCP Foundation / Silent Hill / Junji Ito / Lovecraft. "
        "ONLY 3 JSON lines."
    ),
]

# --- Generation loop ---

total_new = 0
total_calls = 0
consecutive_errors = 0
batch_num = 0

print(f"Generating with {len(MODELS)} models across {len(providers)} providers...", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

while len(exhausted) < len(MODELS):
    available = [(p, m) for p, m in MODELS if f"{p}:{m}" not in exhausted]
    if not available:
        print("All models exhausted!", flush=True)
        break

    provider_name, model = available[batch_num % len(available)]
    client = providers[provider_name]

    # Weighted fear type selection
    ft = random.choices(FEAR_TYPES, weights=FEAR_WEIGHTS, k=1)[0]
    scenario = random.choice(SCENARIOS)
    template = random.choice(PROMPT_TEMPLATES)

    prompt = template(ft, scenario)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Output ONLY valid JSONL. No markdown, no code fences, no explanation. Just raw JSON objects, one per line.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
            max_tokens=4000,
        )

        content = resp.choices[0].message.content.strip()
        # Clean up markdown fences if present
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
                    # Normalize fear_type
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
        consecutive_errors = 0

        short_model = (
            model.replace("seed-2-0-", "s20-")
            .replace("seed-1-8-", "s18-")
            .replace("deepseek-v3-2-", "ds3-")
        )
        short_prov = provider_name[:2]

        print(
            f"#{total_calls:3d} {short_prov}:{short_model:20s} {ft:18s} {scenario[:22]:22s} "
            f"+{count:2d} new={total_new:4d} total={len(seen)}",
            flush=True,
        )

        time.sleep(2)

    except Exception as e:
        err = str(e)
        consecutive_errors += 1
        key = f"{provider_name}:{model}"

        if (
            "429" in err
            or "SetLimitExceeded" in err
            or "insufficient" in err.lower()
            or "quota" in err.lower()
        ):
            print(f"  {key}: EXHAUSTED", flush=True)
            exhausted.add(key)
        else:
            print(f"  Error ({key}): {err[:100]}", flush=True)
            time.sleep(5)

        if consecutive_errors >= len(MODELS) * 2:
            print("All models failing. Stopping.", flush=True)
            break

outf.close()

print(f"\n{'=' * 60}", flush=True)
print("GENERATION COMPLETE", flush=True)
print(f"  New entries this run: {total_new}", flush=True)
print(f"  Total unique entries: {len(seen)}", flush=True)
print(f"  API calls: {total_calls}", flush=True)
print(f"  Models exhausted: {len(exhausted)}/{len(MODELS)}", flush=True)
print(f"  Output: {OUTFILE}", flush=True)
print(f"{'=' * 60}", flush=True)
