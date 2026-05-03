#!/usr/bin/env python3
"""
Eir Post-Processor — Add overlays, watermarks, color grading, and borders.

Transforms raw upscaled images into Instagram-ready content with:
  - @eir.creates watermark (bottom-right, subtle)
  - Optional color grading presets (warm, cool, moody, vivid)
  - Optional thin border (white or dark)
  - Story templates with text overlays
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from pathlib import Path
import argparse

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "outputs" / "final"


# ─── Color Grading Presets ─────────────────────────────────────────
def apply_warm(img: Image.Image) -> Image.Image:
    """Warm golden tone — like sunset lighting."""
    r, g, b = img.split()
    r = r.point(lambda x: min(255, x + 15))
    g = g.point(lambda x: min(255, x + 5))
    b = b.point(lambda x: max(0, x - 10))
    return Image.merge("RGB", (r, g, b))


def apply_cool(img: Image.Image) -> Image.Image:
    """Cool blue tone — winter/frost aesthetic."""
    r, g, b = img.split()
    r = r.point(lambda x: max(0, x - 10))
    g = g.point(lambda x: min(255, x + 2))
    b = b.point(lambda x: min(255, x + 15))
    return Image.merge("RGB", (r, g, b))


def apply_moody(img: Image.Image) -> Image.Image:
    """Dark, desaturated, high contrast — dramatic."""
    img = ImageEnhance.Color(img).enhance(0.7)  # Desaturate
    img = ImageEnhance.Contrast(img).enhance(1.3)  # Boost contrast
    img = ImageEnhance.Brightness(img).enhance(0.85)  # Slightly darker
    return img


def apply_vivid(img: Image.Image) -> Image.Image:
    """Punchy, saturated colors — eye-catching."""
    img = ImageEnhance.Color(img).enhance(1.4)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    return img


GRADES = {
    "warm": apply_warm,
    "cool": apply_cool,
    "moody": apply_moody,
    "vivid": apply_vivid,
}


def add_watermark(
    img: Image.Image,
    text: str = "@eir.creates",
    position: str = "bottom-right",
    opacity: int = 128,
    font_size: int = 36,
) -> Image.Image:
    """Add a subtle watermark to the image."""
    # Try to find a good font, fall back to default
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
    ]
    font = None
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate position
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = 30

    positions = {
        "bottom-right": (img.width - tw - margin, img.height - th - margin),
        "bottom-left": (margin, img.height - th - margin),
        "top-right": (img.width - tw - margin, margin),
        "top-left": (margin, margin),
        "center": ((img.width - tw) // 2, (img.height - th) // 2),
    }
    pos = positions.get(position, positions["bottom-right"])

    # Draw shadow + text
    shadow_offset = 2
    draw.text((pos[0] + shadow_offset, pos[1] + shadow_offset), text, font=font, fill=(0, 0, 0, opacity // 2))
    draw.text(pos, text, font=font, fill=(255, 255, 255, opacity))

    img_rgba = img.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


def add_border(img: Image.Image, width: int = 20, color: str = "white") -> Image.Image:
    """Add a border around the image."""
    border_color = (255, 255, 255) if color == "white" else (20, 20, 20)
    new_w = img.width + width * 2
    new_h = img.height + width * 2
    bordered = Image.new("RGB", (new_w, new_h), border_color)
    bordered.paste(img, (width, width))
    return bordered


def create_story_template(
    img: Image.Image,
    title: str = "",
    subtitle: str = "",
    style: str = "minimal",  # minimal, bold, frosted
) -> Image.Image:
    """Create an IG story template (1080x1920) with text overlay."""
    story_h = 1920
    target_w = 1080

    # Resize image to fill story width, center-crop height
    ratio = target_w / img.width
    new_h = int(img.height * ratio)
    img_resized = img.resize((target_w, new_h), Image.LANCZOS)

    if new_h > story_h:
        top = (new_h - story_h) // 2
        img_resized = img_resized.crop((0, top, target_w, top + story_h))
    else:
        # Image too short — create background and paste
        bg = img_resized.resize((target_w, story_h), Image.LANCZOS)
        # Apply heavy blur for background
        bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
        bg = ImageEnhance.Brightness(bg).enhance(0.5)
        top = (story_h - new_h) // 2
        bg.paste(img_resized, (0, top))
        img_resized = bg

    if not title and not subtitle:
        return img_resized

    # Add text overlay
    overlay = Image.new("RGBA", (target_w, story_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Find font
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/mnt/c/Windows/Fonts/arialbd.ttf",
    ]
    font_bold = None
    font_reg = None
    for fp in font_paths:
        if Path(fp).exists():
            try:
                font_bold = ImageFont.truetype(fp, 64)
                font_reg = ImageFont.truetype(fp, 40)
                break
            except Exception:
                continue
    if font_bold is None:
        font_bold = ImageFont.load_default()
        font_reg = ImageFont.load_default()

    if style == "minimal":
        # Clean text at bottom third
        y = int(story_h * 0.65)
        if title:
            draw.text((60, y), title, font=font_bold, fill=(255, 255, 255, 230))
            y += 80
        if subtitle:
            draw.text((60, y), subtitle, font=font_reg, fill=(255, 255, 255, 180))

    elif style == "bold":
        # Large centered text with shadow
        y = int(story_h * 0.35)
        if title:
            bbox = draw.textbbox((0, 0), title, font=font_bold)
            tw = bbox[2] - bbox[0]
            x = (target_w - tw) // 2
            # Shadow
            draw.text((x + 3, y + 3), title, font=font_bold, fill=(0, 0, 0, 200))
            draw.text((x, y), title, font=font_bold, fill=(255, 255, 255, 240))
            y += 90
        if subtitle:
            bbox = draw.textbbox((0, 0), subtitle, font=font_reg)
            tw = bbox[2] - bbox[0]
            x = (target_w - tw) // 2
            draw.text((x, y), subtitle, font=font_reg, fill=(255, 255, 255, 200))

    elif style == "frosted":
        # Semi-transparent bar across middle
        bar_y = int(story_h * 0.55)
        bar_h = 200
        draw.rectangle([(0, bar_y), (target_w, bar_y + bar_h)], fill=(0, 0, 0, 100))
        y = bar_y + 30
        if title:
            draw.text((60, y), title, font=font_bold, fill=(255, 255, 255, 230))
            y += 70
        if subtitle:
            draw.text((60, y), subtitle, font=font_reg, fill=(255, 255, 255, 200))

    img_rgba = img_resized.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


def main():
    parser = argparse.ArgumentParser(description="Eir Post-Processor")
    parser.add_argument("--input", required=True, help="Input directory or file")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--grade", default=None, choices=list(GRADES.keys()), help="Color grading preset")
    parser.add_argument("--watermark", action="store_true", help="Add @eir.creates watermark")
    parser.add_argument("--border", default=None, choices=["white", "black"], help="Add border")
    parser.add_argument("--story", action="store_true", help="Output as 1080x1920 story format")
    parser.add_argument("--story-title", default="", help="Story title text")
    parser.add_argument("--story-subtitle", default="", help="Story subtitle text")
    parser.add_argument("--story-style", default="minimal", choices=["minimal", "bold", "frosted"])
    parser.add_argument("--limit", type=int, default=0, help="Max images to process")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect input images
    input_path = Path(args.input)
    if input_path.is_file():
        images = [input_path]
    else:
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        images = sorted([f for f in input_path.iterdir() if f.suffix.lower() in exts])

    if args.limit:
        images = images[:args.limit]

    print(f"Eir Post-Processor — {len(images)} images")
    print(f"  Grade: {args.grade or 'none'}")
    print(f"  Watermark: {args.watermark}")
    print(f"  Border: {args.border or 'none'}")
    print(f"  Story: {args.story}")
    print()

    for i, img_path in enumerate(images):
        print(f"[{i+1}/{len(images)}] {img_path.name}")
        try:
            img = Image.open(img_path).convert("RGB")

            # 1. Color grading
            if args.grade:
                img = GRADES[args.grade](img)
                print(f"  + Grade: {args.grade}")

            # 2. Border
            if args.border:
                img = add_border(img, width=20, color=args.border)
                print(f"  + Border: {args.border}")

            # 3. Watermark
            if args.watermark:
                img = add_watermark(img)
                print(f"  + Watermark: @eir.creates")

            # 4. Story template
            if args.story:
                img = create_story_template(
                    img,
                    title=args.story_title,
                    subtitle=args.story_subtitle,
                    style=args.story_style,
                )
                print(f"  + Story template ({args.story_style})")

            # Save
            suffix = ""
            if args.grade:
                suffix += f"_{args.grade}"
            if args.border:
                suffix += f"_brd-{args.border}"
            if args.watermark:
                suffix += "_wm"
            if args.story:
                suffix += "_story"

            # Determine output format (story = JPG for smaller size)
            if args.story:
                out_file = out_dir / f"{img_path.stem}{suffix}.jpg"
                img.save(out_file, "JPEG", quality=95, optimize=True)
            else:
                out_file = out_dir / f"{img_path.stem}{suffix}.jpg"
                img.save(out_file, "JPEG", quality=95, optimize=True)

            print(f"  -> {out_file.name} ({img.width}x{img.height})")

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone! {len(images)} images processed -> {out_dir}")


if __name__ == "__main__":
    main()
