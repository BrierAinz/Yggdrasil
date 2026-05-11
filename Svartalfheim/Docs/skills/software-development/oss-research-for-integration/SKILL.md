---
name: oss-research-for-integration
description: Investigate open-source projects on GitHub to extract architecture patterns, features, and methodologies for integration into a personal ecosystem. Covers API scraping, README analysis, skill extraction, and structured summarization.
trigger: When the user asks to research GitHub repos, web ecosystems (multi-site/multi-subdomain analysis), or competitor projects for inspiration, architecture ideas, design patterns, or feature integration into their own project ecosystem.
---

# OSS Research for Integration

## Purpose
Systematically investigate open-source repositories to extract actionable insights for integration into a personal project ecosystem. Goes beyond "what is this" to "how can I adopt/adapt this."

## Workflow

### 1. Repository Discovery & Metadata
For each repo, fetch via GitHub API:
```bash
curl -s https://api.github.com/repos/{owner}/{repo}
```

Extract:
- Stars, forks, language, license, size
- Description, topics, created/updated dates
- Open issues count (indicator of maturity/activity)

### 2. Deep Content Extraction
Fetch key files in priority order:
1. `README.md` — features, architecture, installation
2. `AGENTS.md` or `CLAUDE.md` — agent instructions, dev workflow
3. `Cargo.toml` / `package.json` / `pyproject.toml` — dependencies, features flags
4. `docs/` or `PLAN_*.md` — implementation plans, RFCs
5. `.github/` — PR templates, issue templates
6. `skills/` or `.claude/skills/` — skill definitions (if agent framework)

Use Python with `urllib.request` when `jq` is unavailable:
```python
import urllib.request, json

def fetch_raw(owner, repo, path, branch="main"):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='replace')
```

### 2B. Web Ecosystem Analysis (for multi-site competitors)
When researching a company's full web presence (not just a single repo):
1. **Enumerate subdomains** — Start from the main site, then visit every linked subdomain.
2. **Identify tech stack per subdomain** — Check for WordPress (Elementor patterns), Shopify, custom SPA, Next.js, etc. Use `document.body.innerHTML` sampling and `getComputedStyle` for CSS details.
3. **Extract design tokens** — Color palettes, typography (font-family, size hierarchy), spacing patterns, border styles, animation/motion FX.
4. **Catalog content structure** — Navigation items, section headings, feature lists, CTAs, code blocks with copy buttons.
5. **Capture interactivity** — Canvas/WebGL usage, scroll animations, dark/light toggles, search/filter functionality, wallet integrations, leaderboards.
6. **Produce cross-cutting analysis** — Compare design language across subdomains, identify shared patterns (badges, monospace accents, generative signatures), note what varies (psyche is cyberpunk vs. hermes-agent is warm minimalist).
7. **Derive actionable takeaways** — Map each pattern to a concrete feature for the user's project.

Use `browser_navigate`, `browser_snapshot`, `browser_scroll`, and `browser_console` (for extracting `getComputedStyle`, innerHTML, CSS variables) to gather data programmatically when vision isn't available.

### 3. Skill/Framework Analysis
If the repo is an agent framework or methodology (e.g., Superpowers), extract:
- Skill directory structure
- Individual SKILL.md files with frontmatter
- Plugin manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`)
- Core methodology documents

Store skill excerpts in `references/` for later adaptation.

### 4. Architecture Pattern Extraction
For structural repos (e.g., jcode's crate workspace), extract:
- Module/crate boundaries and responsibilities
- Feature flags and optional dependencies
- Plugin/extension architecture
- Configuration file schemas

### 5. Structured Summarization
Produce a report with these sections per project:

```
1. {REPO} ({owner}/{repo})
   ───────────────────────────────────────
   Type: {what it is}
   Language: {primary language}
   Stats: {stars}★ | {forks}⎇ | {size}KB | {license}
   
   KEY FEATURES:
   • {bullet list of standout capabilities}
   
   ARCHITECTURE:
   • {structural patterns}
   
   FOR {TARGET_ECOSYSTEM}:
   → {specific integration recommendation}
   → {specific integration recommendation}
```

### 6. Integration Roadmap
After analyzing all repos, propose a phased integration plan:
- **Phase 1 (Immediate)**: Methodology/process changes
- **Phase 2 (Short-term)**: Architecture/code changes
- **Phase 3 (Medium-term)**: UI/infrastructure changes

## References
- `references/ghostty-analysis.md` — Terminal emulator patterns for dashboard UI
- `references/superpowers-skills.md` — Superpowers skill definitions extracted (13 skills, TDD methodology)
- `references/jcode-architecture.md` — jcode crate structure, memory system, MCP support, swarm coordination
- `references/nous-research-ecosystem.md` — Full competitive analysis of Nous Research web ecosystem (10 subdomains, tech stacks, design patterns, takeaways for BrierStudios)

## Pitfalls
- **Don't just list features** — always translate to "what this means for our ecosystem"
- **Don't ignore the license** — MIT/Apache = safe, GPL = viral, proprietary = blocked
- **Check last updated** — stale repos (>6 months) may not be worth adopting
- **Size matters** — a 400MB Rust project may not fit a Python ecosystem
- **Don't copy blindly** — adapt patterns, don't transplant code
- **Watchdog hot-reload tests fail in WSL/tmpfs** — `watchdog` uses inotify which doesn't work reliably on tmpfs or WSL virtual filesystems. Skip hot-reload tests in CI/test environments; verify manually on real Windows/Linux filesystems. Use retry loops instead of fixed sleeps when testing async file watchers.
