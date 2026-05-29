"""
Lilith - Image Processor Tool (Phase 3)
Connects to ComfyUI API for image generation and editing
"""

import base64
import json
import os
import random
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, str(project_root))

# Note: No BaseTool base class needed - tools just implement execute()
import logging

logger = logging.getLogger("ImageProcessor")


class ImageProcessor:
    """
    Image generation and processing via ComfyUI API
    Supports: text2image, image2image, upscaling, inpainting
    """

    def __init__(self, base_url: str = "http://localhost:8188"):
        self.base_url = base_url
        self.client_id = str(uuid.uuid4())
        logger.info(f"ImageProcessor initialized (client_id: {self.client_id[:8]}...)")

    def _get_metadata(self) -> dict:
        """Return tool metadata as a dict (registered via ToolRegistry)"""
        return {
            "name": "ImageProcessor",
            "description": "Generate and edit images using ComfyUI (Stable Diffusion)",
            "category": "media_processing",
            "risk": "low",
            "requires_approval": True,
        }

    def execute(self, parameters: dict) -> str:
        """Execute image generation workflow"""
        try:
            prompt = parameters["prompt"]
            workflow = parameters.get("workflow", "text2image")
            output_path = parameters.get("output_path", "workspace/generated_image.png")

            logger.info(
                f"Image generation: {workflow} workflow, prompt='{prompt[:50]}...'"
            )

            # Check ComfyUI server health
            if not self._check_server():
                return "ERROR: ComfyUI server not running at http://localhost:8188. Please start it first."

            # Load and prepare workflow
            workflow_json = self._get_workflow_template(workflow)
            self._update_workflow(workflow_json, parameters)

            # Queue prompt
            prompt_id = self._queue_prompt(workflow_json)
            if not prompt_id:
                return "ERROR: Failed to queue prompt"

            logger.info(f"Prompt queued: {prompt_id[:8]}...")

            # Wait for completion
            result = self._wait_for_completion(prompt_id, timeout=120)
            if result["status"] == "error":
                return f"ERROR: {result['message']}"

            # Get generated image
            image_data = self._get_generated_image(result["output_node"])
            if not image_data:
                return "ERROR: Failed to retrieve generated image"

            # Save image
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_data)

            file_size = len(image_data) / 1024
            logger.info(f"Image saved: {output_path} ({file_size:.1f} KB)")

            return f"âœ“ Image generated successfully:\n  Path: {output_path}\n  Size: {file_size:.1f} KB\n  Prompt: {prompt[:60]}..."

        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            return f"ERROR: {str(e)}"

    def _check_server(self) -> bool:
        """Check if ComfyUI server is running"""
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _get_workflow_template(self, workflow: str) -> dict:
        """Get pre-configured workflow template"""
        templates = {
            "text2image": {
                "3": {
                    "inputs": {
                        "seed": 0,
                        "steps": 20,
                        "cfg": 8.0,
                        "sampler_name": "dpmpp_2m",
                        "scheduler": "normal",
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                    "class_type": "KSampler",
                },
                "4": {
                    "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
                    "class_type": "CheckpointLoaderSimple",
                },
                "5": {
                    "inputs": {"width": 512, "height": 512, "batch_size": 1},
                    "class_type": "EmptyLatentImage",
                },
                "6": {
                    "inputs": {"text": "", "clip": ["4", 1]},
                    "class_type": "CLIPTextEncode",
                },
                "7": {
                    "inputs": {"text": "", "clip": ["4", 1]},
                    "class_type": "CLIPTextEncode",
                },
                "8": {
                    "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
                    "class_type": "VAEDecode",
                },
                "9": {
                    "inputs": {"filename_prefix": "Lilith", "images": ["8", 0]},
                    "class_type": "SaveImage",
                },
            }
        }

        # Deep copy template
        import copy

        return copy.deepcopy(templates.get(workflow, templates["text2image"]))

    def _update_workflow(self, workflow: dict, parameters: dict):
        """Update workflow with user parameters"""
        # Update positive prompt
        workflow["6"]["inputs"]["text"] = parameters["prompt"]

        # Update negative prompt
        workflow["7"]["inputs"]["text"] = parameters.get(
            "negative_prompt", "blurry, low quality"
        )

        # Update dimensions
        workflow["5"]["inputs"]["width"] = parameters.get("width", 512)
        workflow["5"]["inputs"]["height"] = parameters.get("height", 512)

        # Update steps
        workflow["3"]["inputs"]["steps"] = parameters.get("steps", 20)

        # Update seed
        seed = parameters.get("seed", -1)
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)
        workflow["3"]["inputs"]["seed"] = seed

    def _queue_prompt(self, workflow: dict) -> Optional[str]:
        """Queue workflow and return prompt_id"""
        try:
            payload = {"client_id": self.client_id, "prompt": workflow}

            response = requests.post(
                f"{self.base_url}/prompt", json=payload, timeout=10
            )
            response.raise_for_status()

            return response.json().get("prompt_id")
        except Exception as e:
            logger.error(f"Failed to queue prompt: {e}")
            return None

    def _wait_for_completion(self, prompt_id: str, timeout: int = 120) -> dict:
        """Wait for generation to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/history/{prompt_id}", timeout=5
                )
                if response.status_code == 200:
                    history = response.json()
                    if prompt_id in history:
                        status = history[prompt_id].get("status", {})
                        if status.get("completed"):
                            return {
                                "status": "success",
                                "output_node": "9",  # SaveImage node
                            }
                        elif status.get("status_str") == "error":
                            return {"status": "error", "message": "Generation failed"}
            except Exception as e:
                logger.warning(f"Error checking status: {e}")

            time.sleep(0.5)

        return {"status": "error", "message": f"Timeout after {timeout}s"}

    def _get_generated_image(self, output_node: str) -> Optional[bytes]:
        """Get generated image data from ComfyUI"""
        try:
            # Get prompt history to find output image
            response = requests.get(
                f"{self.base_url}/view?filename=Lilith_00001_.png&type=output",
                timeout=10,
            )

            if response.status_code == 200:
                return response.content

            # Fallback: check output folder directly
            output_paths = [
                "ComfyUI/output/Lilith_00001_.png",
                "output/Lilith_00001_.png",
                "../ComfyUI/output/Lilith_00001_.png",
            ]

            for path in output_paths:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        return f.read()

            logger.error("Could not find generated image")
            return None

        except Exception as e:
            logger.error(f"Failed to get image: {e}")
            return None


# ============================================================================
# TEST (Requires ComfyUI running and model loaded)
# ============================================================================


def test_image_processor():
    """Simple test for ImageProcessor"""
    print("TEST IMAGE PROCESSOR")
    print("=" * 60)

    tool = ImageProcessor()

    # Check server
    print("\n1. Checking ComfyUI server...")
    if not tool._check_server():
        print("   [SKIP] ComfyUI not running. Start it first:")
        print("   python main.py --listen --port 8188")
        return False

    print("   [OK] ComfyUI server is running")

    # Check for model
    print("\n2. Checking for Stable Diffusion model...")
    import glob

    model_files = glob.glob("ComfyUI/models/checkpoints/*.ckpt") + glob.glob(
        "ComfyUI/models/checkpoints/*.safetensors"
    )

    if not model_files:
        print("   [WARN] No model found in ComfyUI/models/checkpoints/")
        print("   Please download v1-5-pruned-emaonly.ckpt")
        return False

    print(f"   [OK] Found {len(model_files)} model(s)")

    # Quick test (would take ~30 seconds)
    print("\n3. Ready for generation test")
    print(
        "   Use: tool.execute({prompt: 'a test image', width: 256, height: 256, steps: 10})"
    )

    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_image_processor()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
