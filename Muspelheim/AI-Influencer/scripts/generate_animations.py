#!/usr/bin/env python3
"""Generate AnimateDiff videos for Eir AI Influencer using ComfyUI API."""
import json
import urllib.request
import time
import os
import shutil
import subprocess

COMFY_URL = "http://localhost:8188"
PROJECT_DIR = "/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer"
OUTPUT_DIR = f"{PROJECT_DIR}/outputs/videos_v2"
COMFY_OUTPUT = os.path.expanduser("~/comfy/ComfyUI/output")
FFMPEG = "/home/brierainz/comfy/ComfyUI/.venv/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"

# AnimateDiff video prompts for TikTok/Reels/Stories
VIDEO_PROMPTS = [
    {
        "name": "frost_breath",
        "positive": "eir_niflheimr, close-up portrait, silver-white hair with violet highlights, icy blue eyes, pale skin, breathing out frost mist, snowflakes falling around face, subtle head tilt, cinematic lighting, 8k, masterpiece, photorealistic",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, extra fingers, blurry, low quality, watermark, text, ugly, mutation, static, frozen",
        "seed": 42,
    },
    {
        "name": "hair_wind",
        "positive": "eir_niflheimr, portrait, silver-white hair flowing in wind, violet highlights, icy blue eyes, pale skin, looking at viewer, wind blowing hair, dramatic cinematic lighting, 8k, masterpiece, photorealistic",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, extra fingers, blurry, low quality, watermark, text, ugly, mutation, static",
        "seed": 1337,
    },
    {
        "name": "ice_crystals",
        "positive": "eir_niflheimr, close-up, icy blue eyes, ice crystals forming around hands, pale skin, silver-white hair, magical frost particles, glowing ice effects, fantasy atmosphere, 8k, masterpiece, photorealistic",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, extra fingers, blurry, low quality, watermark, text, ugly, mutation, static",
        "seed": 2048,
    },
    {
        "name": "snowfall",
        "positive": "eir_niflheimr, upper body portrait, silver-white hair with violet highlights, icy blue eyes, standing in snowfall, snowflakes drifting around, soft smile, winter landscape background, 8k, masterpiece, photorealistic",
        "negative": "cartoon, anime, 3d render, deformed, bad anatomy, extra fingers, blurry, low quality, watermark, text, ugly, mutation, static, frozen",
        "seed": 7777,
    },
]


def build_workflow(prompt_config: dict) -> dict:
    """Build AnimateDiff workflow for ComfyUI API."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"
            }
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "eir_niflheimr_v2_best.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8,
                "model": ["1", 0],
                "clip": ["1", 1]
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_config["positive"],
                "clip": ["2", 1]
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_config["negative"],
                "clip": ["2", 1]
            }
        },
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 16
            }
        },
        "10": {
            "class_type": "ADE_AnimateDiffLoaderWithContext",
            "inputs": {
                "model_name": "mm_sdxl_v10_beta.ckpt",
                "beta_schedule": "autoselect",
                "model": ["2", 0]
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": prompt_config["seed"],
                "steps": 20,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["10", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["8", 0]
            }
        },
        "4": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["1", 2]
            }
        },
        "5": {
            "class_type": "SaveAnimatedWEBP",
            "inputs": {
                "filename_prefix": f"eir_video_{prompt_config['name']}",
                "fps": 8,
                "lossless": False,
                "quality": 80,
                "method": "default",
                "images": ["4", 0]
            }
        }
    }


def wait_for_completion(prompt_id: str, timeout: int = 600) -> dict:
    """Wait for ComfyUI to finish processing."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{COMFY_URL}/history/{prompt_id}")
            ).read())
            if prompt_id in r:
                return r[prompt_id]
        except:
            pass
        time.sleep(3)
    return {}


def queue_prompt(workflow: dict) -> str:
    """Queue a workflow and return the prompt ID."""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY_URL}/prompt", data=data,
                                  headers={"Content-Type": "application/json"})
    response = urllib.request.urlopen(req)
    result = json.loads(response.read())
    return result["prompt_id"]


def convert_to_mp4(webp_path: str, mp4_path: str, fps: int = 8) -> bool:
    """Convert animated WEBP to MP4 using ffmpeg."""
    try:
        cmd = [
            FFMPEG, "-y", "-i", webp_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "23",
            "-vf", f"fps={fps},scale=512:512:flags=lanczos",
            "-an", mp4_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"  FFmpeg error: {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(COMFY_OUTPUT, exist_ok=True)

    results = []

    for i, prompt_config in enumerate(VIDEO_PROMPTS):
        print(f"\n[{i+1}/{len(VIDEO_PROMPTS)}] Generating: {prompt_config['name']}")

        workflow = build_workflow(prompt_config)

        try:
            prompt_id = queue_prompt(workflow)
            print(f"  Queued: {prompt_id}")
        except Exception as e:
            print(f"  Queue error: {e}")
            continue

        result = wait_for_completion(prompt_id)
        if not result:
            print(f"  TIMEOUT or ERROR")
            continue

        outputs = result.get("outputs", {})
        video_file = None
        for node_id, node_output in outputs.items():
            if "gifs" in node_output:
                for gif in node_output["gifs"]:
                    video_file = gif["filename"]
                    print(f"  Saved: {video_file}")
            if "images" in node_output:
                for img in node_output["images"]:
                    video_file = img["filename"]
                    print(f"  Saved: {video_file}")

        if video_file:
            src = os.path.join(COMFY_OUTPUT, video_file)
            dst_webp = os.path.join(OUTPUT_DIR, video_file)

            # Copy WEBP
            if os.path.exists(src):
                shutil.copy2(src, dst_webp)
                print(f"  Copied: {dst_webp}")

                # Convert to MP4
                mp4_name = video_file.replace(".webp", ".mp4")
                mp4_path = os.path.join(OUTPUT_DIR, mp4_name)
                if convert_to_mp4(src, mp4_path):
                    print(f"  Converted to MP4: {mp4_path}")
                    results.append({"name": prompt_config["name"], "webp": dst_webp, "mp4": mp4_path})
                else:
                    results.append({"name": prompt_config["name"], "webp": dst_webp, "mp4": None})
                    print(f"  MP4 conversion failed, keeping WEBP")
            else:
                print(f"  Source file not found: {src}")

        time.sleep(2)  # Brief pause between generations

    print(f"\n{'='*60}")
    print(f"VIDEO GENERATION COMPLETE")
    print(f"{'='*60}")
    for r in results:
        mp4_status = r['mp4'] if r['mp4'] else "WEBP only (MP4 failed)"
        print(f"  {r['name']}: {mp4_status}")
    print(f"\nTotal videos: {len(results)}")


if __name__ == "__main__":
    main()
