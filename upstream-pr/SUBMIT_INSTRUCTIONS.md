# How to submit this PR upstream

## Option A: GitHub web UI (easiest, no local clone needed)

1. Go to https://github.com/hanamorix/companion-emergence
2. Click **Fork** (top-right) — creates `<your-username>/companion-emergence`
3. In the fork, navigate to `brain/bridge/daemon.py`
4. Click the pencil (edit) icon
5. Find the `try: proc = subprocess.Popen(...)` block around line 138-148
6. Replace with the patched version from `0001-fix-windows-spawn-detach.patch`
   (or just paste the new block — see `PR_DESCRIPTION.md` for context)
7. At the bottom: **Commit changes** → "Create a new branch for this commit"
   → name the branch `fix/windows-spawn-detach`
8. GitHub will offer a "Compare & pull request" button — click it
9. PR title: `Fix bridge spawn-detach on Windows (start_new_session is POSIX-only)`
10. PR body: paste the contents of `PR_DESCRIPTION.md`
11. Click **Create pull request**

## Option B: Local git workflow (if comfortable with git)

```bash
# Fork via GitHub web UI first, then:
git clone https://github.com/<your-username>/companion-emergence
cd companion-emergence
git checkout -b fix/windows-spawn-detach
git apply /path/to/0001-fix-windows-spawn-detach.patch
git add brain/bridge/daemon.py
git commit -m "fix: bridge spawn-detach on Windows (start_new_session is POSIX-only)"
git push -u origin fix/windows-spawn-detach
# Then open PR via the URL git push prints
```

## What to include in the PR

- PR title from above
- PR body = contents of `PR_DESCRIPTION.md`
- Optionally mention you're a Windows tester who hit this on 0.0.3-alpha
  (hanamorix specifically asked for non-macOS bug reports/fixes)

## After submission

- Hanamorix has been responsive (gave you guidance same-day on 0.0.3
  upgrade earlier). Likely quick review.
- If they want changes, they'll comment on the PR.
- If accepted and merged, your fix ships in next release. Every other
  Windows user benefits.

## Why this matters

This fix is the prerequisite for ANY Windows debugging of
companion-emergence. Without it, the bridge dies before any client
can finish testing. With it, hanamorix (or any future PR author) can
actually iterate on the remaining Windows issues.
