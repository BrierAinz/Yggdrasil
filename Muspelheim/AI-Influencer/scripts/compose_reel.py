#!/usr/bin/env python3
"""
Eir Reel Composer — Combine AnimateDiff clips into Reels/TikTok videos.

Strategy:
  1. Generate multiple short AnimateDiff clips (16 frames each)
  2. Concatenate with crossfade transitions
  3. Upscale to 1080x1920 (9:16 vertical)
  4. Add @eir.creates watermark
  5. Export as MP4 H.264

Requires: imageio, imageio-ffmpeg, Pillow
"""
import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = Path(__file__).resolve().parent.parent
FFMPEG = Path.home() / "comfy/ComfyUI/.venv/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"


def queue_prompt(workflow: dict) -> str:
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 300) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(resp.read())
            if prompt_id in history:
                return history[prompt_id]
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} timed out after {timeout}s")


def generate_animatediff_clip(prompt: str, neg_prompt: str, seed: int, output_dir: Path, vertical: bool = True) -> Path:
    """Generate a single AnimateDiff clip using ComfyUI API."""
    # Load workflow template (vertical for Reels, square for regular)
    wf_name = "eir_reel_vertical_api.json" if vertical else "eir_animatediff_api.json"
    with open(PROJECT_DIR / "workflows" / wf_name) as f:
        workflow = json.load(f)

    # Update prompts
    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = neg_prompt
    if seed:
        workflow["3"]["inputs"]["noise_seed"] = seed

    # Queue
    pid = queue_prompt(workflow)
    print(f"  Queued AnimateDiff: {pid[:8]}")

    # Wait
    history = wait_for_prompt(pid, timeout=300)
    outputs = history.get("outputs", {})

    # Find output
    comfy_out = Path.home() / "comfy/ComfyUI/output"
    for nid, nout in outputs.items():
        if "images" in nout:
            for img in nout["images"]:
                src = comfy_out / img["filename"]
                if src.exists():
                    dest = output_dir / f"clip_{seed:05d}_{img['filename']}"
                    shutil.copy2(src, dest)
                    print(f"  Saved: {dest.name}")
                    return dest

    raise FileNotFoundError(f"No output for {pid}")


def webp_to_frames(webp_path: Path) -> list:
    """Extract frames from animated WEBP."""
    from PIL import Image
    img = Image.open(webp_path)
    frames = []
    try:
        while True:
            frames.append(img.convert("RGB").copy())
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return frames


def create_reel(
    clip_paths: list,
    output_path: Path,
    transition_frames: int = 8,
    fps: int = 12,
    target_size: tuple = (1080, 1920),
    watermark: str = "@eir.creates",
    color_grade: str = None,
) -> Path:
    """Compose multiple clips into a single Reel with crossfade transitions."""
    import imageio
    import numpy as np

    # Collect all frames from all clips
    all_frame_sets = []
    for cp in clip_paths:
        frames = webp_to_frames(cp)
        all_frame_sets.append(frames)
        print(f"  Loaded {cp.name}: {len(frames)} frames")

    # Interleave with crossfade transitions
    final_frames = []
    for i, frame_set in enumerate(all_frame_sets):
        if i > 0:
            # Add crossfade transition
            prev_set = all_frame_sets[i - 1]
            for t in range(transition_frames):
                alpha = t / transition_frames
                # Blend last frame of prev clip with first frame of current
                prev_frame = prev_set[-1].resize(target_size, Image.LANCZOS)
                curr_frame = frame_set[0].resize(target_size, Image.LANCZOS)
                blended = Image.blend(prev_frame, curr_frame, alpha)
                final_frames.append(blended)

        # Add the clip frames
        for f in frame_set:
            resized = f.resize(target_size, Image.LANCZOS)
            final_frames.append(resized)

    # Apply color grading
    if color_grade == "warm":
        final_frames = [apply_warm(f) for f in final_frames]
    elif color_grade == "cool":
        final_frames = [apply_cool(f) for f in final_frames]
    elif color_grade == "moody":
        final_frames = [apply_moody(f) for f in final_frames]

    # Add watermark to last 30% of frames
    wm_start = int(len(final_frames) * 0.7)
    for i in range(wm_start, len(final_frames)):
        final_frames[i] = add_watermark(final_frames[i], watermark)

    # Write video
    import numpy as np
    writer = imageio.get_writer(
        str(output_path),
        fps=fps,
        codec="libx264",
        output_params=["-pix_fmt", "yuv420p"],
    )
    for frame in final_frames:
        writer.append_data(np.array(frame))
    writer.close()

    duration = len(final_frames) / fps
    print(f"  Reel: {len(final_frames)} frames, {duration:.1f}s at {fps}fps -> {output_path.name}")
    return output_path


def apply_warm(img: Image.Image) -> Image.Image:
    r, g, b = img.split()
    r = r.point(lambda x: min(255, x + 15))
    g = g.point(lambda x: min(255, x + 5))
    b = b.point(lambda x: max(0, x - 10))
    return Image.merge("RGB", (r, g, b))


def apply_cool(img: Image.Image) -> Image.Image:
    r, g, b = img.split()
    r = r.point(lambda x: max(0, x - 10))
    g = g.point(lambda x: min(255, x + 2))
    b = b.point(lambda x: min(255, x + 15))
    return Image.merge("RGB", (r, g, b))


def apply_moody(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(0.7)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Brightness(img).enhance(0.85)
    return img


def add_watermark(img: Image.Image, text: str = "@eir.creates") -> Image.Image:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
    ]
    font = None
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, 28)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (img.width - tw - 20, img.height - th - 20)
    draw.text((pos[0] + 1, pos[1] + 1), text, font=font, fill=(0, 0, 0, 80))
    draw.text(pos, text, font=font, fill=(255, 255, 255, 130))
    result = Image.alpha_composite(img.convert("RGBA"), overlay)
    return result.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="Eir Reel Composer")
    parser.add_argument("--mode", default="reel", choices=["reel", "generate", "compose"],
                        help="Mode: generate=only generate clips, compose=only compose existing, reel=both")
    parser.add_argument("--clips", type=int, default=3, help="Number of clips to generate/compose")
    parser.add_argument("--grade", default=None, choices=["warm", "cool", "moody"],
                        help="Color grading preset")
    parser.add_argument("--output", default=str(PROJECT_DIR / "outputs/reels"),
                        help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load content plan for prompts
    with open(PROJECT_DIR / "config/prompts/eir_content_plan.json") as f:
        plan = json.load(f)

    base_char = plan["prompt_templates"]["base_character"]
    quality = plan["prompt_templates"]["quality_tags"]
    neg = plan["negative_prompts"]["master"]

    # Video prompts — different moods/outfits for variety
    video_prompts = [
        (f"{base_char}, dark flowing robes, silver embroidery, northern lights aurora borealis, cinematic lighting, slow camera pan, {quality}", "aurora_reel"),
        (f"{base_char}, ornate dark plate armor, runic etchings, ethereal blue glow, temple interior, dramatic rim lighting, {quality}", "armor_reel"),
        (f"{base_char}, white fur-trimmed cloak, snowy forest, golden sunset, gentle snow, dreamy atmosphere, {quality}", "forest_reel"),
        (f"{base_char}, oversized cream knit sweater, cozy cabin, fireplace, warm firelight, soft focus, {quality}", "cozy_reel"),
        (f"{base_char}, ice crystal tiara, ceremonial robes, throne room, crystal pillars, dramatic lighting, {quality}", "ceremony_reel"),
        (f"{base_char}, dark leather hunting outfit, hooded cape, frozen tundra, mist, moody lighting, {quality}", "huntress_reel"),
    ]

    clips = []

    # Generate clips
    if args.mode in ("reel", "generate"):
        import random
        prompt_set = video_prompts[:args.clips]
        for i, (prompt, name) in enumerate(prompt_set):
            seed = random.randint(10000, 99999)
            print(f"\n[{i+1}/{len(prompt_set)}] Generating: {name}")
            try:
                clip = generate_animatediff_clip(prompt, neg, seed, output_dir)
                clips.append(clip)
            except Exception as e:
                print(f"  ERROR generating {name}: {e}")

    # Compose into reel
    if args.mode in ("reel", "compose") and clips:
        print(f"\nComposing reel from {len(clips)} clips...")
        reel_path = output_dir / f"eir_reel_{len(clips)}clips_{args.grade or 'normal'}.mp4"
        create_reel(
            clips,
            reel_path,
            transition_frames=8,
            fps=12,
            target_size=(1080, 1920),
            watermark="@eir.creates",
            color_grade=args.grade,
        )
        print(f"\nReel saved: {reel_path}")


if __name__ == "__main__":
    main()
