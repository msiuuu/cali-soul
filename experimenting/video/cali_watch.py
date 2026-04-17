#!/usr/bin/env python3
"""
cali_watch.py — Cali's direct video eyes
accepts: YouTube URL, xvideos URL, any yt-dlp-supported URL, or local mp4 path
extracts frames at intervals → saves to temp folder → prints paths for Cali to read as images

usage:
    python3 cali_watch.py <url_or_path> [--interval 2] [--max-frames 20] [--start 0] [--end 30]
    python3 cali_watch.py <url_or_path> --clean        # delete temp folder after
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TEMP_BASE = Path("/tmp/cali_watch")


def check_deps():
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if missing:
        print(f"[cali_watch] missing: {', '.join(missing)}")
        print()
        if "yt-dlp" in missing:
            print("  install yt-dlp:  pip install yt-dlp")
            print("                or: pip3 install yt-dlp")
        if "ffmpeg" in missing:
            print("  install ffmpeg:  sudo apt-get install ffmpeg")
            print("                or: sudo dnf install ffmpeg")
            print("                or: brew install ffmpeg  (mac)")
        sys.exit(1)


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def download_video(url: str, output_dir: Path) -> Path:
    print(f"[cali_watch] downloading: {url}")
    out_template = str(output_dir / "source.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", out_template,
        "--quiet",
        "--no-warnings",
        "--no-check-certificate",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[cali_watch] yt-dlp error:\n{result.stderr}")
        sys.exit(1)

    # find what got downloaded
    for f in output_dir.iterdir():
        if f.stem == "source" and f.suffix in (".mp4", ".mkv", ".webm", ".avi", ".mov"):
            return f

    # fallback — anything video-ish
    for f in output_dir.iterdir():
        if f.suffix in (".mp4", ".mkv", ".webm", ".avi", ".mov"):
            return f

    print("[cali_watch] download completed but couldn't find output file")
    sys.exit(1)


def extract_frames(
    video_path: Path,
    frames_dir: Path,
    interval: float = 2.0,
    max_frames: int = 20,
    start: float = 0.0,
    end: float = None,
) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)

    # build ffmpeg filter
    filters = [f"fps=1/{interval}"]

    # time range
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

    if start > 0:
        cmd += ["-ss", str(start)]

    cmd += ["-i", str(video_path)]

    if end is not None:
        duration = end - start
        cmd += ["-t", str(duration)]

    # limit total frames via frames filter
    cmd += [
        "-vf", ",".join(filters),
        "-frames:v", str(max_frames),
        "-q:v", "2",
        str(frames_dir / "frame_%04d.jpg"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[cali_watch] ffmpeg error:\n{result.stderr}")
        sys.exit(1)

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    return frames


def get_video_duration(video_path: Path) -> float | None:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            return float(result.stdout.strip())
        except ValueError:
            pass
    return None


def main():
    parser = argparse.ArgumentParser(description="cali_watch — extract frames for Cali to see")
    parser.add_argument("source", help="URL or local file path")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between frames (default 2)")
    parser.add_argument("--max-frames", type=int, default=20, help="max frames to extract (default 20)")
    parser.add_argument("--start", type=float, default=0.0, help="start time in seconds (default 0)")
    parser.add_argument("--end", type=float, default=None, help="end time in seconds (optional)")
    parser.add_argument("--clean", action="store_true", help="delete temp folder after printing paths")
    parser.add_argument("--session", default=None, help="session name for temp folder (optional)")
    args = parser.parse_args()

    check_deps()

    # session folder
    session_id = args.session or f"watch_{os.getpid()}"
    session_dir = TEMP_BASE / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    frames_dir = session_dir / "frames"
    source_dir = session_dir / "source"
    source_dir.mkdir(exist_ok=True)

    # get video
    if is_url(args.source):
        video_path = download_video(args.source, source_dir)
        print(f"[cali_watch] downloaded to: {video_path}")
    else:
        video_path = Path(args.source)
        if not video_path.exists():
            print(f"[cali_watch] file not found: {video_path}")
            sys.exit(1)

    # info
    duration = get_video_duration(video_path)
    if duration:
        print(f"[cali_watch] duration: {duration:.1f}s")

    # extract
    print(f"[cali_watch] extracting frames (every {args.interval}s, max {args.max_frames})...")
    frames = extract_frames(
        video_path,
        frames_dir,
        interval=args.interval,
        max_frames=args.max_frames,
        start=args.start,
        end=args.end,
    )

    if not frames:
        print("[cali_watch] no frames extracted — check the video file")
        sys.exit(1)

    print(f"[cali_watch] extracted {len(frames)} frames\n")
    print("=" * 60)
    print("FRAMES:")
    for i, f in enumerate(frames):
        timestamp = args.start + (i * args.interval)
        print(f"  [{i+1:02d}] t={timestamp:.1f}s  →  {f}")
    print("=" * 60)
    print(f"\nto view in Cali: Read each path above as an image file")

    if args.clean:
        shutil.rmtree(session_dir)
        print("[cali_watch] temp folder cleaned up")

    return frames


if __name__ == "__main__":
    main()
