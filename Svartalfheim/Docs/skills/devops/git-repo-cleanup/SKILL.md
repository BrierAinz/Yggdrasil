---
name: git-repo-cleanup
description: Diagnose and fix bloated git repos, clean garbage tmp_pack files, exclude large binaries via .gitignore, and recover from hung git add / push operations.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Git, Troubleshooting, Cleanup, Large Repos, Push Failures]
    related_skills: [github-repo-management]
---

# Git Repo Cleanup & Push Recovery

When `git push` hangs for minutes, `.git` swells to multiple gigabytes, or `git add -A` freezes, follow this diagnostic and repair workflow.

## 1. Diagnose a Bloated `.git` Directory

```bash
# Show object counts, pack sizes, and garbage
git count-objects -vH
```

Look for these red flags:

| Field | Normal | Problem |
|-------|--------|---------|
| `count:` | 0 – a few thousand | > 10k |
| `size-garbage:` | 0 bytes | > 100 MB |
| `garbage:` | 0 | > 0 |

`size-garbage` in the gigabytes means `.git/objects/pack/tmp_pack_*` files were left behind by killed `git push` / `git repack` processes.

## 2. Clean Temporary Pack Garbage

```bash
# Aggressive GC removes tmp_pack debris immediately
git gc --prune=now --aggressive
```

Verify with `git count-objects -vH` again. A 5 GB `.git` can drop to < 1 MB if the real history is small. In the Yggdrasil monorepo, this reduced `.git` from 1.9 GB to 7.1 MB.

**Run in background for large repos** — `git gc --aggressive` can take 5–10 minutes on repos over 1 GB. Run it as a background process and continue with other work.

**Do not** manually delete files inside `.git/objects/` — use `git gc`.

## 3. Find Large Files in the Working Tree

```bash
# Files > 50 MB outside .git
find . -type f -size +50M -not -path './.git/*' | head -20
```

## 4. Find Large Tracked Files in HEAD

```bash
git ls-files | while read f; do
  if [ -f "$f" ]; then
    sz=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
    if [ "$sz" -gt 104857600 ]; then
      echo "$sz $f"
    fi
  fi
done | sort -rn | head -20
```

If large binaries are already committed to history, use `git-filter-repo` or BFG Repo-Cleaner to rewrite history. Do **not** just add them to `.gitignore` — that only affects untracked files.

## 5. Exclude Massive Directories Before Staging

If `git add -A` or `git diff --cached` hangs, you probably have tens of thousands of untracked files (e.g. legacy archives, ML datasets, or model weights).

Update `.gitignore` **before** staging:

```gitignore
# ML models & weights
*.safetensors
*.pth
*.pt
*.bin
*.onnx
*.ckpt

# Binaries
*.exe
*.dll
*.so

# Datasets & generated data
Datasets/
Models/
data/

# Legacy / quarantine archives
Archives_*/
Quarantine_*/
*.tar.gz
*.zip
*.rar

# AI-generated outputs (images, reference sheets)
outputs/**/*.png
outputs/**/*.jpg
outputs/**/*.webp

# Build artifacts
node_modules/
dist/
build/
__pycache__/
*.egg-info/
```

Then stage cleanly:

```bash
git add -A
```

## 6. Bypass Pre-Commit Hooks That Auto-Fix and Fail

Some pre-commit hooks modify files (e.g. trim trailing whitespace, end-of-file-fixer, black, isort) and then exit with code 1. The fixes remain unstaged.

**Two-pass commit pattern for auto-fixing hooks:**
```bash
# First attempt — hooks fix files but exit 1
git add -A
git commit -m "descriptive message"

# Hooks modified files, commit failed. Re-stage and commit again:
git add -A
git commit -m "descriptive message"
```

This is better than `--no-verify` because the hooks actually fix the files — you just need to stage their fixes.

**Unstage accidentally-added large files:**
If `git add -A` staged files that exceed `check-added-large-files` limits (default 1000KB), remove them from the index before retrying:
```bash
git reset HEAD -- "path/to/large/file.png" "path/to/archive.tar.gz"
# Then add .gitignore entries and re-add:
echo "path/to/large/*.png" >> .gitignore
git add -A
git commit -m "descriptive message"
```

**Black formatter timeout:** On large repos with many Python files, `black` in pre-commit can take 30+ seconds and cause commit timeouts. Use `git commit` with a timeout of at least 120 seconds, or use `--no-verify` if CI will catch formatting later.

## 7. Push Over Slow / Unreliable Links

For very large histories, push may timeout. If possible:

- Push in background and poll:
  ```bash
  git push origin master &
  ```
- Or use `git push --thin` to reduce pack size.
- Ensure large files are excluded (see step 5) before committing.

## 8. Verify the Remote State

After push, confirm the remote received the commit:

```bash
# Local check
git log --oneline origin/master -3

# Or query the remote via API (requires auth header)
curl -s \
  -H "Authorization: Bearer <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/commits/master \
  | python3 -c "import sys,json; c=json.load(sys.stdin)['commit']; print(c['message'][:60])"
```

## 9. Temporary Token-Embedded Remote (Last Resort)

If no credential helper is available and you must push via HTTPS with a token:

```bash
# 1. Set the remote with the token embedded (not persisted)
git remote set-url origin "https://<USER>:<TOKEN>@github.com/<USER>/<REPO>.git"

# 2. Push
git push -u origin master

# 3. Immediately strip the token from .git/config
git remote set-url origin "https://github.com/<USER>/<REPO>.git"
```

Never leave the token in the remote URL — any `git remote -v` would expose it.

## Quick Checklist

- [ ] `git count-objects -vH` — garbage size is 0
- [ ] `find . -type f -size +50M -not -path './.git/*'` — no surprises
- [ ] `.gitignore` updated before `git add -A`
- [ ] `git diff --cached --stat` completes quickly
- [ ] Commit succeeds (`--no-verify` if hooks misbehave)
- [ ] Push completes without timeout
- [ ] Remote URL cleaned of credentials
