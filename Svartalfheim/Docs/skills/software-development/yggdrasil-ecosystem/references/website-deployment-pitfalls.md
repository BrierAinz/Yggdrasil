# Website Deployment Pitfalls (Docusaurus + GitHub Pages)

## First Deploy: gh-pages Branch Must Exist

When deploying Docusaurus for the first time via `npm run deploy`, the remote must already have a `gh-pages` branch. If it doesn't exist:

```
fatal: Remote branch gh-pages not found in upstream origin
```

**Fix**: Create it via a temp clone:
```bash
tmp=$(mktemp -d)
git clone --depth=1 https://github.com/BrierAinz/Yggdrasil.git "$tmp"
cd "$tmp"
git checkout --orphan gh-pages
git rm -rf .
git commit --allow-empty -m "init gh-pages"
git push origin gh-pages
cd -
rm -rf "$tmp"
```

Then re-run `npm run deploy`. After the first successful deploy, the branch persists and this isn't needed again.

## Git Identity Required for Deploy

`npm run deploy` does a `git commit` internally. If `git config --global user.name/email` is unset:

```
fatal: empty ident name not allowed
```

**Fix**:
```bash
git config --global user.name "BrierAinz"
git config --global user.email "brierainz@users.noreply.github.com"
```

Set once per machine; persists across sessions.

## Docusaurus Stale Cache After Content Edits

After editing `.mdx` files, the build cache may contain outdated HTML. The deployed site can show stale content even if source files are correct.

**Fix**: Clear all caches before rebuilding:
```bash
cd website-v2
rm -rf build .docusaurus node_modules/.cache
npm run build
```

Then redeploy. This is especially necessary after a failed deploy attempt.

## Orphan Branch Operations Destroy Uncommitted Changes

Running `git checkout --orphan gh-pages && git rm -rf .` wipes the working tree. **Any uncommitted patches will be lost**. The working tree becomes empty on the orphan branch, and switching back may not recover edits.

**Prevention**: Always `git add -A && git commit` before any orphan branch operations. If changes are lost, re-apply from edit history or re-patch.

## Agent Roster Update (May 2026)

Reduced from 8 agents to 4 core agents. The 3 removed agents (Crystal, Albedo, Archivero) have `NotImplementedError` stubs in `panteon/` to prevent `ImportError` crashes across 14+ importing files.

**Website files updated**:
- `docs/intro.mdx` — Agent table rewritten (4 rows only)
- `docs/changelog.mdx` — v4.0.0 row updated ("4 specialist agents"), Crystal removed from v3.9.0
- `docs/architecture.mdx` — Tree diagram shows "4 active agents (Shalltear, Adán, Eva, Odín)"

**Commit**: `0fb99eb` — "[WEBSITE] update agent tables: 4 active agents"

**Previous cleanup commit**: `e6659f3` — 34 files changed, -2100 lines (dead agent removal from codebase)

## GIT_USER Required for `docusaurus deploy`

`npx docusaurus deploy` fails with `Error: Please set the GIT_USER environment variable` unless explicitly provided.

**Fix**: Set `GIT_USER` when deploying:
```bash
cd website-v2
GIT_USER=BrierAinz npx docusaurus deploy
```

This does a full build + push to `gh-pages` branch in one command. No separate `git push` needed for the website — `docusaurus deploy` handles it.

## SVG Asset Edits — Only Source Matters

Static assets live in `website-v2/static/img/`. The `website-v2/build/` directory is gitignored — Docusaurus rebuilds it from source during `docusaurus build` or `deploy`. When fixing typos or updating SVGs, only edit files under `static/img/`. After pushing to `main`, run `docusaurus deploy` (or let CI handle it) to rebuild and publish.

**Common pitfall**: SVG text elements can have typos that are invisible in file names. Always grep for the text content inside SVGs when auditing brand assets:
```bash
grep -r 'YGGDRASIL\|YGGRASIL' website-v2/static/img/*.svg
```

The logo SVG `logo-yggdrasil.svg` has TWO text elements (main + shadow) — both must be updated when fixing the brand name.