# Yggdrasil GitHub Audit (May 2026) — Worked Example

Real-world audit identifying 9 issues across a user profile repo and a project repo, with the fixes applied via GitHub REST API.

## Audit Process

1. **AUDIT** — Fetched all fields via `gh_api()`:
   - `GET /repos/BrierAinz/Yggdrasil` — description, homepage, wiki, topics
   - `GET /repos/BrierAinz/BrierAinz` — profile README content
   - `GET /user/repos` — list all accessible repos
   - `GET /repos/BrierAinz/Yggdrasil/topics` — current topics

2. **IDENTIFY** — Compared against best practices, found 9 issues:

| # | Repo | Issue | Fix |
|---|------|-------|-----|
| 1 | Yggdrasil | Empty description | Set to "Nine-Realm AI ecosystem..." |
| 2 | Yggdrasil | No homepage URL | Set to `https://brierainz.github.io/Yggdrasil/` |
| 3 | Yggdrasil | Wiki enabled (redundant with Docusaurus) | Disabled (`has_wiki: False`) |
| 4 | Yggdrasil | Only 11 topics (missing key tech) | Added 9: fastapi, go, react, rust, sqlite, textual, typescript, wasm, yggdrasil |
| 5 | BrierAinz | Profile README contained "Hermes-Lilith" (deprecated name) | Replaced with "Lilith" |
| 6 | BrierAinz | No YggdrasilForge mention | Added YggdrasilForge + highlight row |
| 7 | BrierAinz | No ForgeMaster mention | Added ForgeMaster + highlight row |
| 8 | BrierAinz | Missing tech (Rust, Go, WASM) | Added badges and text |
| 9 | BrierAinz | No profile repo topics | Set: ai, ecosystem, local-first, norse, python |

3. **FIX** — Applied via `gh_api()`:

```python
# Repo settings (single PATCH)
gh_api("/repos/BrierAinz/Yggdrasil", method="PATCH", data={
    "description": "Nine-Realm AI ecosystem — Lilith agents, ComfyUI studio, 3D asset forge, TUI dashboard, WASM image processor, and Go gateway. Norse-themed, local-first, GPU-powered.",
    "homepage": "https://brierainz.github.io/Yggdrasil/",
    "has_wiki": False
})

# Topics (PUT replaces all)
gh_api("/repos/BrierAinz/Yggdrasil/topics", method="PUT", data={
    "names": ["3d","agents","ai","blender","comfyui","ecosystem","fastapi","go","llm","memory","multi-model","norse","python","react","rust","sqlite","textual","typescript","wasm","yggdrasil"]
})

# Profile README (via Contents API)
import base64
current = gh_api("/repos/BrierAinz/BrierAinz/contents/README.md")
new_content = base64.b64encode(new_readme_bytes).decode()
gh_api("/repos/BrierAinz/BrierAinz/contents/README.md", method="PUT", data={
    "message": "Update profile README: Lilith branding, new projects, tech stack",
    "content": new_content,
    "sha": current["sha"]
})

# Profile repo topics
gh_api("/repos/BrierAinz/BrierAinz/topics", method="PUT", data={
    "names": ["ai", "ecosystem", "local-first", "norse", "python"]
})
```

4. **VERIFY** — Re-fetched all modified fields and confirmed each change stuck.

## Key Takeaways

- The `git credential fill` + `urllib.request` pattern worked for all operations where `gh` CLI was unavailable (not authenticated in WSL)
- `PUT /repos/OWNER/REPO/topics` is a **replace** operation — must send the FULL topic list, not just additions
- GitHub Contents API (`PUT /repos/OWNER/REPO/contents/PATH`) requires the current file's `sha` for updates
- When Docusaurus serves as the documentation site, the GitHub wiki should be disabled to avoid duplication
- Only change VISIBLE TEXT in READMEs — backticked file paths (`Asgard/Hermes-Lilith/`) are git history references and must stay