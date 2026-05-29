---
sidebar_position: 8
title: lilith-cli
---

# lilith-cli

Interactive CLI for Yggdrasil. REPL with autocompletion, history, and command system.

## Commands

```
lilith> /help          Show available commands
lilith> /status        System status
lilith> /memory search Search memory
lilith> /tools list    List tools
lilith> /config show   Show configuration
lilith> /exit          Exit CLI
```

## Usage

```bash
# Start interactive mode
uv run lilith-cli

# Single command
uv run lilith-cli --command "/status"
```
