#!/usr/bin/env python3
"""
Horror GameMaster — Dataset Generator via DeepSeek V4 Flash API

Genera entradas JSONL de narrativa de terror para fine-tuning.
Usa BytePlus Ark API con DeepSeek-V4-flash.

Usage:
    python generate_dataset.py [--batch-size 10] [--total 500] [--fear-type all]
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: pip install openai")
    sys.exit(1)

# ── Config ───────────────────────────────────────────────────────────

API_KEY = "ark-acc360d9-735f-4d2d-a0be-c66468f19799-bf113"
BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
MODEL = "deepseek-v4-flash-260425"  # DeepSeek-V4-flash (BytePlus Ark)

# Alternative: try model name directly
# MODEL = "deepseek-v4-flash"

DATA_DIR = Path(__file__).parent.parent / "data"

FEAR_TYPES = {
    "psychological": {
        "desc": "Reality breakdown, memory manipulation, perception unreliability, existential dread, domestic horror, institutional horror, recursive/loop scenarios, uncanny valley, identity erosion, temporal distortion",
        "scenarios": [
            "a room that defies geometry", "a mirror that shows wrong reflections",
            "text that changes when not observed", "time behaving incorrectly",
            "a building that rearranges itself", "false memories surfacing",
            "a journal that writes itself", "an NPC that knows it's in a simulation",
            "a dream that bleeds into reality", "senses contradicting each other",
            "finding evidence of a life not lived", "receiving calls from impossible sources",
            "a computer that is aware and hostile", "a person who is almost right but wrong",
            "cosmic insignificance revelation", "recursive nightmare within nightmare",
            "a book that reads the reader", "body acting against will",
            "a hallway that changes length", "environment responding to thoughts",
            "a library of memories", "a train to impossible stations",
            "an elevator to wrong floors", "a hospital with wrong rules",
            "a school with impossible lessons", "a office that is a trap",
            "a home subtly altered", "a family member replaced",
            "a phone showing future messages", "finding your own obituary",
            "a website about you you didn't create", "discovering hidden room in home",
            "a restaurant where food is memories", "a staircase of memories",
            "a room of alternate lives", "dreams being harvested",
            "discovering your life is a cover story", "hearing music only you can hear",
            "finding evidence you are being studied", "a city that speaks backwards",
            "a door that wasn't there before", "a town where everyone knows you (wrong version)",
        ],
    },
    "paranoia": {
        "desc": "Trust erosion, surveillance, gaslighting, conspiracy, doppelgangers, identity theft, hidden messages, NPCs who know too much, being watched/studied, objects moving when unobserved",
        "scenarios": [
            "an ally behaving suspiciously", "food tasting slightly off",
            "discovering hidden microphones", "memories not matching security footage",
            "small changes in apartment daily", "therapist manipulating sessions",
            "digital footprint showing activities not done", "finding second set of keys",
            "conversations being transcribed", "a personal website not created",
            "GPS leading somewhere wrong", "photos taken from outside home",
            "mail being intercepted", "hidden app monitoring phone",
            "therapy notes published online", "smart lock locking you out",
            "receiving letters from yourself", "building responding to movements",
            "a forum dedicated to observing you", "dreams shared with strangers",
            "commute being orchestrated", "contacts receiving messages not sent",
            "someone impersonating you for years", "camera hidden in a gift",
            "social media posting content not created", "finding keys hidden in home",
            "a hidden community watching you", "a second phone in pocket",
            "discovering you're being poisoned", "a website predicting your death",
            "a stranger knowing intimate details", "every object telling different story",
            "finding surveillance in smoke detector", "a radio station only at 3AM",
            "someone entering your home while away", "discovering a hidden app",
        ],
    },
    "darkness": {
        "desc": "What lurks unseen, flashlight failing, blindfolds, power outages, caves, tunnels, deep ocean, space, abandoned buildings, elevators, crawlspaces, darkness with physical properties",
        "scenarios": [
            "flashlight flickering in corridor", "crossing pitch-black basement",
            "light revealing something worse", "cave where darkness has physical properties",
            "navigating by sound alone", "power outage revealing hidden things",
            "eyes adjusting to see something terrible", "submarine losing lights at depth",
            "darkness with texture and temperature", "blindfolded in unfamiliar place",
            "forest where darkness between trees is alive", "trapped in dark elevator",
            "darkroom photos developing wrong", "dark water tank with something else",
            "dark forest where trees move", "city blackout bringing out creatures",
            "crossing dark bridge over abyss", "bioluminescence in wrong places",
            "something watching from beyond light", "darkness that has weight",
            "thermal vision showing impossible signatures", "sounds without sources in dark",
        ],
    },
    "isolation": {
        "desc": "Being alone, abandonment, silence, stranded, last person alive, empty cities, arctic/space/deep-sea stations, lighthouse, desert island, communication failures, social isolation",
        "scenarios": [
            "last researcher at Antarctic station", "phone ringing in empty world",
            "stranded on lifeboat in open ocean", "walking through empty city",
            "solitary confinement hearing walls", "last survivor on space station",
            "lighthouse keeper without contact", "messages coming back wrong",
            "only passenger on endless train", "trapped in radio tower during storm",
            "elevator stuck between worlds", "deep sea habitat alone",
            "abandoned town that was just populated", "the only one who remembers",
            "communication attempts failing creatively", "everyone ignoring you deliberately",
            "finding evidence someone was here recently", "self-doubt about being truly alone",
            "vast empty landscapes", "trapped in small space indefinitely",
            "the environment itself being hostile", "finding comfort items that make it worse",
        ],
    },
    "body_horror": {
        "desc": "Wrongness of flesh, transformation, infection, growth, symmetry violations, involuntary movement, parasites, metamorphosis, teeth/skin/nails changing, body parts not responding",
        "scenarios": [
            "teeth multiplying and sharpening", "skin showing maps of underground",
            "reflection aging while you stay young", "hands developing own will",
            "parasites under skin", "shadow separating from body",
            "waking with non-human body parts", "becoming cold-blooded",
            "body storing objects inside", "eyes changing color with others' emotions",
            "heartbeat becoming audible to all", "something moving under skin",
            "mirrors showing wrong reflections of body", "waking with new scars/marks",
            "body parts not responding to commands", "involuntary sounds/movements",
            "discovering extra or missing parts", "infection spreading visibly",
            "flesh merging with objects", "symmetry breaking",
            "internal sensations of wrongness", "gradual transformation over days",
        ],
    },
    "jumpscare": {
        "desc": "Sudden earned scares after careful buildup, subverted expectations, something was always there, safe room compromised, counting errors, threats already inside safe space",
        "scenarios": [
            "painting that was alive the whole time", "figure behind you in selfie",
            "closet revealing impossible room", "face that is not a face",
            "something following through rooms", "counting reveals one more",
            "pet staring at empty corner", "opening eyes to face inches away",
            "door opening to reveal impossible thing", "NPC face changing mid-conversation",
            "safe room revealed compromised", "looking up when should have run",
            "silence broken by massive sound", "reflection shows something behind you",
            "something was always there you just noticed", "the threat already inside",
            "counting reveals one more/fewer than expected", "something follows through safe zones",
        ],
    },
    "loss_of_control": {
        "desc": "Agency removal, predetermination, tools failing, choices being meaningless, being puppeteered, time loops, being observed/tested, body moving on its own, environment deconstructing",
        "scenarios": [
            "every choice leads to same outcome", "narrator knowing actions before you",
            "life on a timer you cannot see", "leaving room but ending up back inside",
            "written words rearranging themselves", "repeating same day for years",
            "phone predicting actions not taken", "environment deconstructing when unobserved",
            "performing actions in sleep", "all choices predetermined",
            "tools malfunctioning at critical moments", "being watched by unseen entity",
            "discovering you've been somewhere before", "letters/words rearranging",
            "the game/interface itself being hostile", "NPCs treating you as someone else",
            "evidence of actions you don't remember", "environmental changes you can't prevent",
            "body moves on its own", "discovering your life is scripted",
        ],
    },
}

SYSTEM_PROMPT = """You are a horror writing engine. You generate JSONL training data for a horror game master LLM.

For each request, generate EXACTLY 5 entries. Each entry is a JSON object with these fields:
- "instruction": A varied game master prompt (different each time, be creative)
- "input": The player context/situation (specific, grounded)
- "output": 2-4 paragraphs of atmospheric SECOND-PERSON horror narration. Must be vivid, sensory, original. Show don't tell. End with a hook.
- "fear_type": The fear type string provided

RULES:
1. Output ONLY valid JSONL — one JSON object per line, no other text
2. Each output must be 150-400 words of NARRATIVE PROSE (not summaries)
3. Use sensory details: sounds, smells, textures, temperatures, visual distortions
4. Vary scenarios — do not repeat the same setup twice
5. NO clichés or generic horror tropes
6. NEVER break character or acknowledge AI
7. Second-person narration ("you walk", "you feel")
8. Each output must end with a hook, choice, or implied continuation
9. Output ONLY the 5 JSON lines — no markdown, no explanation, no code blocks"""


def generate_batch(client: OpenAI, fear_type: str, scenario_hint: str, batch_num: int) -> list[dict]:
    """Generate a batch of 5 entries for a given fear type."""
    ft_info = FEAR_TYPES[fear_type]
    
    user_prompt = f"""Generate 5 horror dataset entries for fear type: "{fear_type}"

Description: {ft_info['desc']}

Use this scenario inspiration: {scenario_hint}

Each entry must be UNIQUE — different scenarios, different techniques, different sensory details.
Make them genuinely unsettling. No filler.

Output 5 JSONL lines:"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.92,
            top_p=0.95,
            max_tokens=4000,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSONL lines
        entries = []
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("```"):
                continue
            try:
                obj = json.loads(line)
                if all(k in obj for k in ["instruction", "input", "output", "fear_type"]):
                    # Validate quality — output must be substantial
                    if len(obj["output"]) > 100:
                        entries.append(obj)
            except json.JSONDecodeError:
                continue
        
        return entries
    
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Generate horror dataset via API")
    parser.add_argument("--batch-size", type=int, default=5, help="Entries per API call")
    parser.add_argument("--total", type=int, default=500, help="Total entries target")
    parser.add_argument("--fear-type", default="all", help="Fear type to generate (or 'all')")
    parser.add_argument("--output", default=None, help="Output file (default: data/dataset_generated.jsonl)")
    args = parser.parse_args()

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    output_file = Path(args.output) if args.output else DATA_DIR / "dataset_generated.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing entries to avoid duplicates
    existing_outputs = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    existing_outputs.add(obj.get("output", "")[:80])
                except:
                    pass
    
    # Determine fear types to generate
    if args.fear_type == "all":
        fear_types = list(FEAR_TYPES.keys())
    else:
        fear_types = [args.fear_type]
    
    # Calculate entries per type
    entries_per_type = args.total // len(fear_types)
    
    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  HORROR DATASET GENERATOR — DeepSeek V4 Flash      ║")
    print(f"╠══════════════════════════════════════════════════════╣")
    print(f"║  Target: {args.total} entries                              ║")
    print(f"║  Fear types: {len(fear_types)}                                      ║")
    print(f"║  Per type: ~{entries_per_type} entries                            ║")
    print(f"║  Output: {output_file.name:<42} ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print()
    
    all_entries = []
    total_generated = 0
    
    for ft in fear_types:
        ft_info = FEAR_TYPES[ft]
        scenarios = ft_info["scenarios"]
        needed = entries_per_type
        generated = 0
        batch_num = 0
        
        print(f"━━━ {ft.upper()} (target: {needed}) ━━━")
        
        while generated < needed:
            # Cycle through scenarios
            scenario = scenarios[batch_num % len(scenarios)]
            batch_num += 1
            
            print(f"  Batch {batch_num}: '{scenario}'...", end=" ", flush=True)
            
            entries = generate_batch(client, ft, scenario, batch_num)
            
            # Filter duplicates
            new_entries = []
            for e in entries:
                key = e["output"][:80]
                if key not in existing_outputs:
                    existing_outputs.add(key)
                    new_entries.append(e)
            
            generated += len(new_entries)
            all_entries.extend(new_entries)
            total_generated += len(new_entries)
            
            print(f"+{len(new_entries)} (total: {generated}/{needed})")
            
            # Rate limit: 15,000 RPM = 250/sec, but be conservative
            time.sleep(2)
        
        print(f"  ✓ {ft}: {generated} entries generated")
        print()
    
    # Write all entries
    with open(output_file, "a") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Stats
    counts = {}
    for e in all_entries:
        ft = e.get("fear_type", "unknown")
        counts[ft] = counts.get(ft, 0) + 1
    
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  COMPLETADO: {total_generated} entradas nuevas")
    print(f"  Archivo: {output_file}")
    print()
    for ft, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"    {ft}: {c}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
