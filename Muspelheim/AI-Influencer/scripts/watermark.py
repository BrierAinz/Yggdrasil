#!/usr/bin/env python3
"""
Eir Watermark — Subtle watermark overlay for content protection
================================================================
Adds a visible + invisible watermark to images.
"""

import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
except ImportError:
    print("✗ Pillow not installed. Run: pip install Pillow")
    raise

try:
    import tomllib
except ImportError:
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).parent.parent


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "generation.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def add_watermark(
    input_path: str,
    output_path: str = None,
    text: str = "@eir.creates",
    opacity: int = 153,
    position: str = "bottom_right",
    font_size: int = 16,
):
    """Add a subtle visible watermark to an image."""
    img = Image.open(input_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a nice font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Calculate position
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 15

    positions = {
        "bottom_right": (img.width - text_w - margin, img.height - text_h - margin),
        "bottom_left": (margin, img.height - text_h - margin),
        "bottom_center": ((img.width - text_w) // 2, img.height - text_h - margin),
    }
    pos = positions.get(position, positions["bottom_right"])

    # Draw watermark with specified opacity
    draw.text(pos, text, fill=(255, 255, 255, opacity), font=font)

    # Composite and convert back to RGB
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")

    if output_path is None:
        p = Path(input_path)
        output_path = str(p.parent / f"{p.stem}_wm{p.suffix}")

    result.save(output_path, quality=95)
    print(f"  ✓ Watermarked: {output_path}")
    return output_path


def batch_watermark(input_dir: str, output_dir: str = None):
    """Add watermark to all images in a directory."""
    input_path = Path(input_dir)
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path / "watermarked"

    config = load_config()
    wm_config = config.get("watermark", {})

    count = 0
    for img_file in input_path.glob("*.png"):
        out = output_path / img_file.name
        add_watermark(
            str(img_file),
            str(out),
            text=wm_config.get("text", "@eir.creates"),
            opacity=wm_config.get("opacity", 153),
        )
        count += 1

    for img_file in input_path.glob("*.jpg"):
        out = output_path / img_file.name
        add_watermark(
            str(img_file),
            str(out),
            text=wm_config.get("text", "@eir.creates"),
            opacity=wm_config.get("opacity", 153),
        )
        count += 1

    print(f"  ◆ Batch complete: {count} images watermarked")


def main():
    parser = argparse.ArgumentParser(description="Eir Watermark Tool")
    parser.add_argument("--input", required=True, help="Input image or directory")
    parser.add_argument("--output", help="Output image or directory")
    parser.add_argument("--text", default="@eir.creates", help="Watermark text")
    parser.add_argument("--opacity", type=int, default=153, help="Opacity 0-255")
    parser.add_argument("--batch", action="store_true", help="Process entire directory")
    args = parser.parse_args()

    if args.batch:
        batch_watermark(args.input, args.output)
    else:
        add_watermark(args.input, args.output, args.text, args.opacity)


if __name__ == "__main__":
    main()