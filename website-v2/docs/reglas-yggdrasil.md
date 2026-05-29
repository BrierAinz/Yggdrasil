---
sidebar_position: 8
title: Yggdrasil Rules
---

# Yggdrasil Rules

Fundamental laws of the ecosystem.

## Monorepo Rules

1. **Each realm has a purpose.** Don't mix responsibilities.
2. **Svartalfheim is the source of truth.** All documentation lives there.
3. **lilith-* packages are modular.** Each has its own pyproject.toml.
4. **Scripts go in Scripts/.** No loose scripts in root.
5. **Plans follow plan-NN-*.md.** Sequential numbering in plans/.
6. **Dead projects go to Helheim.** Don't delete, archive with reason and date.
7. **.env is never committed.** Use .env.example as template.
8. **Models go to Niflheim.** Excluded from git.
9. **Python >=3.11.** Minimum requirement.
10. **Commits prefixed with realm.** Format: `[REALM] type: description`

## Commit Convention

```
[ASGARD] feat: new module in lilith-core
[MUSPELHEIM] fix: dataset generation bug
[SVARTALFHEIM] docs: update API documentation
[ALL] chore: update dependencies
```

Types: feat, fix, docs, style, refactor, test, chore

## Realm Organization

| Realm | Allowed | Not Allowed |
|-------|---------|-------------|
| Asgard | lilith-* packages | Docs, loose scripts |
| Vanaheim | Agent frameworks | Specific implementations |
| Alfheim | UIs, dashboards | Backend logic |
| Svartalfheim | Docs, scripts, plans | Application code |
| Muspelheim | WIP projects | Stable projects |
| Niflheim | Models, datasets | Code |
| Helheim | Dead projects | Active projects |
| Jotunheim | Large projects | Small projects |
| Midgard | Personal projects | Ecosystem projects |
