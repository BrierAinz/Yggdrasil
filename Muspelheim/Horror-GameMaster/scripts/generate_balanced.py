#!/usr/bin/env python3
"""
Balance dataset v2 — target underrepresented fear types.
Focus on false_security (13 -> ~250) and body_horror (176 -> ~250).
Only uses VERIFIED working models + MiMo.
"""

import json
import os
import random
import time

from openai import OpenAI


BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
UNIFIED = f"{BASE}/dataset_unified.jsonl"
OUTFILE = f"{BASE}/dataset_balanced.jsonl"

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

# ONLY VERIFIED WORKING MODELS (tested 2026-05-29)
MODELS = [
    ("byteplus", "glm-4-7-251222", "glm4.7", 494397),
    ("byteplus", "gpt-oss-120b-250805", "gpt-oss", 498304),
    ("byteplus", "seed-2-0-lite-260428", "s20-lite", 372063),
    ("byteplus", "seed-1-8-251228", "s1.8", 359485),
    ("byteplus", "seed-2-0-mini-260428", "s20-mini", 279933),
    ("byteplus", "deepseek-v3-2-251201", "ds3.2", 235546),
    ("byteplus", "seed-2-0-code-preview-260328", "s20-code", 140534),
    ("byteplus", "seed-1-6-250915", "s1.6", 500000),
    ("byteplus", "seed-1-6-flash-250715", "s1.6-flash", 500000),
    # MiMo DISABLED — hangs on API calls
    # ("mimo",     "MiMo-V2.5",                 "mimo",        999999),
    # ("mimo",     "MiMo-V2.5-Pro",             "mimo-pro",    999999),
]

exhausted = set()

# --- Load existing for dedup ---
seen = set()
for fname in [
    "dataset_unified.jsonl",
    "dataset_generated_v3.jsonl",
    "dataset_balanced.jsonl",
    "dataset_environmental.jsonl",
]:
    fpath = f"{BASE}/{fname}"
    if os.path.exists(fpath):
        with open(fpath) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    seen.add(obj.get("output", "")[:100])
                except:
                    pass

print(f"Starting with {len(seen)} existing entries (dedup)", flush=True)
print(f"Models available: {len(MODELS)}", flush=True)

# --- Targeted content for BALANCING ---

BALANCE_TARGETS = {
    "false_security": {
        "weight": 10,
        "scenarios": [
            "a hospital where everything seems normal but isn't",
            "a friendly neighbor's house that's too perfect",
            "a safe room that the player trusts completely",
            "a rescue team arriving to save the player",
            "a well-lit corridor that feels secure",
            "a phone call from a loved one",
            "a church or sanctuary",
            "a police station",
            "a school during daytime with people around",
            "a shopping mall with other shoppers",
            "a campfire with friendly strangers",
            "a doctor's office during a checkup",
            "a therapist's comfortable session room",
            "a warm kitchen with food cooking",
            "an elevator with other passengers",
            "a bus during rush hour with commuters",
            "a hotel room with good reviews",
            "a museum with security guards",
            "a playground with children laughing nearby",
            "a garden in full bloom on a sunny day",
            "a library with a helpful librarian",
            "a restaurant with other diners",
            "a train car with sleeping passengers",
            "a friend's living room during a visit",
            "a workplace break room with coworkers",
            "a gym with other people exercising",
            "a spa with relaxing music",
            "a grocery store during business hours",
            "a waiting room with magazines",
            "a parking lot with other cars and lights",
        ],
        "prompt_templates": [
            lambda sc: (
                f"Generate 5 FALSE SECURITY horror entries. Setting: {sc}. "
                "The scene MUST feel safe, warm, friendly at first. Then introduce "
                "ONE subtle wrong detail that the player might miss. The horror is "
                "in the GAP between how safe things feel and how wrong they actually are. "
                "Do NOT make it obviously scary. The wrong detail should be easy to dismiss. "
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                "ONLY valid JSON lines, no markdown."
            ),
            lambda sc: (
                f"Generate 5 FALSE SECURITY entries. Setting: {sc}. "
                "Write about a moment of RELIEF that is actually the setup for something worse. "
                "The player has just escaped danger. They found safety. Everything is fine. "
                "Except one tiny detail suggests the safety is manufactured, staged, or a trap. "
                "The tone should be 90% comforting, 10% unsettling. "
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                "ONLY valid JSON lines."
            ),
            lambda sc: (
                f"Generate 5 FALSE SECURITY entries about TRUST being weaponized. Setting: {sc}. "
                "An NPC is helping the player. They seem genuine. Their advice works. "
                "But there are signs — ambiguous signs — that this NPC knows more than they say, "
                'or that the "help" is guiding the player somewhere specific. '
                "The player should feel grateful AND slightly uneasy. "
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                "ONLY valid JSON lines."
            ),
            lambda sc: (
                f"Generate 5 FALSE SECURITY entries about ROUTINE hiding horror. Setting: {sc}. "
                "The scene is mundane, everyday, boring even. Nothing is wrong. "
                "But the player notices that this exact scene — same sounds, same smells, same "
                "arrangement — has happened before. Deja vu. Or is the environment on a loop? "
                "The horror is in repetition that the player can't prove. "
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                "ONLY valid JSON lines."
            ),
        ],
    },
    "body_horror": {
        "weight": 4,
        "scenarios": [
            "a hospital with experimental procedures",
            "a laboratory with specimens in jars",
            "a bathroom with mirrors that reflect wrong",
            "a tattoo parlor after hours",
            "a prosthetics workshop with spare parts",
            "a veterinary clinic with unusual patients",
            "a beauty salon offering strange treatments",
            "a gym with modified equipment",
            "a pool with water that's slightly too thick",
            "a sauna where the steam has texture",
            "a dental office with tools that move",
            "a pharmacy with unlabeled medications",
            "a meat processing plant with familiar shapes",
            "a tannery with hides that look like faces",
            "a wax museum where figures blink",
            "a morgue with one too many drawers",
            "a maternity ward at 3am",
            "a dermatology clinic with growth samples",
            "a blood bank with warm bags",
            "a physical therapy room with stretchy skin models",
        ],
        "prompt_templates": [
            lambda sc: (
                f"Generate 5 BODY HORROR entries. Setting: {sc}. "
                "Focus on the WRONGNESS of flesh — not gore, but transformation. "
                "Things that should not be growing, shrinking, moving, or changing. "
                "The body betraying itself. Sensations that have no source. "
                "Subtle at first, escalating. "
                'JSON: instruction, input, output (150-250 words), fear_type="body_horror". '
                "ONLY valid JSON lines."
            ),
            lambda sc: (
                f"Generate 5 BODY HORROR entries about PERCEPTION. Setting: {sc}. "
                "The player notices something wrong with their own body — "
                "a mark that appeared, a sensation that won't stop, a limb that "
                "responds differently than expected. Not painful. Just WRONG. "
                "The horror is in realizing the body is changing and you can't stop it. "
                'JSON: instruction, input, output (150-250 words), fear_type="body_horror". '
                "ONLY valid JSON lines."
            ),
            lambda sc: (
                f"Generate 5 BODY HORROR entries about MIMICRY. Setting: {sc}. "
                "Something is imitating human body parts imperfectly. "
                "A hand that has too many joints. A face whose proportions are slightly off. "
                "Skin with the wrong texture. Not monstrous — just NOT QUITE RIGHT. "
                "Uncanny valley territory. "
                'JSON: instruction, input, output (150-250 words), fear_type="body_horror". '
                "ONLY valid JSON lines."
            ),
        ],
    },
}

# Flat list for random selection
generation_pool = []
for ft, config in BALANCE_TARGETS.items():
    for _ in range(config["weight"]):
        generation_pool.append(ft)

# --- Stats ---
total_new = 0
total_calls = 0
errors_by_model = {}
batch_num = 0
generated_per_type = dict.fromkeys(BALANCE_TARGETS, 0)

print("\nGenerating balanced entries...", flush=True)
print("Targets: false_security +175+, body_horror +75+", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

MAX_BATCHES = 300

while len(exhausted) < len(MODELS) and batch_num < MAX_BATCHES:
    available = [(p, m, n, t) for p, m, n, t in MODELS if f"{p}:{m}" not in exhausted]
    if not available:
        print("All models exhausted!", flush=True)
        break

    provider_name, model, short, tokens = available[batch_num % len(available)]
    client = providers[provider_name]

    ft = random.choice(generation_pool)
    config = BALANCE_TARGETS[ft]
    scenario = random.choice(config["scenarios"])
    template = random.choice(config["prompt_templates"])
    prompt = template(scenario)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Output ONLY valid JSONL. No markdown, no fences, no code blocks. Raw JSON objects, one per line. Every entry MUST have fear_type field.",
                },
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
                    obj["fear_type"] = ft  # force correct type
                    key = obj["output"][:100]
                    if len(obj["output"]) > 80 and key not in seen:
                        seen.add(key)
                        outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                        outf.flush()
                        count += 1
                        total_new += 1
                        generated_per_type[ft] += 1
            except json.JSONDecodeError:
                pass

        total_calls += 1
        errors_by_model.pop(f"{provider_name}:{model}", None)

        progress = " | ".join(f"{k}:{v}" for k, v in generated_per_type.items())
        print(
            f"#{total_calls:3d} {short:12s} {ft:18s} +{count:2d} new={total_new:4d} [{progress}]",
            flush=True,
        )

        time.sleep(1.5)

    except Exception as e:
        err = str(e)
        key = f"{provider_name}:{model}"
        errors_by_model[key] = errors_by_model.get(key, 0) + 1

        if any(x in err for x in ["429", "SetLimitExceeded", "insufficient", "quota", "suspended"]):
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

    batch_num += 1

outf.close()

# --- Merge into unified ---
print("\nMerging into unified dataset...", flush=True)
all_entries = {}
for fname in ["dataset_unified.jsonl", "dataset_balanced.jsonl", "dataset_environmental.jsonl"]:
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

# Normalize stray fear types
NORMALIZE = {
    "guilt & entrapment": "paranoia",
    "memory loss & oblivion": "psychological",
    "repression & erasure": "psychological",
    "cosmic dread": "psychological",
    "cosmic horror": "psychological",
    "body horror / obsession": "body_horror",
    "organic transformation": "body_horror",
    "false lead with real threat hint": "false_security",
}
for entry in all_entries.values():
    ft = entry.get("fear_type", "").lower().strip()
    if ft in NORMALIZE:
        entry["fear_type"] = NORMALIZE[ft]

with open(UNIFIED, "w") as f:
    for entry in all_entries.values():
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# --- Final stats ---
from collections import Counter


fear_counts = Counter(e.get("fear_type", "unknown") for e in all_entries.values())

print(f"\n{'=' * 60}", flush=True)
print("BALANCING COMPLETE", flush=True)
print(f"  New entries this run: {total_new}", flush=True)
print(f"  Total unique entries: {len(all_entries)}", flush=True)
print(f"  API calls: {total_calls}", flush=True)
print(f"  Models exhausted: {len(exhausted)}/{len(MODELS)}", flush=True)
print("", flush=True)
print("  Distribution:", flush=True)
for ft, count in sorted(fear_counts.items(), key=lambda x: -x[1]):
    pct = count / len(all_entries) * 100
    print(f"    {ft:<22} {count:>5} ({pct:.1f}%)", flush=True)
print("", flush=True)
print(f"  Output: {UNIFIED}", flush=True)
print(f"{'=' * 60}", flush=True)
