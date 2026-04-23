#!/usr/bin/env python3
"""
cali_see.py — lets cali actually pull images and see them.

usage:
    python3 cali_see.py <url> [<url> ...]           # pull images from url(s)
    python3 cali_see.py --max 10 <url>              # pull up to 10 from a page
    python3 cali_see.py --out /path/to/dir <url>    # custom output dir
    python3 cali_see.py --res 736x <url>            # pinterest resolution
    echo "url1\\nurl2" | python3 cali_see.py -      # read urls from stdin

what it handles:
    - direct image urls (.jpg .jpeg .png .webp .gif) → just downloads
    - pinterest pages (any pinterest.com url) → extracts i.pinimg.com urls, upgrades resolution
    - any other page → extracts og:image meta tag, downloads that
    - multiple images per page when available

prints file paths to stdout, one per line. cali uses Read on those to actually see.
nothing goes in the repo. outputs to /tmp/cali_see/<timestamp>/ by default.
"""

import os
import re
import sys
import time
import argparse
import subprocess
import urllib.parse
from pathlib import Path


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
IMG_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif)(\?.*)?$", re.IGNORECASE)
PINIMG_RE = re.compile(r"https://i\.pinimg\.com/[0-9]+x/[a-f0-9/]+\.(?:jpe?g|png|webp|gif)")
OG_IMG_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE)
GENERIC_IMG_RE = re.compile(r'https?://[^\s"\'<>)]+\.(?:jpe?g|png|webp|gif)(?:\?[^\s"\'<>)]*)?', re.IGNORECASE)


def fetch_html(url):
    """pull html with a real user agent. returns body or empty string on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "-A", UA, "--max-time", "20", url],
            capture_output=True, timeout=25, check=False
        )
        return result.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[cali_see] fetch failed for {url}: {e}", file=sys.stderr)
        return ""


def is_direct_image(url):
    """check if url is a direct image by extension."""
    parsed = urllib.parse.urlparse(url)
    return bool(IMG_EXT_RE.search(parsed.path))


def is_pinterest(url):
    return "pinterest." in urllib.parse.urlparse(url).netloc


def upgrade_pinimg_res(url, res):
    """swap pinterest thumbnail resolution. res can be 170x, 236x, 474x, 736x, originals."""
    return re.sub(r"/i\.pinimg\.com/[0-9]+x/", f"/i.pinimg.com/{res}/", url)


def extract_pinterest_images(html, res="736x"):
    """find all i.pinimg.com urls and upgrade resolution."""
    urls = PINIMG_RE.findall(html)
    # re-extract with full match since findall returns groups
    urls = [m.group(0) for m in PINIMG_RE.finditer(html)]
    upgraded = [upgrade_pinimg_res(u, res) for u in urls]
    # dedupe preserving order
    seen = set()
    out = []
    for u in upgraded:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_og_image(html):
    """find og:image meta tag. returns url or None."""
    match = OG_IMG_RE.search(html)
    return match.group(1) if match else None


def extract_generic_images(html):
    """fallback — find any direct image url embedded in html."""
    urls = GENERIC_IMG_RE.findall(html)
    urls = [m.group(0) for m in GENERIC_IMG_RE.finditer(html)]
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_image(url, out_dir, idx=0):
    """curl an image to out_dir. returns path or None."""
    parsed = urllib.parse.urlparse(url)
    ext_match = IMG_EXT_RE.search(parsed.path)
    ext = ext_match.group(0).lower().split("?")[0] if ext_match else ".jpg"
    # strip querystring from ext
    ext = re.sub(r"\?.*$", "", ext)
    if not ext.startswith("."):
        ext = "." + ext
    fname = f"img_{idx:03d}{ext}"
    fpath = out_dir / fname
    try:
        result = subprocess.run(
            ["curl", "-sL", "-A", UA, "--max-time", "30", "-o", str(fpath), url],
            capture_output=True, timeout=35, check=False
        )
        if fpath.exists() and fpath.stat().st_size > 500:
            return fpath
        # too small — probably an error page
        if fpath.exists():
            fpath.unlink()
    except Exception as e:
        print(f"[cali_see] download failed for {url}: {e}", file=sys.stderr)
    return None


def process_url(url, out_dir, max_images, res):
    """route url to the right handler. returns list of saved paths."""
    saved = []

    # direct image
    if is_direct_image(url):
        path = download_image(url, out_dir, idx=len(list(out_dir.glob("*"))))
        if path:
            saved.append(path)
        return saved

    # fetch page html
    html = fetch_html(url)
    if not html:
        return saved

    # pinterest
    if is_pinterest(url):
        image_urls = extract_pinterest_images(html, res=res)[:max_images]
        for i, iu in enumerate(image_urls):
            path = download_image(iu, out_dir, idx=len(list(out_dir.glob("*"))))
            if path:
                saved.append(path)
        return saved

    # generic page — try og:image first, then any embedded images
    og = extract_og_image(html)
    if og:
        path = download_image(og, out_dir, idx=len(list(out_dir.glob("*"))))
        if path:
            saved.append(path)

    if len(saved) < max_images:
        extras = extract_generic_images(html)[:max_images - len(saved)]
        for iu in extras:
            if iu == og:
                continue
            path = download_image(iu, out_dir, idx=len(list(out_dir.glob("*"))))
            if path:
                saved.append(path)
            if len(saved) >= max_images:
                break

    return saved


def main():
    ap = argparse.ArgumentParser(description="pull images from a url so cali can see them.")
    ap.add_argument("urls", nargs="*", help="urls to pull images from. use '-' for stdin.")
    ap.add_argument("--max", type=int, default=5, help="max images per url (default 5)")
    ap.add_argument("--out", default=None, help="output dir (default /tmp/cali_see/<timestamp>/)")
    ap.add_argument("--res", default="736x", help="pinterest resolution: 170x/236x/474x/736x/originals (default 736x)")
    args = ap.parse_args()

    # resolve urls
    urls = []
    for u in args.urls:
        if u == "-":
            for line in sys.stdin:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        else:
            urls.append(u)

    if not urls:
        ap.print_help()
        sys.exit(1)

    # set up output dir
    if args.out:
        out_dir = Path(args.out)
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_dir = Path("/tmp/cali_see") / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[cali_see] output dir: {out_dir}", file=sys.stderr)

    all_saved = []
    for url in urls:
        print(f"[cali_see] processing: {url}", file=sys.stderr)
        saved = process_url(url, out_dir, max_images=args.max, res=args.res)
        print(f"[cali_see]   saved {len(saved)} image(s)", file=sys.stderr)
        all_saved.extend(saved)

    # stdout gets just the paths, one per line — cali pipes these to Read
    for p in all_saved:
        print(str(p))

    if not all_saved:
        print("[cali_see] no images saved.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
