#!/usr/bin/env python3
"""Generate horror entity entries via DeepSeek V4 Flash API."""

from openai import OpenAI
import json, time

client = OpenAI(
    api_key="ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113",
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    timeout=60.0,
)

ENTITY_TYPES = [
    ("lovecraftian", "Lovecraftian cosmic entities - incomprehensible geometry, non-Euclidean forms, things that drive madness by existing, ancient beyond time, indifference to humanity, vast scale, impossible biology"),
    ("junji_ito", "Junji Ito style entities - spiral obsession, body horror transformation, infection that spreads by observation, uncanny symmetry, things that should not be contorted, beauty turned grotesque, viral memetic horror"),
    ("unknown", "Unknown/unclassifiable entities - things that defy categorization, no folklore matches, witnesses cannot describe coherently, the more you understand the worse it gets, reality glitches around them"),
    ("flesh", "Flesh/body entities - things made of human tissue, amalgamations of bodies, growths that think, tumors with consciousness, skin that moves independently, teeth in wrong places, bones that restructure"),
    ("shadow", "Shadow/darkness entities - things that live in absence of light, shadows that move independently, darkness with weight and intent, things seen only in peripheral vision, entities made of void"),
    ("mimic", "Mimic/shape entities - things that copy human form imperfectly, faces that almost fit, voices that almost sound right, uncanny valley incarnate, doppelgangers with wrong details, the familiar made alien"),
    ("memetic", "Memetic/information entities - things that exist in knowledge, seeing them makes them real, words that contain consciousness, images that infect, concepts that are alive, thoughts that are parasites"),
    ("temporal", "Temporal/time entities - things that exist across time, echoes of future events, beings that live in time loops, entities made of accumulated moments, time itself as a predator"),
    ("geometric", "Geometric/mathematical entities - things made of impossible shapes, fractal consciousness, entities in higher dimensions, angles that hurt to observe, mathematics that bleeds"),
    ("nature", "Nature/corruption entities - nature wrong, forests that think, plants that grow in patterns, animals that behave as one, ecosystems with a single consciousness, biological networks with intent"),
    ("parasitic", "Parasitic/symbiotic entities - things that attach to hosts, entities that feed on specific emotions, creatures that replace body parts gradually, beings that need human suffering to survive"),
    ("recursive", "Recursive/loop entities - things that exist in repetition, entities that trap you in patterns, beings that are the same event recurring, creatures that exist in the space between iterations"),
]

SYSTEM = "Output ONLY valid JSONL lines. No markdown, no code blocks, no explanation."

total = 0
outf = open("data/dataset_entities.jsonl", "w")

for etype, description in ENTITY_TYPES:
    for batch in range(8):
        prompt = (
            f'Generate 3 horror ENTITY entries. Entity type: "{etype}". '
            f"Context: {description}. "
            "Each entry teaches an LLM to CREATE a new horror entity. "
            "JSON fields: instruction, input, output, fear_type, entity_type. "
            "The output field must be 150-300 words with: "
            "physical appearance, behavior, origin, what makes it terrifying, "
            "how the player encounters it. "
            "Make each entity UNIQUE. No vampires, zombies, werewolves. "
            "Think: SCP Foundation, Silent Hill, Junji Ito, Lovecraft. "
            "Output ONLY 3 JSON lines."
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
            print(f"{etype} b{batch+1}: +{count} ({total})", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"{etype} b{batch+1}: ERR {str(e)[:60]}", flush=True)
            time.sleep(5)

outf.close()
print(f"\nTotal entity entries: {total}")
