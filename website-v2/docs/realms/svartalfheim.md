---
sidebar_position: 1
title: "Svartalfheim — Docs & Scripts"
---

# Svartalfheim — Docs & Scripts

The realm of the dark dwarves. All documentation, scripts, plans, and the ancestral memory of the ecosystem.

## Structure

```
Svartalfheim/
├── Docs/           # Main documentation
├── Knowledge_Base/ # Lilith knowledge base (101 files)
├── Scripts/        # Automation scripts (22 files)
├── plans/          # Implementation plans (21 plans)
├── wiki/           # ADRs, features, runbooks
└── notes/          # Quick notes
```

## Rules

1. Documentation and scripts only
2. Scripts live in `Scripts/`
3. Plans follow `plan-NN-*.md` format
4. Wiki is sacred (ADRs, runbooks, features)
5. `Lilith_Docs` is the living source
6. `Lilith_Legacy` is read-only

## Key Contents

### Knowledge Base
- **Lilith_Docs/** — Active documentation (101 files)
- **Lilith_Legacy/** — Inherited knowledge from the monolith

### Scripts (22 files)
- `ask_archivero.py` — Query the RAG archiver
- `index_docs_to_muninn.py` — Index documents to Muninn vault
- `health_check.sh` — Health verification
- Various test scripts

### Plans (21 plans)
- `plan-01-autosub.md` through `plan-18-forgemaster.md`
- Format: `plan-NN-name.md`

### Docs
- `API.md` — API documentation
- `ARCHITECTURE.md` — Detailed architecture
- `TUTORIALS.md` — Usage tutorials
- `github-presence-guide.md` — GitHub presence guide
