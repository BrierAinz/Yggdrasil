#!/bin/bash
# Yggdrasil Health Check
YGG_ROOT="${YGGDRASIL_ROOT:-/home/brierainz/Proyectos/Yggdrasil}"
echo "=== Yggdrasil Health Check ==="
echo "Root: $YGG_ROOT"
echo ""

# Check Python
echo "[Python]"
python3 --version
echo ""

# Check .venv
echo "[Venv]"
if [ -d "$YGG_ROOT/.venv" ]; then
    echo "  .venv: OK ($($YGG_ROOT/.venv/bin/python --version 2>&1))"
else
    echo "  .venv: MISSING"
fi
echo ""

# Check realms
echo "[Realms]"
for realm in Asgard Alfheim Vanaheim Muspelheim Niflheim Svartalfheim Midgard Helheim Jotunheim; do
    count=$(find "$YGG_ROOT/$realm" -type f 2>/dev/null | wc -l)
    echo "  $realm: $count files"
done
echo ""

# Check packages
echo "[Asgard Packages]"
for pkg in lilith-core lilith-memory lilith-tools lilith-orchestrator lilith-api lilith-cli lilith-skills lilith-bridge; do
    if [ -f "$YGG_ROOT/Asgard/$pkg/pyproject.toml" ]; then
        echo "  $pkg: OK"
    else
        echo "  $pkg: MISSING"
    fi
done
echo ""

echo "=== Done ==="
