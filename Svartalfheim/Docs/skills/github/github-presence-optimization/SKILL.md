---
name: github-presence-optimization
title: Optimize GitHub Project Presence
description: Enhance a GitHub repository's discoverability, professionalism, and community engagement. Covers Topics, community health files (SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md), Issue/PR templates, Dependabot, badges, social preview images, Discussions, Projects v2, profile READMEs, release configuration, demo assets, and SSG selection for project sites.
trigger: When the user wants to improve how their GitHub project looks, increase discoverability, add community infrastructure, set up CI hygiene, choose a static site generator, or generally level-up a repo's professionalism.
related_skills:
  - github-pages-project-site
  - github-repo-management
  - github-issues
  - github-pr-workflow
---

# Optimize GitHub Project Presence

A systematic approach to transforming a GitHub repo from "functional but bare" into a polished, discoverable, professionally-presented project. Ordered by impact-to-effort ratio.

## Phase 1: Quick Wins (2–30 min each, high impact)

### 1.1 GitHub Topics
- Settings → About → gear icon → Topics field
- Add 5–15 topics: `ai-agent`, `local-ai`, `python`, `fastapi`, `telegram-bot`, `monorepo`, `ecosystem`, etc.
- Impact: **HIGH** — primary discovery mechanism on GitHub search
- Also doable via API:
  ```bash
  curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.mercy-preview+json" \
    https://api.github.com/repos/$OWNER/$REPO/topics \
    -d '{"names": ["ai-agent","python","ecosystem"]}'
  ```

### 1.2 Community Health Files
| File | Location | Priority |
|------|----------|----------|
| SECURITY.md | Repo root | MUST-HAVE |
| CODE_OF_CONDUCT.md | Repo root | MUST-HAVE |
| CONTRIBUTING.md | Repo root | MUST-HAVE (may exist) |
| FUNDING.yml | `.github/` | Nice-to-have |

**SECURITY.md** template:
```markdown
# Security Policy
## Supported Versions
| Version | Supported |
| ------- | --------- |
| >= 4.0  | ✅        |
| < 4.0   | ❌        |
## Reporting a Vulnerability
Email [your-email] or open a private Security Advisory. 
Response within 48h, fix within 30 days.
```

**CODE_OF_CONDUCT.md**: Use Contributor Covenant v2.1 (GitHub can auto-generate).

### 1.3 Issue & PR Templates
```
.github/
  ISSUE_TEMPLATE/
    bug_report.yml      # Structured bug reports
    feature_request.yml # Feature proposals
    config.yml          # Disable blank issues, link to Discussions
  PULL_REQUEST_TEMPLATE.md
```

PR template should include: realm/module affected, test plan, checklist items.

### 1.4 Release Notes Configuration
`.github/release.yml`:
```yaml
changelog:
  exclude:
    labels:
      - ignore-for-release
      - dependencies
    authors:
      - dependabot[bot]
  categories:
    - title: "🚀 Features"
      labels: [enhancement, feature]
    - title: "🐛 Bug Fixes"
      labels: [bug, fix]
    - title: "📖 Documentation"
      labels: [documentation]
    - title: "🔧 Dependencies"
      labels: [dependencies]
    - title: "🧹 Other Changes"
      labels: ["*"]
```

### 1.5 Dependabot
`.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 1.6 Badges (shields.io)
Add to README header, max 2 rows of 4–5 each:
- CI status: `[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)]()`
- Deploy status, Website status
- License, Python version, pre-commit
- GitHub Discussions (if enabled), Open Issues count
- "PRs Welcome" badge linking to CONTRIBUTING.md

### 1.7 Social Preview Image
- Create 1280×640px PNG preferred; SVG also works (GitHub accepts both)
- Upload via Settings → General → Social preview
- Dark theme recommended: radial gradient bg (#0B0F19), amber (#F59E0B) + cyan (#22D3EE) accents
- If no image generation API available, hand-craft an SVG with `<filter>` glow effects and rune decoration
- Convert SVG to PNG: `inkscape file.svg -w 1280 -h 640 -e file.png` or `chromium --headless --screenshot`
- Impact: **HIGH** — 2–3x CTR on link shares

---

## Phase 2: Structural Enhancements (1–4 hrs each)

### 2.1 Profile README (`BrierAinz/BrierAinz`)
Create a repo matching your username with a README that:
- Introduces you with a tagline
- Highlights current project (Yggdrasil)
- Shows tech stack badges
- Embeds github-readme-stats cards (dark theme: `&theme=dark`)
- Links to all project repos

### 2.2 Demo GIF / Asciinema
- Record startup flow: clone → configure → launch → Telegram command
- Use `asciinema rec` for CLI demos, Peek/LICEcap for GUI
- Keep under 5MB, 15–30 seconds
- Embed in README after the hero section

### 2.3 Collapsible README Sections
```html
<details><summary>⚙️ Advanced Configuration</summary>
Content hidden by default...
</details>
```

### 2.4 DevContainer (`.devcontainer/devcontainer.json`)
Enables one-click GitHub Codespaces. Include Python, extensions, and post-create commands.

### 2.5 AI Agent Config (`.claude/CLAUDE.md`)
Emerging pattern from Nx and AutoGPT — project context file for AI coding assistants. Include: project structure, conventions, key paths, testing commands.

### 2.6 CODEOWNERS
Map realm directories to maintainers. Even solo projects benefit — signals ownership intent.

---

## Phase 3: Community & Automation

### 3.1 GitHub Discussions
Enable in Settings → Features. Create categories:
- Announcements (maintainers only)
- Ideas and Feature Requests
- Q&A (answers can be marked)
- Show and Tell

### 3.2 GitHub Projects v2
Create a board with custom fields:
- **Status**: Backlog → In Progress → Review → Done
- **Realm**: Asgard, Vanaheim, ..., Helheim (single select)
- **Priority**: Critical, High, Medium, Low
- **Milestone**: Iteration field for phases

### 3.3 Additional Workflows
- **Stale bot** (`.github/workflows/stale.yml`): Mark issues/PRs stale after 30d
- **Greeting bot** (`greeting.yml`): Welcome first-time contributors
- **Auto-README stats** (weekly): Update dynamic metric badges

### 3.4 Data-Driven READMEs
For ecosystem/repos with structured content:
- Create `yggdrasil-data/` with YAML/JSON project manifests
- Generate realm tables and status sections from data
- CI validates that data and README stay in sync

---

## SSG Selection for Project Sites

When the project website needs more than static HTML, choose a Static Site Generator:

| SSG | Setup | Dark Theme | Mermaid | Search | GH Pages | Best For |
|-----|-------|-----------|---------|--------|----------|----------|
| **Docusaurus** | Medium | Excellent | Official | Algolia (free OSS) | Actions | Ecosystems with multiple components, versioning |
| **MkDocs Material** | Easy-Med | Excellent (slate) | Native | Built-in Lunr | gh-deploy | Polished docs, easiest dark theme |
| **Just the Docs** (Jekyll) | Easy | Basic | Plugin | Built-in Lunr | Native | Simple documentation |
| **Astro** | Med-Hard | DIY | Integration | Pagefind | Actions | Maximum creative control, portfolio showcase |
| **Plain HTML** | N/A | Custom | Manual JS | Must add | Native | Minimal, rarely updated |

**Recommendation hierarchy:**
1. **Docusaurus** — best for project ecosystems (MDX, Showcase feature, versioning, React components)
2. **MkDocs Material** — best for documentation-heavy projects (fastest path to polished dark theme)
3. **Astro** — best for highly custom creative sites (island architecture, any framework components)

See `references/ssg-comparison.md` for full decision matrix.

---

## Programmatic GitHub API Operations (without `gh` CLI)

When `gh` CLI is unavailable or not authenticated, use `git credential fill` + Python `urllib.request` for API operations. This is more reliable than parsing `~/.git-credentials` directly (works with any credential helper, not just `store`).

### Primary Method: `git credential fill` + `urllib.request`

```python
import subprocess, urllib.request, json

def get_github_token():
    """Extract GitHub token from git credential helper (works with store, cache, etc.)."""
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, timeout=10
    )
    for line in result.stdout.strip().split('\n'):
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return None

def gh_api(path, method="GET", data=None, token=None):
    """Call GitHub REST API. Returns parsed JSON or status dict."""
    if not token:
        token = get_github_token()
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "YggdrasilBot")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        if resp.status == 204:
            return {"status": "success", "code": 204}
        return json.loads(resp.read())
```

### Common Operations

```python
# Get repo info
repo = gh_api("/repos/OWNER/REPO")
print(f"Description: {repo['description']}")
print(f"Homepage: {repo['homepage']}")
print(f"Has wiki: {repo['has_wiki']}")

# Patch repo settings (description, homepage, wiki, etc.)
gh_api("/repos/OWNER/REPO", method="PATCH", data={
    "description": "New description",
    "homepage": "https://owner.github.io/repo/",
    "has_wiki": False
})

# Set topics (PUT replaces all topics)
gh_api("/repos/OWNER/REPO/topics", method="PUT", data={
    "names": ["python", "ai", "fastapi", "ecosystem"]
})

# Commit a file to a repo (profile README update)
# Step 1: Get current file SHA
current = gh_api("/repos/OWNER/REPO/contents/README.md")
sha = current["sha"]
# Step 2: Create new blob
import base64
new_content = base64.b64encode(b"New README content").decode()
gh_api("/repos/OWNER/REPO/contents/README.md", method="PUT", data={
    "message": "Update README",
    "content": new_content,
    "sha": sha
})

# Enable discussions
gh_api("/repos/OWNER/REPO", method="PATCH", data={"has_discussions": True})
```

### Fallback: `~/.git-credentials` file + `curl`

If Python `urllib` is unavailable, fall back to reading the credential file directly and using `curl`:

```bash
# Extract token (only works with 'store' credential helper)
GITHUB_TOKEN=$(grep github.com ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')

# Patch repo description
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO \
  -d '{"description": "New description"}'

# Set topics
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.mercy-preview+json" \
  https://api.github.com/repos/OWNER/REPO/topics \
  -d '{"names": ["python", "ai"]}'
```

Key steps:
1. Prefer `git credential fill` over file parsing — works with ANY credential helper (store, cache, osxkeychain, etc.)
2. Use `Authorization: token {token}` header (not Bearer)
3. Topics API requires `Accept: application/vnd.github.mercy-preview+json` (for PUT)
4. Profile repo name MUST exactly match the GitHub username
5. `PATCH /repos/OWNER/REPO` for description, homepage, wiki, discussions
6. `PUT /repos/OWNER/REPO/topics` replaces ALL topics (send the full list)

### Audit-Identify-Fix-Verify Workflow

Use this systematic pattern when optimizing a repo's presence:

1. **AUDIT**: Fetch repo info, profile README, topics, and settings via API
2. **IDENTIFY**: Compare current state against best practices — list specific discrepancies with proposed fixes
3. **FIX**: Apply all changes via API calls (description, homepage, topics, wiki, etc.)
4. **VERIFY**: Re-fetch all modified fields and confirm each change stuck

This pattern caught 9 issues in a real session: outdated description, missing homepage, wiki enabled when Docusaurus replaces it, missing topics, profile README referencing old project names.

## Pitfalls

- **Don't add all badges at once** — max 2 rows of 4–5. More becomes noise.
- **Don't enable Discussions and Projects** before you have bandwidth to engage — empty community spaces look worse than none.
- **Topics have a practical limit** — 5–15 optimal, GitHub accepts up to ~20 but relevance degrades.
- **Social preview must be exactly 1280×640px** — other sizes get cropped badly. SVGs work too if the project has no raster image capability.
- **DevContainers cost minutes on first launch** — skip if your project starts in < 60 seconds locally.
- **Dependabot on monorepos** — specify subdirectory paths with `directory:` per ecosystem.
- **Profile README is per-account** — the repo name must exactly match the GitHub username (`BrierAinz/BrierAinz`).
- **CI badges break** if the workflow filename changes — use stable URLs.
- **Pre-commit hooks auto-fix files** — after committing, pre-commit may fix trailing whitespace/EOF. Re-stage fixed files with `git add -u` and amend or re-commit.
- **Selective staging in mixed-work trees** — when the working tree has changes from multiple logical tasks, `git add` each file individually rather than `git add -A` to avoid mixing unrelated changes in one commit.
- **GitHub token from credential-store may have limited scopes** — a `ghp_` token that works for `git push` may need `repo` scope for API writes like topics. If API returns 404/403, the token lacks scope.
- **`gh auth login --with-token` gives 401 with git-credential tokens** — tokens from `git credential fill` or `~/.git-credentials` do NOT work with `gh auth login --with-token`. They lack the OAuth scopes `gh` requires. Use `gh auth login --web` (device flow) instead, or skip `gh` entirely and use the `gh_api()` Python helper.
- **`git credential fill` is more reliable than file parsing** — `git credential fill` works with ANY credential helper (store, cache, osxkeychain, manager), while reading `~/.git-credentials` only works with the `store` helper. Always prefer `git credential fill`.
- **Wiki → Docusaurus migration** — if the project has a Docusaurus/SSG site deployed on GitHub Pages, disable the wiki (`has_wiki: False`) to avoid duplicate documentation. Docusaurus replaces it.
- **Audit–Identify–Fix–Verify beats ad-hoc changes** — systematically fetch all repo fields, compare to best practices, list discrepancies, apply fixes, then re-fetch to confirm. This catches issues ad-hoc approaches miss (stale descriptions, missing homepage URLs, enabled features that should be disabled).

## References
- `references/quick-wins-checklist.md` — Prioritized checklist with time estimates
- `references/ecosystem-research-findings.md` — Detailed analysis of 15+ top GitHub projects
- `templates/norse-issue-templates.yml` — Themed bug/feature/config issue templates ready to copy
- `references/yggdrasil-audit-example.md` — Worked example: 9-issue audit with API calls and fixes
- `templates/social-preview-design-guide.md` — Design spec for SVG social preview images