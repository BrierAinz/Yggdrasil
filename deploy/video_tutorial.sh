#!/bin/bash
# Lilith Agent — Video Tutorial Generator
# Creates a terminal recording script for demo purposes
set -e

OUTPUT_DIR="${1:-/tmp/lilith-demo}"
mkdir -p "$OUTPUT_DIR"

cat > "$OUTPUT_DIR/demo.sh" << 'DEMO'
#!/bin/bash
# Lilith Agent Demo Script
# Run with: asciinema rec demo.cast -c "bash demo.sh"

set -e
DELAY=0.05

type_text() {
    echo -n "$ "
    for (( i=0; i<${#1}; i++ )); do
        echo -n "${1:$i:1}"
        sleep $DELAY
    done
    echo
    sleep 0.5
    eval "$1"
    sleep 1
}

clear
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     ᛚ        LILITH         ᛚ                                ║"
echo "║                                                               ║"
echo "║     Dark Goddess of Yggdrasil Digital                         ║"
echo "║     Full Coding CLI Agent                                     ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
sleep 2

echo "Features:"
echo "  ᛏ 59 tools (code, files, git, web, media, memory)"
echo "  ᛒ 13 providers (DeepSeek, Alibaba, BytePlus)"
echo "  ᚨ Persistent memory & reusable skills"
echo "  ᛟ Safety confirmations for destructive ops"
echo "  ᚱ Background processes & parallel execution"
echo ""
sleep 2

echo "── Example: Interactive Chat ──"
echo ""
type_text "lilith --provider qwen3.7"
sleep 2

echo "── Example: Single Message ──"
echo ""
type_text "lilith -m 'read REGLAS_YGGDRASIL.md and count the rules'"
sleep 2

echo "── Example: Code Analysis ──"
echo ""
type_text "lilith -m 'analyze lilith_agent.py structure'"
sleep 2

echo "── Example: Memory ──"
echo ""
type_text "lilith -m 'remember: user prefers dark themes'"
sleep 1
type_text "lilith -m 'what do you know about user preferences?'"
sleep 2

echo "── Example: Skills ──"
echo ""
type_text "lilith -m 'save this workflow as a skill called deploy-pipeline'"
sleep 2

echo "── Example: Background Process ──"
echo ""
type_text "lilith -m 'run pytest in the background'"
sleep 2

echo "── Example: Multi-provider ──"
echo ""
echo "Providers available:"
echo "  deepseek     — deepseek-chat (direct)"
echo "  qwen3.7      — qwen3.7-max (Alibaba free)"
echo "  qwen-max     — qwen-max-latest (Alibaba free)"
echo "  qwen-plus    — qwen-plus-latest (Alibaba free)"
echo "  qwen-turbo   — qwen-turbo-latest (Alibaba free)"
echo "  ds-v4-flash  — deepseek-v4-flash (Alibaba free)"
echo "  seed-1.6     — seed-1-6-250915 (BytePlus)"
echo ""
sleep 2

echo "── Slash Commands ──"
echo ""
echo "  /quit        — Exit"
echo "  /clear       — Reload context"
echo "  /memory      — Show saved sessions"
echo "  /skills      — List saved skills"
echo "  /knowledge   — Show all known facts"
echo "  /profile     — Token/cost/performance stats"
echo "  /fork        — Save conversation branch"
echo "  /provider    — Switch LLM provider"
echo ""
sleep 2

echo "── Documentation ──"
echo ""
echo "  LILITH_README.md    — Full guide"
echo "  LILITH_ROADMAP.md   — 96% complete"
echo "  LILITH_TOOLS.md     — 59 tool reference"
echo ""
sleep 1

echo "Install: pip install lilith-agent"
echo "Or:      python3 lilith_agent.py"
echo ""
echo "ᛒᚱᛁᛖᚱᛊᛏᚢᛞᛁᛟᛊ — The forge burns eternal."
DEMO

chmod +x "$OUTPUT_DIR/demo.sh"

echo ""
echo "Demo script created: $OUTPUT_DIR/demo.sh"
echo ""
echo "To record:"
echo "  asciinema rec $OUTPUT_DIR/demo.cast -c 'bash $OUTPUT_DIR/demo.sh'"
echo ""
echo "To convert to GIF:"
echo "  agg $OUTPUT_DIR/demo.cast $OUTPUT_DIR/demo.gif"
echo ""
echo "To convert to MP4:"
echo "  ffmpeg -i $OUTPUT_DIR/demo.cast $OUTPUT_DIR/demo.mp4"
