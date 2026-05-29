# GitHub Presence Quick Wins Checklist

Priority-ordered checklist for improving a project's GitHub presence. Each item includes time estimate and impact rating.

## Must-Have (Do Today)

- [ ] **Add 5–15 GitHub Topics** (2 min) — Settings → About → gear → Topics
  - Impact: HIGH discoverability
- [ ] **Add `.github/release.yml`** (10 min) — Categorized auto-release-notes
  - Impact: HIGH professionalism
- [ ] **Add `.github/dependabot.yml`** (10 min) — pip + github-actions weekly
  - Impact: HIGH maintenance/security
- [ ] **Create `SECURITY.md`** (10 min) — Vulnerability reporting policy
  - Impact: HIGH (GitHub Community Standards requires)
- [ ] **Create `CODE_OF_CONDUCT.md`** (5 min) — Contributor Covenant v2.1
  - Impact: HIGH (GitHub Community Standards requires)
- [ ] **Add CI/Deploy/Wbsite badges to README** (10 min) — shields.io for each workflow
  - Impact: HIGH professionalism
- [ ] **Design & upload Social Preview image** (30 min) — 1280×640px, dark themed
  - Impact: HIGH (2–3x CTR on link shares)
- [ ] **Add `.github/ISSUE_TEMPLATE/`** (20 min) — bug_report.yml, feature_request.yml, config.yml
  - Impact: HIGH community polish
- [ ] **Add `.github/PULL_REQUEST_TEMPLATE.md`** (10 min) — Realm, tests, checklist
  - Impact: MEDIUM consistency
- [ ] **Add `.github/release.yml`** (10 min) — Categorized release notes config
- [ ] **Code quality in PR CI** (20 min) — ruff linting + mypy with `--output-format=github`
  - Impact: HIGH quality signal

## High Value (Do This Week)

- [ ] **Create Profile README** (`BrierAinz/BrierAinz` repo) (1 hr)
  - Transform "1 repo, bio: IDK" into professional portfolio
- [ ] **Record Demo GIF** (1 hr) — Asciinema or Peek, 15–30s, under 5MB
  - Impact: HIGH engagement
- [ ] **Add `.devcontainer/devcontainer.json`** (30 min) — One-click Codespaces
- [ ] **Add `.claude/CLAUDE.md`** (15 min) — AI assistant context (emerging pattern)
- [ ] **Add `CODEOWNERS`** (10 min) — Map realms to maintainers
- [ ] **Add collapsible README sections** (30 min) — `<details>` for advanced config
- [ ] **Enable GitHub Discussions** (5 min) + configure categories (25 min)

## Nice-to-Have (Do Eventually)

- [ ] **GitHub Projects v2 Kanban** (30 min) — Status, Realm, Priority, Milestone fields
- [ ] **FUNDING.yml** (5 min) — Ko-fi or BuyMeACoffee link
- [ ] **Stale bot workflow** (10 min) — `.github/workflows/stale.yml`
- [ ] **Greeting bot workflow** (10 min) — `.github/workflows/greeting.yml`
- [ ] **Auto-README stats workflow** (1 hr) — Weekly dynamic badge updates
- [ ] **Data-driven README** (2–3 hrs) — YAML manifests → generated realm tables
- [ ] **Monorepo-aware CI** (2–4 hrs) — Only test changed realms
- [ ] **CI linting REGLAS_YGGDRASIL.md** (1–2 hrs) — Validate project structure

## File Structure After Full Implementation

```
.github/
  FUNDING.yml
  release.yml
  dependabot.yml
  workflows/
    ci.yml                       # exists
    release.yml                  # exists
    deploy-website.yml           # exists
    pages.yml                    # exists
    stale.yml                    # NEW
    greeting.yml                 # NEW
    update-readme-stats.yml      # NEW
  ISSUE_TEMPLATE/
    bug_report.yml               # NEW
    feature_request.yml          # NEW
    config.yml                   # NEW
  DISCUSSION_TEMPLATE/
    q-a.yml
    idea.yml
  PULL_REQUEST_TEMPLATE.md      # NEW

Root additions:
  SECURITY.md                    # NEW
  CODE_OF_CONDUCT.md             # NEW
  CONTRIBUTING.md                # exists
  LICENSE                        # exists
  .devcontainer/devcontainer.json # NEW
  .claude/CLAUDE.md              # NEW
  CODEOWNERS                     # NEW
```