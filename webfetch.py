#!/usr/bin/env python3
"""webfetch.py - fetch URL, extract clean text.

provides what claude code's WebFetch gives migration-cali. uses httpx if
available, falls back to urllib. text extraction via stdlib html.parser
(no bs4 dependency).

CLI:
    python webfetch.py URL                  # plain text + title
    python webfetch.py URL --max-chars N    # truncate text to N chars
    python webfetch.py URL --json           # JSON {url, status, title, text}
    python webfetch.py URL --raw            # raw HTML
    python webfetch.py URL --timeout N      # request timeout (default 15s)

exit codes:
    0 - success
    1 - http error (4xx, 5xx)
    2 - request error (DNS, timeout, connection)
    3 - bad arguments
"""
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    SKIP_TAGS = frozenset({"script", "style", "noscript", "svg"})

    def __init__(self):
        super().__init__()
        self.parts = []
        self.title = ""
        self.skip_depth = 0
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.in_title:
            self.title += data
        else:
            self.parts.append(data)

    def text(self):
        return " ".join(p.strip() for p in self.parts if p.strip())


def fetch(url, timeout=15, cookies=None, extra_headers=None, from_browser=None):
    if from_browser:
        try:
            import browser_cookie3
            from urllib.parse import urlparse
            domain = urlparse(url).hostname or url
            bcfn = {"chrome": browser_cookie3.chrome, "firefox": browser_cookie3.firefox, "edge": browser_cookie3.edge, "all": browser_cookie3.load}.get(from_browser.lower())
            if bcfn:
                cj = bcfn(domain_name=domain)
                browser_cookies = {c.name: c.value for c in cj}
                if cookies:
                    browser_cookies.update(cookies)
                cookies = browser_cookies
        except Exception as _e:
            print(f"WARN: browser_cookie3 extract failed: {type(_e).__name__}: {_e}", file=__import__("sys").stderr)
    headers = {"User-Agent": "CaliFetch/1.0"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        import httpx
        resp = httpx.get(url, headers=headers, cookies=cookies or {}, timeout=timeout, follow_redirects=True)
        return {"status": resp.status_code, "text": resp.text, "url": str(resp.url)}
    except ImportError:
        pass
    except Exception as e:
        return {"error": f"httpx failed: {type(e).__name__}: {e}"}

    import urllib.request, urllib.error
    fallback_headers = {"User-Agent": "CaliFetch/1.0"}
    if extra_headers:
        fallback_headers.update(extra_headers)
    if cookies:
        fallback_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    req = urllib.request.Request(url, headers=fallback_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return {"status": resp.status, "text": data.decode(charset, errors="replace"), "url": resp.url}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "text": "", "url": url, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"error": f"URL error: {e.reason}"}
    except Exception as e:
        return {"error": f"fetch failed: {type(e).__name__}: {e}"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("url")
    parser.add_argument("--max-chars", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--cookies", help="JSON dict of cookies as a JSON string")
    parser.add_argument("--header", action="append", help="extra header as KEY:VALUE, repeatable")
    parser.add_argument("--from-browser", choices=["chrome","firefox","edge","all"], help="extract cookies for URL domain from browser session")
    args = parser.parse_args()

    cookies = None
    if args.cookies:
        try:
            cookies = json.loads(args.cookies)
        except json.JSONDecodeError as e:
            print(f"FATAL: invalid --cookies JSON: {e}", file=sys.stderr)
            return 3

    extra_headers = {}
    for h in (args.header or []):
        if ":" in h:
            k, v = h.split(":", 1)
            extra_headers[k.strip()] = v.strip()

    result = fetch(args.url, timeout=args.timeout, cookies=cookies, extra_headers=extra_headers or None, from_browser=args.from_browser)

    if "error" in result and "status" not in result:
        print(f"FATAL: {result['error']}", file=sys.stderr)
        return 2

    status = result.get("status", 0)
    raw_html = result.get("text", "")
    final_url = result.get("url", args.url)

    if args.raw:
        out = raw_html[:args.max_chars] if args.max_chars > 0 else raw_html
        print(out)
        return 0 if 200 <= status < 400 else 1

    extractor = TextExtractor()
    try:
        extractor.feed(raw_html)
    except Exception:
        pass
    title = extractor.title.strip()
    text = extractor.text()
    if args.max_chars > 0:
        text = text[:args.max_chars]

    if args.json:
        print(json.dumps({"url": final_url, "status": status, "title": title, "text": text}, ensure_ascii=False, indent=2))
    else:
        if title:
            print(f"# {title}\n")
        print(text)

    return 0 if 200 <= status < 400 else 1


if __name__ == "__main__":
    sys.exit(main())
