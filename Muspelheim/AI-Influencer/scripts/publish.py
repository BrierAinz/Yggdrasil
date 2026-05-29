#!/usr/bin/env python3
"""
Eir Content Publisher — CLI tool for managing and publishing @eir.creates content.

Platforms:
  - X/Twitter: via xurl CLI (requires auth setup first)
  - Instagram: manual (instagrapi available but requires IG session)
  - TikTok: manual upload required

Usage:
  python publish.py status                     # Show content inventory
  python publish.py calendar                   # Show content calendar
  python publish.py post-x <image> <text>      # Post to X/Twitter
  python publish.py post-x-batch [--dry-run]   # Batch post all content to X
  python publish.py generate-captions          # Generate caption text from content plan
  python publish.py schedule                   # Show optimal posting times
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_DIR / "outputs"
CONTENT_PLAN = PROJECT_DIR / "config" / "prompts" / "eir_content_plan.json"
STATE_FILE = PROJECT_DIR / "config" / "publish_state.json"
VOICE_FILE = PROJECT_DIR / "docs" / "VOICE_AND_PERSONALITY.md"
HASHTAG_FILE = PROJECT_DIR / "docs" / "HASHTAG_STRATEGY.md"

# ─── State Management ─────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"x_posts": 0, "ig_posts": 0, "ig_stories": 0, "tiktok_posts": 0,
            "last_post": None, "published": [], "created": datetime.now().isoformat()}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ─── Content Inventory ────────────────────────────────────────────────────────

def scan_outputs() -> dict:
    """Scan all output directories and return inventory."""
    inventory = {}
    for subdir in ["feed_batch_v2", "content_bank_v2", "stories_highlights_v2",
                   "profile_assets", "profile_variations", "videos_v2"]:
        dir_path = OUTPUTS_DIR / subdir
        if dir_path.exists():
            files = list(dir_path.iterdir())
            inventory[subdir] = {
                "count": len(files),
                "files": [f.name for f in files if f.is_file()],
                "size_mb": sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024
            }
    return inventory

def show_status():
    """Show content inventory and publishing status."""
    state = load_state()
    inventory = scan_outputs()

    print("\n╔══════════════════════════════════════════╗")
    print("║   Eir Content Inventory — @eir.creates  ║")
    print("╚══════════════════════════════════════════╝\n")

    total_files = 0
    total_size = 0
    for name, data in inventory.items():
        print(f"  {name:25s} {data['count']:3d} files  ({data['size_mb']:.1f} MB)")
        total_files += data['count']
        total_size += data['size_mb']

    print(f"\n  {'TOTAL':25s} {total_files:3d} files  ({total_size:.1f} MB)")

    print(f"\n  Publishing Status:")
    print(f"    X/Twitter posts: {state.get('x_posts', 0)}")
    print(f"    IG posts:        {state.get('ig_posts', 0)}")
    print(f"    IG stories:      {state.get('ig_stories', 0)}")
    print(f"    TikTok posts:    {state.get('tiktok_posts', 0)}")
    print(f"    Last post:       {state.get('last_post', 'Never')}")
    print()

# ─── X/Twitter Publishing ─────────────────────────────────────────────────────

def post_x(image_path: str, text: str) -> dict:
    """Post to X/Twitter via xurl CLI."""
    # Step 1: Upload media
    print(f"  Uploading media: {image_path}")
    try:
        result = subprocess.run(
            ["xurl", "media", "upload", image_path],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"  ERROR: Media upload failed: {result.stderr}")
            return {"success": False, "error": result.stderr}

        # Parse media_id from JSON response
        media_data = json.loads(result.stdout)
        media_id = media_data.get("data", {}).get("media_id_string") or media_data.get("media_id_string")
        if not media_id:
            # Try alternate format
            media_id = media_data.get("data", {}).get("id") or media_data.get("id")

        if not media_id:
            print(f"  ERROR: Could not parse media_id from: {result.stdout}")
            return {"success": False, "error": "no_media_id"}

        print(f"  Media ID: {media_id}")
    except FileNotFoundError:
        print("  ERROR: xurl not found. Install with: curl -fsSL https://raw.githubusercontent.com/xdevplatform/xurl/main/install.sh | bash")
        return {"success": False, "error": "xurl_not_found"}

    # Step 2: Post tweet with media
    print(f"  Posting tweet...")
    result = subprocess.run(
        ["xurl", "post", text, "--media-id", media_id],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        print(f"  ERROR: Post failed: {result.stderr}")
        return {"success": False, "error": result.stderr}

    post_data = json.loads(result.stdout)
    post_id = post_data.get("data", {}).get("id", "unknown")
    print(f"  Posted! ID: {post_id}")
    return {"success": True, "post_id": post_id, "output": result.stdout}

def batch_post_x(dry_run: bool = False):
    """Batch post all content to X/Twitter."""
    plan = load_content_plan()
    state = load_state()
    inventory = scan_outputs()

    ig_posts = plan.get("instagram_feed", {})

    print(f"\n{'='*60}")
    print(f"  X/Twitter Batch Publishing — @eir.creates")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # Map content to available images
    all_images = {}
    for subdir in ["feed_batch_v2", "content_bank_v2"]:
        if subdir in inventory:
            for f in inventory[subdir]["files"]:
                all_images[f] = str(OUTPUTS_DIR / subdir / f)

    posted = 0
    for key, post in ig_posts.items():
        title = key.replace("_", " ").title()
        caption_x = post.get("caption_x", post.get("caption_ig", ""))
        posted_flag = post.get("posted", False)

        if posted_flag:
            print(f"  SKIP: {title} (already posted)")
            continue

        # Find an image for this post
        # Use content bank images matching the post theme
        image = None

        print(f"  [{posted+1}] {title}")
        print(f"      Text: {caption_x[:80]}...")
        print(f"      Image: {image or 'manual selection needed'}")

        if dry_run:
            print(f"      [DRY RUN] Would post\n")
            continue

        if not image:
            print(f"      SKIP: No image found\n")
            continue

        result = post_x(image, caption_x[:280])  # X character limit
        if result.get("success"):
            state["published"].append({
                "platform": "x", "title": title, "image": os.path.basename(image),
                "timestamp": datetime.now().isoformat(), "post_id": result.get("post_id")
            })
            state["x_posts"] = state.get("x_posts", 0) + 1
            state["last_post"] = datetime.now().isoformat()
            save_state(state)
            posted += 1

        # Rate limiting
        if posted < len(ig_posts):
            print("      Waiting 60s before next post...")
            import time
            time.sleep(60)

    print(f"\n  Complete! Posted {posted} tweets.")

# ─── Content Plan & Captions ──────────────────────────────────────────────────

def load_content_plan():
    with open(CONTENT_PLAN) as f:
        return json.load(f)

def generate_captions():
    """Extract and display all captions from content plan."""
    plan = load_content_plan()

    print("\n╔══════════════════════════════════════════╗")
    print("║   Eir Caption Bank — @eir.creates       ║")
    print("╚══════════════════════════════════════════╝\n")

    char_count = {}  # platform: total_chars

    for key, post in plan.get("instagram_feed", {}).items():
        title = key.replace("_", " ").title()
        caption_ig = post.get("caption_ig", "No caption")
        caption_x = post.get("caption_x", "No X caption")

        print(f"  ── {title} ──")
        print(f"  [IG] ({len(caption_ig)} chars)")
        print(f"  {caption_ig}")
        print()
        print(f"  [X]  ({len(caption_x)} chars)")
        print(f"  {caption_x}")
        print()

# ─── Schedule ──────────────────────────────────────────────────────────────────

def show_schedule():
    """Show optimal posting schedule."""
    plan = load_content_plan()
    schedule = plan.get("posting_schedule", {})

    print("\n╔══════════════════════════════════════════╗")
    print("║   Eir Posting Schedule — @eir.creates    ║")
    print("╚══════════════════════════════════════════╝\n")

    for phase, info in schedule.items():
        print(f"  {phase.replace('_', ' ').title()}")
        print(f"    Duration:   {info.get('duration', 'N/A')}")
        print(f"    Frequency:  {info.get('frequency', 'N/A')}")
        print(f"    Notes:      {info.get('notes', 'N/A')}")
        print()

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Eir Content Publisher — @eir.creates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publish.py status                       # Show content inventory
  python publish.py calendar                     # Show content calendar
  python publish.py post-x photo.png "Caption"  # Post to X/Twitter
  python publish.py post-x-batch --dry-run       # Preview batch X posts
  python publish.py generate-captions            # Show all captions
  python publish.py schedule                     # Show posting schedule
        """
    )

    parser.add_argument("command", choices=[
        "status", "calendar", "post-x", "post-x-batch",
        "generate-captions", "schedule"
    ])
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview without posting")
    parser.add_argument("--image", "-i", help="Image path for post-x")
    parser.add_argument("--text", "-t", help="Caption text for post-x")

    args = parser.parse_args()

    if args.command == "status":
        show_status()
    elif args.command == "calendar":
        show_schedule()
    elif args.command == "post-x":
        if not args.image or not args.text:
            print("ERROR: --image and --text are required for post-x")
            print("Usage: python publish.py post-x --image <path> --text <caption>")
            return
        if not os.path.exists(args.image):
            print(f"ERROR: Image not found: {args.image}")
            return
        result = post_x(args.image, args.text)
    elif args.command == "post-x-batch":
        batch_post_x(args.dry_run)
    elif args.command == "generate-captions":
        generate_captions()
    elif args.command == "schedule":
        show_schedule()

if __name__ == "__main__":
    main()
