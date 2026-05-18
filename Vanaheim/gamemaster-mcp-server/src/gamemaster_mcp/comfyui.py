"""ComfyUI client — generates character card images via ComfyUI API.

Supports multiple generation modes:
- Character card (portrait for Caveduck/Tipsy profile)
- Reference sheet (full body with details)
- Album image (scene image for character gallery)
- NSFW variant (using NSFW checkpoint + CLIPSeg inpainting)

Uses the existing ComfyUI instance on localhost:8188 with RTX 3060 12GB VRAM.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("gamemaster.comfyui")

# ComfyUI API endpoint (WSL instance)
COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_OUTPUT = Path("/home/brierainz/comfy/ComfyUI/output")

# Available checkpoints on this machine (RTX 3060 12GB)
CHECKPOINTS = {
    "flux_dev_q8": {
        "filename": "flux1-dev-Q8_0.gguf",
        "type": "gguf",
        "loader": "UNETLoader",
        "config": {"weight_dtype": "default"},
        "vram_gb": 8.5,
        "description": "FLUX.1-dev Q8_0 GGUF — best quality, fits in 12GB VRAM",
    },
    "unstable_evolution_xxx": {
        "filename": "unstableEvolution_Fp8.safetensors",
        "type": "safetensors",
        "loader": "UNETLoader",
        "config": {"weight_dtype": "fp8_e4m3fn"},
        "vram_gb": 11.1,
        "description": "unStable Evolution FluXXX — NSFW, preserves faces with LoRAs",
    },
    "getphat_reality_xxx": {
        "filename": "getphatFLUXReality_v11SoftcoreFP8.safetensors",
        "type": "safetensors",
        "loader": "UNETLoader",
        "config": {"weight_dtype": "fp8_e4m3fn"},
        "vram_gb": 11.0,
        "description": "getphat FLUX Reality NSFW v11 — #1 rated for photorealistic skin",
    },
}

# Style presets for character cards
STYLE_PRESETS = {
    "dark_fantasy": {
        "positive": (
            "dark fantasy art, dramatic lighting, medieval atmosphere, "
            "intricate details, moody, ethereal glow, cinematic composition"
        ),
        "negative": "modern, casual, bright, cartoon, anime style, low quality, blurry",
        "steps": 28,
        "cfg": 3.5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 0.90,
    },
    "noir": {
        "positive": (
            "film noir style, dramatic shadows, monochrome accent, "
            "cigarette smoke, neon reflections, rain, trench coat, moody"
        ),
        "negative": "bright, colorful, cartoon, anime, low quality",
        "steps": 28,
        "cfg": 3.5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 0.88,
    },
    "anime": {
        "positive": (
            "high quality anime art, detailed, vibrant, "
            "clean lines, beautiful, professional illustration"
        ),
        "negative": "low quality, blurry, realistic photo, deformed, ugly",
        "steps": 30,
        "cfg": 4.0,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 0.85,
    },
    "photorealistic": {
        "positive": (
            "photorealistic, 8k, detailed skin texture, professional portrait, "
            "studio lighting, sharp focus, DSLR"
        ),
        "negative": "cartoon, anime, painting, illustration, low quality, blurry, deformed",
        "steps": 30,
        "cfg": 3.5,
        "sampler": "euler_ancestral",
        "scheduler": "normal",
        "denoise": 0.88,
    },
}

# Card dimensions for platforms
CARD_SIZES = {
    "caveduck_profile": {"width": 512, "height": 768},  # 2:3 portrait
    "caveduck_album": {"width": 768, "height": 512},  # 3:2 landscape
    "tipsy_profile": {"width": 512, "height": 768},
    "reference_sheet": {"width": 1024, "height": 1536},
}


async def queue_prompt(workflow: dict) -> str:
    """Queue a workflow to ComfyUI API and return the prompt_id."""
    async with httpx.AsyncClient(timeout=300) as client:
        # Get client_id
        resp = await client.get(f"{COMFYUI_URL}/system_stats")
        if resp.status_code != 200:
            raise ConnectionError(f"ComfyUI not reachable at {COMFYUI_URL}")

        payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
        resp = await client.post(f"{COMFYUI_URL}/prompt", json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"ComfyUI rejected prompt: {resp.text}")

        return resp.json()["prompt_id"]


async def wait_for_completion(prompt_id: str, timeout: int = 300) -> dict:
    """Poll ComfyUI for prompt completion. Returns output info."""
    async with httpx.AsyncClient(timeout=300) as client:
        for _ in range(timeout // 2):
            resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            if resp.status_code == 200:
                history = resp.json()
                if prompt_id in history:
                    status = history[prompt_id].get("status", {})
                    if status.get("completed", False) or status.get("status_str") == "success":
                        outputs = history[prompt_id].get("outputs", {})
                        return {"status": "completed", "outputs": outputs}
                    elif status.get("status_str") == "error":
                        return {"status": "error", "message": status}
            await asyncio.sleep(2)
        return {"status": "timeout", "message": f"Prompt {prompt_id} timed out after {timeout}s"}


def build_character_card_workflow(
    prompt: str,
    negative_prompt: str,
    checkpoint: str = "flux_dev_q8",
    style: str = "dark_fantasy",
    card_type: str = "caveduck_profile",
    seed: int | None = None,
) -> dict:
    """Build a ComfyUI workflow JSON for character card generation.

    Uses FLUX.1-dev Q8_0 GGUF by default (fits in 12GB VRAM).
    Falls back to basic KSampler + UNETLoader for compatibility.
    """
    import random

    if seed is None:
        seed = random.randint(0, 2**32 - 1)

    size = CARD_SIZES.get(card_type, CARD_SIZES["caveduck_profile"])
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["dark_fantasy"])
    ckpt = CHECKPOINTS.get(checkpoint, CHECKPOINTS["flux_dev_q8"])

    # Build full prompt with style
    full_positive = f"{prompt}, {style_config['positive']}"
    full_negative = style_config["negative"]

    if ckpt["type"] == "gguf":
        # GGUF workflow (FLUX.1-dev Q8_0)
        return {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": ckpt["filename"],
                    "weight_dtype": ckpt["config"].get("weight_dtype", "default"),
                },
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": full_positive,
                    "clip": ["4", 1],
                },
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": full_negative,
                    "clip": ["4", 1],
                },
            },
            "4": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": "clip_l.safetensors",
                    "clip_name2": "t5xxl_fp16.safetensors",
                    "type": "flux",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": size["width"],
                    "height": size["height"],
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": style_config["steps"],
                    "cfg": style_config["cfg"],
                    "sampler_name": style_config["sampler"],
                    "scheduler": style_config["scheduler"],
                    "denoise": style_config["denoise"],
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0],
                },
            },
            "7": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "ae.sft",
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["7", 0],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "gamemaster_card",
                    "images": ["8", 0],
                },
            },
        }
    else:
        # FP8/FP16 safetensors workflow
        return {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": ckpt["filename"],
                    "weight_dtype": ckpt["config"].get("weight_dtype", "fp8_e4m3fn"),
                },
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": full_positive,
                    "clip": ["4", 1],
                },
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": full_negative,
                    "clip": ["4", 1],
                },
            },
            "4": {
                "class_type": "DualCLIPLoader",
                "inputs": {
                    "clip_name1": "clip_l.safetensors",
                    "clip_name2": "t5xxl_fp16.safetensors",
                    "type": "flux",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": size["width"],
                    "height": size["height"],
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": style_config["steps"],
                    "cfg": style_config["cfg"],
                    "sampler_name": style_config["sampler"],
                    "scheduler": style_config["scheduler"],
                    "denoise": style_config["denoise"],
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0],
                },
            },
            "7": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "ae.sft",
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["7", 0],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "gamemaster_card",
                    "images": ["8", 0],
                },
            },
        }


async def generate_character_card(
    prompt: str,
    style: str = "dark_fantasy",
    checkpoint: str = "flux_dev_q8",
    card_type: str = "caveduck_profile",
    seed: int | None = None,
) -> dict[str, Any]:
    """Generate a character card image via ComfyUI.

    Args:
        prompt: Character description for image generation
        style: Style preset (dark_fantasy, noir, anime, photorealistic)
        checkpoint: Checkpoint to use (flux_dev_q8, unstable_evolution_xxx, getphat_reality_xxx)
        card_type: Card size format (caveduck_profile, caveduck_album, tipsy_profile)
        seed: Optional seed for reproducibility

    Returns:
        dict with status, prompt_id, output_path(s), and metadata
    """
    # Check ComfyUI is reachable
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{COMFYUI_URL}/system_stats")
            if resp.status_code != 200:
                return {"status": "error", "message": f"ComfyUI not reachable at {COMFYUI_URL}"}
    except Exception as e:
        return {"status": "error", "message": f"ComfyUI connection failed: {e}"}

    # Build and queue workflow
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["dark_fantasy"])
    workflow = build_character_card_workflow(
        prompt=prompt,
        negative_prompt=style_config["negative"],
        checkpoint=checkpoint,
        style=style,
        card_type=card_type,
        seed=seed,
    )

    try:
        prompt_id = await queue_prompt(workflow)
        logger.info(f"Queued ComfyUI prompt {prompt_id} for style={style} checkpoint={checkpoint}")
    except Exception as e:
        return {"status": "error", "message": f"Failed to queue prompt: {e}"}

    # Wait for completion
    result = await wait_for_completion(prompt_id, timeout=300)

    if result["status"] != "completed":
        return {
            "status": result["status"],
            "prompt_id": prompt_id,
            "message": result.get("message", ""),
        }

    # Extract output paths
    output_files = []
    for node_id, node_output in result["outputs"].items():
        if "images" in node_output:
            for img in node_output["images"]:
                output_files.append(
                    {
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "path": str(COMFYUI_OUTPUT / img.get("subfolder", "") / img["filename"]),
                    }
                )

    return {
        "status": "completed",
        "prompt_id": prompt_id,
        "checkpoint": checkpoint,
        "style": style,
        "card_type": card_type,
        "seed": seed,
        "output_files": output_files,
        "comfyui_url": COMFYUI_URL,
    }


async def get_available_checkpoints() -> dict[str, Any]:
    """List available checkpoints on the ComfyUI instance."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{COMFYUI_URL}/object_info/UNETLoader")
            if resp.status_code == 200:
                info = resp.json()
                available = info.get("UNETLoader", {}).get("input", {}).get("unet_name", [])
                return {"status": "ok", "checkpoints": available}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "ok", "checkpoints": list(CHECKPOINTS.keys())}
