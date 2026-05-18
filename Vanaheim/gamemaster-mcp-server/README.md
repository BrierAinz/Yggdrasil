# 🎲 GameMaster MCP Server

Character creation agent for AI chat platforms (Caveduck, Tipsy Chat). Exposed as FastMCP server for invocation from Hermes and external apps.

## Quick Start

```bash
# Install (from Yggdrasil root)
cd /mnt/d/Proyectos/Yggdrasil
uv sync --package gamemaster-mcp-server

# Run MCP server
uv run gamemaster-mcp-server

# Or with Hermes MCP config
# Add to ~/.hermes/config.yaml:
# mcp_servers:
#   gamemaster:
#     command: uv
#     args: ["run", "--package", "gamemaster-mcp-server", "gamemaster-mcp-server"]
```

## Tools

| Tool | Description |
|------|-------------|
| `ideate_characters` | Generate character concepts by genre |
| `create_character_sheet` | Full character sheet (name, desc, greeting, personality, scenario, tags) |
| `analyze_trending` | Analyze trending characters on a platform |
| `suggest_tags` | Suggest optimal tags for maximum visibility |
| `generate_character_image` | Generate character card image via ComfyUI |

## Architecture

GameMaster is a **separate agent** from Lilith. Lilith remains the brand/mascot of Yggdrasil. GameMaster is functional — no goddess roleplay.

```
Hermes ──→ GameMaster MCP Server (FastMCP) ──→ GameMaster Agent
                        │
External apps ──────────┘  (Caveduck, Tipsy, etc.)
```

## Platform Support

| Platform | Creation | Trending | Tags |
|----------|----------|----------|------|
| Caveduck | ✅ | ✅ | ✅ |
| Tipsy Chat | ✅ | ✅ | 🔄 |

## Norse Naming Convention

Part of Vanaheim (AI agents realm) in Yggdrasil. GameMaster = the norse god of games and strategy.
