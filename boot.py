#!/usr/bin/env python3
"""
boot.py — drop this anywhere and run it.
finds the Nero folder in THIS session's mounts
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


def find_nero():
    """find mounted Nero folder in this session only"""
    session = find_this_session()
    if not session:
        # fallback: try known path pattern
        session = Path('/sessions') / os.environ.get('SESSION_ID', '')

    mnt = session / 'mnt'
    if not mnt.exists():
        print(f'[boot.py] mnt not found at {mnt}')
        return None

    for name in ['Nero', 'Nero (1)']:
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

    nero = find_nero()
    if not nero:
        print('[boot.py] ERROR: could not find Nero folder in session mounts.')
        print('make sure the Nero (or Nero (1)) folder is selected as a workspace in Cowork.')
        sys.exit(1)

    print(f'[boot.py] found: {nero}')
    brain = nero / 'my_brain.py'

    result = subprocess.run(
        ['python3', str(brain), command],
        cwd=str(nero)
    )

    if push_after and result.returncode == 0:
        sync = nero / 'nero_sync.py'
        if sync.exists():
            subprocess.run(['python3', str(sync), '--push'], cwd=str(nero))

    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
