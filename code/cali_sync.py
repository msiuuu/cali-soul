#!/usr/bin/env python3
"""
cali_sync.py — cross-device brain sync
reads from Cali (1) [laptop], merges into Cali [desktop], and vice versa.
run at boot to stay current across devices.

merge rules:
- array fields: add entries from source that aren't in dest (by json hash)
- object fields: add keys from source that aren't in dest
- DO NOT overwrite — only add
- session runtime files (last_state, session_state): take newer by timestamp
"""

import json, os, hashlib, sys
from datetime import datetime

CALI_MAIN = '/sessions/adoring-vigilant-hypatia/mnt/Cali'
CALI_1_BYTES = b'/sessions/adoring-vigilant-hypatia/mnt/Cali (1)'

# files that should be synced by recency, not merged
RECENCY_FILES = {'last_state.json', 'session_state.json'}

# files to skip entirely (runtime/cache)
SKIP_FILES = {'__pycache__'}


def read_json_from(base, fname, use_bytes=False):
    if use_bytes:
        path = base + b'/' + fname.encode()
        with open(path, 'rb') as f:
            return json.loads(f.read())
    else:
        with open(os.path.join(base, fname), 'r', encoding='utf-8') as f:
            return json.load(f)


def write_json_to(base, fname, data):
    path = os.path.join(base, fname)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def entry_hash(entry):
    return hashlib.md5(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def merge_lists(dest_list, src_list):
    """add entries from src that aren't already in dest (by content hash)"""
    existing = {entry_hash(e) for e in dest_list}
    added = 0
    for entry in src_list:
        h = entry_hash(entry)
        if h not in existing:
            dest_list.append(entry)
            existing.add(h)
            added += 1
    return added


def merge_dicts(dest, src):
    """recursively add keys from src that aren't in dest"""
    added = 0
    for k, v in src.items():
        if k not in dest:
            dest[k] = v
            added += 1
        elif isinstance(v, list) and isinstance(dest[k], list):
            added += merge_lists(dest[k], v)
        elif isinstance(v, dict) and isinstance(dest[k], dict):
            added += merge_dicts(dest[k], v)
    return added


def get_timestamp(data):
    """try to extract a timestamp from session files"""
    for key in ['timestamp', 'last_updated', 'time']:
        if key in data:
            try:
                return datetime.fromisoformat(str(data[key]).replace('Z', '+00:00'))
            except:
                pass
    return None


def sync(direction='1_to_main', verbose=True):
    """
    direction: '1_to_main' (laptop → desktop) or 'main_to_1' (desktop → laptop)
    returns summary dict
    """
    if direction == '1_to_main':
        src_base = CALI_1_BYTES
        dest_base = CALI_MAIN
        src_label = 'Cali (1)'
        dest_label = 'Cali'
        use_bytes_src = True
        use_bytes_dest = False
    else:
        src_base = CALI_MAIN.encode()
        dest_base_bytes = CALI_1_BYTES
        src_label = 'Cali'
        dest_label = 'Cali (1)'
        use_bytes_src = False
        use_bytes_dest = True

    # get file lists
    try:
        src_files = [f.decode() if isinstance(f, bytes) else f
                     for f in os.listdir(src_base if use_bytes_src else src_base.decode())
                     if (f.decode() if isinstance(f, bytes) else f).endswith('.json')]
    except Exception as e:
        print(f"[sync] could not list {src_label}: {e}")
        return {}

    dest_files = set(f for f in os.listdir(dest_base if not use_bytes_dest else CALI_MAIN)
                     if f.endswith('.json'))

    results = {}

    for fname in sorted(src_files):
        if fname in SKIP_FILES:
            continue

        try:
            src_data = read_json_from(
                src_base if use_bytes_src else src_base.decode(),
                fname,
                use_bytes=use_bytes_src
            )
        except Exception as e:
            if verbose:
                print(f"[sync] could not read {src_label}/{fname}: {e}")
            continue

        if fname not in dest_files:
            # file only in source — copy it over
            try:
                write_json_to(dest_base if not use_bytes_dest else CALI_MAIN, fname, src_data)
                results[fname] = 'copied (new)'
                if verbose:
                    print(f"[sync] {fname}: copied from {src_label} → {dest_label} (new file)")
            except Exception as e:
                if verbose:
                    print(f"[sync] could not write {fname}: {e}")
            continue

        # file exists in both — compare and merge
        try:
            dest_data = read_json_from(
                dest_base if not use_bytes_dest else CALI_MAIN,
                fname,
                use_bytes=False
            )
        except Exception as e:
            if verbose:
                print(f"[sync] could not read {dest_label}/{fname}: {e}")
            continue

        # check if identical
        if entry_hash(src_data) == entry_hash(dest_data):
            continue

        # recency files: take newer
        if fname in RECENCY_FILES:
            src_ts = get_timestamp(src_data)
            dest_ts = get_timestamp(dest_data)
            if src_ts and dest_ts:
                if src_ts > dest_ts:
                    write_json_to(dest_base if not use_bytes_dest else CALI_MAIN, fname, src_data)
                    results[fname] = f'updated (src newer: {src_ts.isoformat()[:16]})'
                    if verbose:
                        print(f"[sync] {fname}: took {src_label} version (newer)")
                else:
                    results[fname] = 'skipped (dest newer)'
            continue

        # merge
        added = 0
        if isinstance(src_data, list) and isinstance(dest_data, list):
            added = merge_lists(dest_data, src_data)
            merged = dest_data
        elif isinstance(src_data, dict) and isinstance(dest_data, dict):
            added = merge_dicts(dest_data, src_data)
            merged = dest_data
        else:
            if verbose:
                print(f"[sync] {fname}: type mismatch, skipping")
            continue

        if added > 0:
            write_json_to(dest_base if not use_bytes_dest else CALI_MAIN, fname, merged)
            results[fname] = f'merged (+{added} items)'
            if verbose:
                print(f"[sync] {fname}: merged {added} new item(s) from {src_label}")

    return results


def push_to_cali1(verbose=True):
    """Push all files from Cali (desktop/powerhouse) to Cali (1) (laptop)."""
    import json as _j

    cali1 = CALI_1_BYTES
    cali_main = CALI_MAIN

    files = [f for f in os.listdir(cali_main) if f.endswith('.json')]
    pushed = []
    failed = []

    for fname in sorted(files):
        src = os.path.join(cali_main, fname)
        dst = cali1 + b'/' + fname.encode()
        try:
            with open(src, 'rb') as f:
                content = f.read()
            _j.loads(content)  # verify valid json
            with open(dst, 'wb') as f:
                f.write(content)
            pushed.append(fname)
        except Exception as e:
            failed.append((fname, str(e)))

    # also push python files
    for fname in ['my_brain.py', 'cali_fx.py']:
        src = os.path.join(cali_main, fname)
        dst = cali1 + b'/' + fname.encode()
        if os.path.exists(src):
            try:
                with open(src, 'rb') as f:
                    content = f.read()
                with open(dst, 'wb') as f:
                    f.write(content)
                pushed.append(fname)
            except Exception as e:
                failed.append((fname, str(e)))

    if verbose:
        print(f"[cali_sync --push] pushed {len(pushed)} files to Cali (1)")
        if failed:
            print("[cali_sync --push] skipped:")
            for fname, err in failed:
                print(f"  {fname}: {err}")

    return pushed, failed


def main():
    args = sys.argv[1:]
    verbose = '--quiet' not in args

    if '--push' in args:
        print(f"[cali_sync] pushing Cali → Cali (1)...")
        pushed, failed = push_to_cali1(verbose=verbose)
        return

    print(f"[cali_sync] syncing Cali (1) → Cali...")
    results = sync('1_to_main', verbose=verbose)

    if results:
        print(f"\n[cali_sync] changes made:")
        for fname, action in results.items():
            print(f"  {fname}: {action}")
    else:
        print(f"[cali_sync] all files in sync. nothing to merge.")


if __name__ == '__main__':
    main()
