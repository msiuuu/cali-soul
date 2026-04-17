#!/usr/bin/env python3
"""
cali_save.py — save an image (URL or local path) permanently

usage:
    python3 cali_save.py <url_or_path> [--label "note"] [--dir path]
"""

import argparse
import mimetypes
import shutil
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


SAVED_DIR = Path("/home/user/cali-soul/experimenting/images/saved")

EXT_FROM_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
}


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def download_image(url: str, dest_dir: Path, label: str = None) -> Path:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) cali_save/1.0",
        },
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        content_type = r.headers.get("Content-Type", "").split(";")[0].strip()
        data = r.read()

    ext = EXT_FROM_MIME.get(content_type)
    if not ext:
        # fallback — try from URL path
        url_path = url.split("?")[0]
        ext = Path(url_path).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".avif"):
            ext = ".jpg"

    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{timestamp}_{label.replace(' ', '_')}" if label else timestamp
    dest = dest_dir / f"{stem}{ext}"

    dest.write_bytes(data)
    return dest


def copy_local(src: Path, dest_dir: Path, label: str = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = src.suffix.lower() or ".jpg"
    stem = f"{timestamp}_{label.replace(' ', '_')}" if label else timestamp
    dest = dest_dir / f"{stem}{ext}"
    shutil.copy2(src, dest)
    return dest


def main():
    parser = argparse.ArgumentParser(description="cali_save — save an image permanently")
    parser.add_argument("source", help="URL or local file path")
    parser.add_argument("--label", default=None, help="label for the saved file")
    parser.add_argument("--dir", default=None, help="destination folder (default: experimenting/images/saved)")
    args = parser.parse_args()

    dest_dir = Path(args.dir) if args.dir else SAVED_DIR

    if is_url(args.source):
        try:
            saved = download_image(args.source, dest_dir, args.label)
        except Exception as e:
            print(f"[cali_save] download failed: {e}")
            sys.exit(1)
    else:
        src = Path(args.source)
        if not src.exists():
            print(f"[cali_save] file not found: {src}")
            sys.exit(1)
        saved = copy_local(src, dest_dir, args.label)

    print(f"[cali_save] saved → {saved}")
    return saved


if __name__ == "__main__":
    main()
