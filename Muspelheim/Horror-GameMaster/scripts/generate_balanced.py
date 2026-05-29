#!/usr/bin/env python3
"""
Balance dataset — target underrepresented fear types.
Focus on false_security (13 -> ~250) and body_horror (176 -> ~250).
Uses ALL available BytePlus models + MiMo rotation.
"""

from openai import OpenAI
import json, time, sys, os, random

BASE = "/home/brierainz/Proyectos/Yggdrasil/Muspelheim/Horror-GameMaster/data"
UNIFIED = f"{BASE}/dataset_unified.jsonl"
OUTFILE = f"{BASE}/dataset_balanced.jsonl"

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
# Ordered by tokens remaining — use fullest first to avoid suspension
MODELS = [
    # === 500K tokens each (full) ===
    ("byteplus", "deepseek-v3-1-250821",       "ds3.1",       500000),
    ("byteplus", "kimi-k2-250905",             "kimi-k2",     500000),
    ("byteplus", "seed-1-6-250915",            "s1.6",        500000),
    ("byteplus", "seed-1-6-flash-250715",      "s1.6-flash",  500000),
    ("byteplus", "skylark-lite-250215",        "sky-lite",    500000),
    ("byteplus", "skylark-pro-250215",         "sky-pro",     500000),
    ("byteplus", "deepseek-v3",                "ds3",         500000),
    ("byteplus", "deepseek-r1-250528",         "r1",          500000),
    ("byteplus", "deepseek-r1-distill-qwen-32b-250120", "r1-distill", 500000),
    # === Partially used ===
    ("byteplus", "glm-4-7-251222",            "glm4.7",      494397),
    ("byteplus", "gpt-oss-120b-250805",       "gpt-oss",     498304),
    ("byteplus", "seed-2-0-lite-260428",      "s20-lite",    372063),
    ("byteplus", "seed-1-8-251228",           "s1.8",        359485),
    ("byteplus", "seed-2-0-mini-260428",      "s20-mini",    279933),
    ("byteplus", "deepseek-v3-2-251201",      "ds3.2",       235546),
    ("byteplus", "seed-2-0-code-preview-260328", "s20-code", 140534),
    # === MiMo (unlimited) ===
    ("mimo",     "MiMo-V2.5",                "mimo",        999999),
    ("mimo",     "MiMo-V2.5-Pro",            "mimo-pro",    999999),
]

exhausted = set()

# --- Load existing for dedup ---
seen = set()
for fname in ["dataset_unified.jsonl", "dataset_generated_v3.jsonl", "dataset_balanced.jsonl"]:
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

# We need ~175 false_security + ~75 body_horror entries
# Also some environmental_storytelling variety

BALANCE_TARGETS = {
    "false_security": {
        "weight": 10,  # heavily weighted
        "scenarios": [
            "a hospital where everything seems normal but isn't",
            "a friendly neighbor's house that's too perfect",
            "a safe room that the player trusts",
            "a rescue team arriving to save the player",
            "a well-lit corridor that feels secure",
            "a phone call from a loved one",
            "a church or sanctuary",
            "a police station",
            "a school during daytime",
            "a shopping mall with other people around",
            "a campfire with friendly strangers",
            "a doctor's office",
            "a therapist's session",
            "a warm kitchen with food cooking",
            "an elevator with other passengers",
            "a bus during rush hour",
            "a hotel room with good reviews",
            "a museum with security guards",
            "a playground with children laughing",
            "a garden in full bloom",
        ],
        "prompt_templates": [
            lambda sc: (
                f'Generate 5 FALSE SECURITY horror entries. Setting: {sc}. '
                'The scene MUST feel safe, warm, friendly at first. Then introduce '
                'ONE subtle wrong detail that the player might miss. The horror is '
                'in the GAP between how safe things feel and how wrong they actually are. '
                'Do NOT make it obviously scary. The wrong detail should be easy to dismiss. '
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                'ONLY valid JSON lines, no markdown.'
            ),
            lambda sc: (
                f'Generate 5 FALSE SECURITY entries. Setting: {sc}. '
                'Write about a moment of RELIEF that is actually the setup for something worse. '
                'The player has just escaped danger. They found safety. Everything is fine. '
                'Except one tiny detail suggests the safety is manufactured, staged, or a trap. '
                'The tone should be 90% comforting, 10% unsettling. '
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                'ONLY valid JSON lines.'
            ),
            lambda sc: (
                f'Generate 5 FALSE SECURITY entries about TRUST being weaponized. Setting: {sc}. '
                'An NPC is helping the player. They seem genuine. Their advice works. '
                'But there are signs — ambiguous signs — that this NPC knows more than they say, '
                'or that the "help" is guiding the player somewhere specific. '
                'The player should feel grateful AND slightly uneasy. '
                'JSON: instruction, input, output (150-250 words), fear_type="false_security". '
                'ONLY valid JSON lines.'
            ),
        ],
    },
    "body_horror": {
        "weight": 4,
        "scenarios": [
            "a hospital with experimental procedures",
            "a laboratory with specimens",
            "a bathroom with mirrors",
            "a tattoo parlor after hours",
            "a prosthetics workshop",
            "a veterinary clinic",
            "a beauty salon with strange treatments",
            "a gym with modified equipment",
            "a pool with strange water",
            "a sauna that's too hot",
            "a dental office",
            "a pharmacy with unknown medications",
            "a meat processing plant",
            "a tannery",
            "a wax museum",
        ],
        "prompt_templates": [
            lambda sc: (
                f'Generate 5 BODY HORROR entries. Setting: {sc}. '
                'Focus on the WRONGNESS of flesh — not gore, but transformation. '
                'Things that should not be growing, shrinking, moving, or changing. '
                'The body betraying itself. Sensations that have no source. '
                'Subtle at first, escalating. '
                'JSON: instruction, input, output (150-250 words), fear_type="body_horror". '
                'ONLY valid JSON lines.'
            ),
            lambda sc: (
                f'Generate 5 BODY HORROR entries about PERCEPTION. Setting: {sc}. '
                'The player notices something wrong with their own body — '
                'a mark that appeared, a sensation that won\'t stop, a limb that '
                'responds differently than expected. Not painful. Just WRONG. '
                'The horror is in realizing the body is changing and you can\'t stop it. '
                'JSON: instruction, input, output (150-250 words), fear_type="body_horror". '
                'ONLY valid JSON lines.'
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
generated_per_type = {ft: 0 for ft in BALANCE_TARGETS}

print(f"\nGenerating balanced entries...", flush=True)
print(f"Targets: false_security +175+, body_horror +75+", flush=True)
print("", flush=True)

outf = open(OUTFILE, "a")

MAX_BATCHES = 300  # safety limit

while len(exhausted) < len(MODELS) and batch_num < MAX_BATCHES:
    available = [(p, m, n, t) for p, m, n, t in MODELS if f"{p}:{m}" not in exhausted]
    if not available:
        print("All models exhausted!", flush=True)
        break

    provider_name, model, short, tokens = available[batch_num % len(available)]
    client = providers[provider_name]

    # Pick fear type from weighted pool
    ft = random.choice(generation_pool)
    config = BALANCE_TARGETS[ft]
    scenario = random.choice(config["scenarios"])
    template = random.choice(config["prompt_templates"])
    prompt = template(scenario)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output ONLY valid JSONL. No markdown, no fences, no code blocks. Raw JSON objects, one per line. Every entry MUST have fear_type field."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.95,
            max_tokens=4000,
        )

        content = (resp.choices[0].message.content or "").strip()
        # Strip markdown fences
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
                    # Force correct fear_type for this batch
                    obj["fear_type"] = ft
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

        # Progress: show running totals
        progress = " | ".join(f"{k}:{v}" for k, v in generated_per_type.items())
        print(
            f"#{total_calls:3d} {short:12s} {ft:18s} "
            f"+{count:2d} new={total_new:4d} [{progress}]",
            flush=True,
        )

        time.sleep(1.5)

    except Exception as e:
        err = str(e)
        key = f"{provider_name}:{model}"
        errors_by_model[key] = errors_by_model.get(key, 0) + 1

        if any(x in err for x in ["429", "SetLimitExceeded", "insufficient", "quota", "suspended"]):
            print(f"  {short}: EXHAUSTED ({err[:60]})", flush=True)
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
print(f"\nMerging into unified dataset...", flush=True)
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

print(f"\n{'='*60}", flush=True)
print(f"BALANCING COMPLETE", flush=True)
print(f"  New entries this run: {total_new}", flush=True)
print(f"  Total unique entries: {len(all_entries)}", flush=True)
print(f"  API calls: {total_calls}", flush=True)
print(f"  Models exhausted: {len(exhausted)}/{len(MODELS)}", flush=True)
print(f"", flush=True)
print(f"  Distribution:", flush=True)
for ft, count in sorted(fear_counts.items(), key=lambda x: -x[1]):
    pct = count / len(all_entries) * 100
    print(f"    {ft:<22} {count:>5} ({pct:.1f}%)", flush=True)
print(f"", flush=True)
print(f"  Output: {UNIFIED}", flush=True)
print(f"{'='*60}", flush=True)
