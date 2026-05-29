#!/usr/bin/env python3
"""Extract frames from videos for face consistency check."""
from PIL import Image
import subprocess
from pathlib import Path

videos_dir = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/videos_v2")
ffmpeg = Path.home() / "comfy/ComfyUI/.venv/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
out_dir = Path("/mnt/d/Proyectos/Yggdrasil/Muspelheim/AI-Influencer/outputs/video_frames_check")
out_dir.mkdir(parents=True, exist_ok=True)

for mp4 in sorted(videos_dir.glob("*.mp4")):
    name = mp4.stem
    for frame_num in [1, 8, 16]:
        out_path = out_dir / f"{name}_f{frame_num:02d}.png"
        cmd = [
            str(ffmpeg), "-y", "-i", str(mp4),
            "-vf", f"select=eq(n\\,{frame_num-1})",
            "-vframes", "1",
            "-q:v", "2",
            str(out_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if out_path.exists() and out_path.stat().st_size > 1000:
            img = Image.open(out_path)
            img = img.resize((256, 256), Image.LANCZOS)
            img.save(out_dir / f"{name}_f{frame_num:02d}_thumb.jpg", "JPEG", quality=85)
            print(f"  {name} frame {frame_num}: OK ({img.size})")
        else:
            print(f"  {name} frame {frame_num}: FAILED")

print("Done!")
