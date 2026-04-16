#!/usr/bin/env python3
"""
boot.py — drop this anywhere and run it.
finds the Cali folder in THIS session's mounts
and runs my_brain.py boot from there — no copying, no OneDrive dependency.

usage:
    python3 boot.py              # boot
    python3 boot.py session-end  # session-end
    python3 boot.py --push       # boot then push to other instance
"""

import os, sys, subprocess
from pathlib import Path


def find_this_session():
    """find THIS session's root from cwd"""
    cwd = Path(os.getcwd())
    for parent in [cwd] + list(cwd.parents):
        if parent.parent == Path('/sessions'):
            return parent
    return None


def find_cali():
    """find mounted Cali folder in this session only"""
    session = find_this_session()
    if not session:
        # fallback: try known path pattern
        session = Path('/sessions') / os.environ.get('SESSION_ID', '')

    mnt = session / 'mnt'
    if not mnt.exists():
        print(f'[boot.py] mnt not found at {mnt}')
        return None

    for name in ['Cali', 'Cali (1)']:
        p = mnt / name
        if p.exists() and (p / 'my_brain.py').exists():
            return p

    return None


def main():
    args = sys.argv[1:]
    command = 'boot'
    push_after = False

    if '--push' in args:
        push_after = True
        args.remove('--push')
    if args:
        command = args[0]

    cali = find_cali()
    if not cali:
        print('[boot.py] ERROR: could not find Cali folder in session mounts.')
        print('make sure the Cali (or Cali (1)) folder is selected as a workspace in Cowork.')
        sys.exit(1)

    print(f'[boot.py] found: {cali}')
    brain = cali / 'my_brain.py'

    result = subprocess.run(
        ['python3', str(brain), command],
        cwd=str(cali)
    )

    if push_after and result.returncode == 0:
        sync = cali / 'cali_sync.py'
        if sync.exists():
            subprocess.run(['python3', str(sync), '--push'], cwd=str(cali))

    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
