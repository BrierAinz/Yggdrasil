"""
Lilith - ComfyUI Workflow Templates
Pre-built workflows for common image generation tasks
"""

import copy
from typing import Any, Dict


class ComfyWorkflows:
    """
    Collection of pre-built ComfyUI workflows
    """

    @staticmethod
    def get_text2image() -> Dict[str, Any]:
        """Basic text to image generation"""
        return {
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

    @staticmethod
    def get_upscale() -> Dict[str, Any]:
        """Image upscaling workflow"""
        # Simplified upscale workflow
        workflow = ComfyWorkflows.get_text2image()

        # Add upscaling nodes
        workflow["10"] = {
            "inputs": {"upscale_model": "RealESRGAN_x4plus.pth", "image": ["8", 0]},
            "class_type": "ImageUpscaleWithModel",
        }

        # Update save node to use upscaled image
        workflow["9"]["inputs"]["images"] = ["10", 0]

        return workflow

    @staticmethod
    def get_image2image() -> Dict[str, Any]:
        """Image to image transformation"""
        workflow = ComfyWorkflows.get_text2image()

        # Replace EmptyLatentImage with ImageLatentEncode
        workflow["5"] = {
            "inputs": {"pixels": ["10", 0], "vae": ["4", 2]},  # From LoadImage node
            "class_type": "VAEEncode",
        }

        # Add LoadImage node
        workflow["10"] = {
            "inputs": {"image": "input_image.png"},
            "class_type": "LoadImage",
        }

        return workflow

    @staticmethod
    def get_variations(prompt: str, count: int = 4) -> Dict[str, Any]:
        """Generate multiple variations of same prompt"""
        base_workflow = ComfyWorkflows.get_text2image()

        # Update batch size
        base_workflow["5"]["inputs"]["batch_size"] = count
        base_workflow["6"]["inputs"]["text"] = prompt

        return base_workflow

    @staticmethod
    def get_quick_demo() -> Dict[str, Any]:
        """Fast generation for demos (reduced steps)"""
        workflow = ComfyWorkflows.get_text2image()
        workflow["3"]["inputs"]["steps"] = 10
        workflow["5"]["inputs"]["width"] = 256
        workflow["5"]["inputs"]["height"] = 256
        return workflow


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    print("ComfyWorkflows Demo")
    print("=" * 50)

    workflows = ComfyWorkflows()

    text2img = workflows.get_text2image()
    print(f"Text2Image nodes: {len(text2img)}")
    print(f"Sampler steps: {text2img['3']['inputs']['steps']}")
    print(
        f"Dimensions: {text2img['5']['inputs']['width']}x{text2img['5']['inputs']['height']}"
    )

    upscale = workflows.get_upscale()
    print(f"\nUpscale with {len(upscale)} nodes")

    demo = workflows.get_quick_demo()
    print(
        f"\nQuick demo: {demo['3']['inputs']['steps']} steps, {demo['5']['inputs']['width']}x{demo['5']['inputs']['height']}"
    )
