#!/usr/bin/env python3
"""Continue entity generation from where we left off."""

import json
import time

from openai import OpenAI


client = OpenAI(
    api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    timeout=60.0,
)

ENTITY_TYPES = [
    (
        "unknown",
        "Unknown/unclassifiable entities that defy categorization, witnesses cannot describe coherently",
    ),
    (
        "flesh",
        "Flesh/body entities made of human tissue, amalgamations, growths that think, skin that moves",
    ),
    (
        "shadow",
        "Shadow/darkness entities that live in absence of light, shadows that move independently",
    ),
    ("mimic", "Mimic/shape entities that copy human form imperfectly, uncanny valley incarnate"),
    (
        "memetic",
        "Memetic/information entities that exist in knowledge, seeing them makes them real",
    ),
    ("temporal", "Temporal/time entities that exist across time, time loops, accumulated moments"),
    ("geometric", "Geometric/mathematical entities made of impossible shapes, higher dimensions"),
    ("nature", "Nature/corruption entities, forests that think, animals that behave as one"),
    ("parasitic", "Parasitic/symbiotic entities that attach to hosts, feed on emotions"),
    ("recursive", "Recursive/loop entities that exist in repetition, trap you in patterns"),
]

SYSTEM = "Output ONLY valid JSONL lines. No markdown, no code blocks."

total = 0
outf = open("data/dataset_entities.jsonl", "a")

for etype, description in ENTITY_TYPES:
    for batch in range(8):
        prompt = (
            f'Generate 3 horror ENTITY entries. Type: "{etype}". '
            f"{description}. "
            "JSON: instruction, input, output, fear_type. "
            "output = 150-300 words: appearance, behavior, origin, horror, encounter. "
            "UNIQUE entities only. Think SCP, Silent Hill, Junji Ito, Lovecraft. "
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
            time.sleep(2)
        except Exception as e:
            print(f"{etype} b{batch + 1}: ERR {str(e)[:60]}", flush=True)
            time.sleep(5)

outf.close()
print(f"\nTotal new entity entries: {total}")
