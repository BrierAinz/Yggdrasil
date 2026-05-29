#!/usr/bin/env python3
"""Generate remaining entity types. Waits for rate limit reset."""

import json
import sys
import time

from openai import OpenAI


client = OpenAI(
    api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    timeout=60.0,
)

ENTITY_TYPES = [
    (
        "flesh",
        "Flesh/body entities made of human tissue, amalgamations, growths that think, skin that moves",
    ),
    (
        "shadow",
        "Shadow/darkness entities, shadows that move independently, void creatures with weight",
    ),
    ("mimic", "Mimic/shape entities that copy human form imperfectly, uncanny valley incarnate"),
    (
        "memetic",
        "Memetic/information entities that exist in knowledge, seeing them makes them real",
    ),
    ("temporal", "Temporal/time entities across time, time loops, accumulated moments"),
    (
        "geometric",
        "Geometric/mathematical entities, impossible shapes, higher dimensions, fractal consciousness",
    ),
    (
        "nature",
        "Nature/corruption entities, forests that think, animals behave as one, biological networks",
    ),
    (
        "parasitic",
        "Parasitic entities that attach to hosts, feed on specific emotions, replace body parts",
    ),
    (
        "recursive",
        "Recursive/loop entities, repetition patterns, creatures in the space between iterations",
    ),
]

SYSTEM = "Output ONLY valid JSONL. No markdown, no code blocks."


def try_api():
    """Test if API is available."""
    try:
        client.chat.completions.create(
            model="deepseek-v4-flash-260425",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        return True
    except Exception as e:
        return "429" not in str(e)


# Wait for rate limit reset
print("Waiting for rate limit to reset...", flush=True)
for attempt in range(120):  # Max 2 hours wait
    if try_api():
        print("API available! Starting generation.", flush=True)
        break
    print(f"  Still rate limited. Waiting 60s... (attempt {attempt + 1})", flush=True)
    time.sleep(60)
else:
    print("ERROR: Rate limit did not reset after 2 hours.", flush=True)
    sys.exit(1)

# Generate
total = 0
outf = open("data/dataset_entities.jsonl", "a")

for etype, desc in ENTITY_TYPES:
    for batch in range(8):
        prompt = (
            f'Generate 3 horror ENTITY entries. Type: "{etype}". '
            f"{desc}. "
            "JSON: instruction, input, output, fear_type. "
            "output = 150-300 words: appearance, behavior, origin, horror, encounter. "
            "UNIQUE entities. Think SCP, Silent Hill, Junji Ito, Lovecraft. "
            "3 JSON lines only."
        )
        try:
            resp = client.chat.completions.create(
                model="deepseek-v4-flash-260425",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.98,
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
                        if len(obj["output"]) > 100:
                            obj["entity_type"] = etype
                            outf.write(json.dumps(obj, ensure_ascii=False) + "\n")
                            outf.flush()
                            count += 1
                            total += 1
                except json.JSONDecodeError:
                    pass
            print(f"{etype} b{batch + 1}: +{count} ({total})", flush=True)
            time.sleep(8)
        except Exception as e:
            err = str(e)[:60]
            if "429" in err:
                print(f"Rate limit hit again at {etype} b{batch + 1}. Waiting 5min...", flush=True)
                time.sleep(300)
            else:
                print(f"{etype} b{batch + 1}: ERR {err}", flush=True)
                time.sleep(10)

outf.close()
print(f"\nDONE: {total} new entity entries added to data/dataset_entities.jsonl")
