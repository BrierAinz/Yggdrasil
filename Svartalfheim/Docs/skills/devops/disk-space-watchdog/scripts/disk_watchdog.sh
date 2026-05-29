#!/usr/bin/env bash
# ~/.hermes/scripts/disk_watchdog.sh
# Disk space watchdog for WSL2 + Windows mounts
# Called by cron or manually — alerts on CRITICAL (<5 GiB) and WARNING (<15 GiB)
set -euo pipefail

CRITICAL_THRESHOLD=$((5 * 1073741824))   # 5 GiB
WARNING_THRESHOLD=$((15 * 1073741824))    # 15 GiB
MOUNTS=("/" "/mnt/c" "/mnt/d" "/mnt/e")
ALERTS=()

for mount in "${MOUNTS[@]}"; do
    # Skip mounts that aren't available
    if ! mountpoint -q "$mount" 2>/dev/null && [ "$mount" != "/" ]; then
        echo "$(date -Iseconds) [SKIP] $mount — not mounted"
        continue
    fi

    avail=$(df -B1 "$mount" | tail -1 | awk '{print $4}')
    avail_gib=$((avail / 1073741824))

    if [ "$avail" -lt "$CRITICAL_THRESHOLD" ]; then
        msg="$(date -Iseconds) [CRITICAL] $mount — ${avail_gib} GiB free (< 5 GiB threshold)"
        ALERTS+=("$msg")
        echo "$msg"
    elif [ "$avail" -lt "$WARNING_THRESHOLD" ]; then
        msg="$(date -Iseconds) [WARNING] $mount — ${avail_gib} GiB free (< 15 GiB threshold)"
        ALERTS+=("$msg")
        echo "$msg"
    else
        echo "$(date -Iseconds) [OK] $mount — ${avail_gib} GiB free"
    fi
done

if [ ${#ALERTS[@]} -gt 0 ]; then
    echo ""
    echo "=== CLEANUP SUGGESTIONS ==="
    echo "Safe to delete (auto-regenerate):"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/DXCache/*"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/D3DSCache/*"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/pip/cache/*"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/npm-cache/*"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/Temp/*"
    echo "  rm -rf /mnt/c/Users/Game_/AppData/Local/CrashDumps/*"
    echo ""
    echo "For VHDX compaction (run from PowerShell Admin):"
    echo "  wsl --shutdown"
    echo '  Optimize-VHD -Path "C:\Users\Game_\AppData\Local\wsl\{GUID}\ext4.vhdx" -Mode Full'
    exit 1
fi

exit 0