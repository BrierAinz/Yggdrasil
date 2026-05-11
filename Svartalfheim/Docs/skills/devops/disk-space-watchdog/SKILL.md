---
name: disk-space-watchdog
version: 1.0.0
description: Monitor disk space on WSL2 Windows mounts and WSL root, alert on thresholds, suggest automated cleanup, and manage cron-based watchdog.
tags: [wsl, disk-space, monitoring, cron, watchdog, alerting, devops]
triggers:
  - check disk space on WSL or Windows mounts
  - set up disk space monitoring or watchdog
  - disk full or nearly full alert
  - automate disk space checks with cron
related_skills:
  - wsl-windows-storage
---

# Disk Space Watchdog

Monitor disk space across WSL2 Windows mounts (`/mnt/c`, `/mnt/d`, `/mnt/e`) and WSL root (`/`), with threshold-based alerting and automated cleanup suggestions.

## Step 1: Check Disk Space

```bash
# Quick check all mounted drives + WSL root
df -h / /mnt/c /mnt/d /mnt/e
```

**Pitfall: `df` reports in GiB (1 GiB = 1,073,741,824 bytes) when `-h` is used, NOT in GB (1 GB = 1,000,000,000 bytes). The `-h` flag uses 1024-based units.** For rough estimates this is fine, but if you need GB-precision (e.g., comparing against a spec that says "500 GB"), use `df -H` (SI units, 1000-based) or convert manually:

```bash
# SI units (true GB/TB, 1000-based) — useful for comparison with spec sheets
df -H / /mnt/c /mnt/d /mnt/e

# Exact bytes for scripting
df -B1 / /mnt/c /mnt/d /mnt/e
```

**Pitfall: `df` shows whole-number GB/GiB rounded down.** A volume showing "5G" free might have 5.9 GiB or 4.1 GiB — you can't tell. For precise decisions, use `df -B1` and divide by 1073741824 (or 1000000000 for GB).

## Step 2: Threshold Alerting

| Level   | Free Space  | Action                                         |
|---------|-------------|------------------------------------------------|
| OK      | >= 15 GB    | No action                                      |
| WARNING | 5-15 GB     | Suggest cleanup, log warning                   |
| CRITICAL| < 5 GB      | Force cleanup suggestions, log urgent alert    |

**Pitfall: Thresholds are in GB (decimal, 10^9), but `df -h` shows GiB.** A 5 GB threshold ≈ 4.66 GiB. Use `df -B1` (whole bytes) for threshold comparison in scripts:

```bash
#!/bin/bash
# Threshold constants in bytes
CRITICAL=$((5 * 1073741824))   # 5 GiB ≈ 5.37 GB — using binary here for safety
WARNING=$((15 * 1073741824))   # 15 GiB ≈ 16.1 GB

for mount in / /mnt/c /mnt/d /mnt/e; do
    avail=$(df -B1 "$mount" | tail -1 | awk '{print $4}')
    if [ "$avail" -lt "$CRITICAL" ]; then
        echo "[CRITICAL] $mount has less than 5 GiB free ($((avail / 1073741824)) GiB remaining)"
    elif [ "$avail" -lt "$WARNING" ]; then
        echo "[WARNING] $mount has less than 15 GiB free ($((avail / 1073741824)) GiB remaining)"
    else
        echo "[OK] $mount: $((avail / 1073741824)) GiB free"
    fi
done
```

## Step 3: Automated Cleanup Suggestions

When a volume hits WARNING or CRITICAL, suggest these safe cleanups:

### Safe to Delete (Auto-regenerate)

| Target | Path (WSL) | Typical Savings | Command |
|--------|-----------|-----------------|---------|
| NVIDIA DXCache | `/mnt/c/Users/Game_/AppData/Local/NVIDIA/DXCache` | 5-15 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/DXCache/*` |
| NVIDIA D3DSCache | `/mnt/c/Users/Game_/AppData/Local/NVIDIA/D3DSCache` | 1-5 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/D3DSCache/*` |
| pip cache | `/mnt/c/Users/Game_/AppData/Local/pip/cache` | 1-5 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/pip/cache/*` |
| npm cache | `/mnt/c/Users/Game_/AppData/Local/npm-cache` | 1-3 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/npm-cache/*` |
| Windows Temp | `/mnt/c/Users/Game_/AppData/Local/Temp` | 1-10 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/Temp/*` |
| Crash Dumps | `/mnt/c/Users/Game_/AppData/Local/CrashDumps` | 0.5-2 GB | `rm -rf /mnt/c/Users/Game_/AppData/Local/CrashDumps/*` |

**Pitfall: Some DXCache files may be locked by the GPU process.** Use `rm -rf ... ; true` (ignore errors) or `find ... -delete` which skips locked files gracefully.

### Requires User Confirmation (Risk of breakage)

| Target | Path | Risk | Better Alternative |
|--------|------|------|--------------------|
| Cursor data | `AppData/Roaming/Cursor` | May break editor session | Delete only `state.vscdb.backup*` and `.trash/` |
| Store apps | `C:/Program Files/WindowsApps` | Cannot be moved easily | Use Settings → Apps to uninstall; no symlink possible |
| WSL VHDX | `AppData/Local/wsl/{GUID}/ext4.vhdx` | Must shut down WSL first | See VHDX compaction below |

**Pitfall: Microsoft Store apps (WindowsApps) cannot be moved via symlink or junction.** They must be uninstalled and reinstalled to a different drive via Windows Settings → Apps, or moved with the "Move" button (which only works for some apps). Attempting to junction these folders breaks the app and Windows update system.

### WSL VHDX Compaction

The WSL2 VHDX grows but never shrinks automatically. After freeing space inside WSL:

**Pitfall: VHDX compaction MUST be done from PowerShell (Admin), not from inside WSL.** You are shutting down your own WSL session, so this cannot be automated from within WSL cron.

```powershell
# From PowerShell Admin — WSL must be shut down first
wsl --shutdown
Optimize-VHD -Path "C:\Users\Game_\AppData\Local\wsl\{GUID}\ext4.vhdx" -Mode Full
```

Find your GUID first:
```powershell
dir "C:\Users\Game_\AppData\Local\wsl\" /s /b | findstr ext4.vhdx
```

## Step 4: Watchdog Script

A ready-made watchdog script lives at `~/.hermes/scripts/disk_watchdog.sh`. It implements the threshold logic above and outputs structured alert messages.

```bash
# Run manually
bash ~/.hermes/scripts/disk_watchdog.sh

# Or make executable and run directly
chmod +x ~/.hermes/scripts/disk_watchdog.sh
~/.hermes/scripts/disk_watchdog.sh
```

If the script doesn't exist yet, create it with this content:

```bash
#!/usr/bin/env bash
# ~/.hermes/scripts/disk_watchdog.sh
# Disk space watchdog for WSL2 + Windows mounts
set -euo pipefail

CRITICAL_THRESHOLD=$((5 * 1073741824))   # 5 GiB
WARNING_THRESHOLD=$((15 * 1073741824))   # 15 GiB
MOUNTS=("/" "/mnt/c" "/mnt/d" "/mnt/e")
ALERTS=()

for mount in "${MOUNTS[@]}"; do
    # Skip mounts that aren't available
    if ! mountpoint -q "$mount" 2>/dev/null && [ "$mount" != "/" ]; then
        echo "[SKIP] $mount — not mounted"
        continue
    fi

    avail=$(df -B1 "$mount" | tail -1 | awk '{print $4}')
    avail_gib=$((avail / 1073741824))

    if [ "$avail" -lt "$CRITICAL_THRESHOLD" ]; then
        msg="[CRITICAL] $mount — ${avail_gib} GiB free (< 5 GiB threshold)"
        ALERTS+=("$msg")
        echo "$msg"
    elif [ "$avail" -lt "$WARNING_THRESHOLD" ]; then
        msg="[WARNING] $mount — ${avail_gib} GiB free (< 15 GiB threshold)"
        ALERTS+=("$msg")
        echo "$msg"
    else
        echo "[OK] $mount — ${avail_gib} GiB free"
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
```

## Step 5: Cron Job Setup (Automated Monitoring)

Set up a cron job to run the watchdog every 6 hours (or your preferred interval):

```bash
# Edit crontab
crontab -e

# Add this line — run every 6 hours at :00
0 */6 * * * /home/$(whoami)/.hermes/scripts/disk_watchdog.sh >> /home/$(whoami)/.hermes/logs/disk_watchdog.log 2>&1

# Or run hourly
0 * * * * /home/$(whoami)/.hermes/scripts/disk_watchdog.sh >> /home/$(whoami)/.hermes/logs/disk_watchdog.log 2>&1
```

Ensure the log directory exists:
```bash
mkdir -p ~/.hermes/logs
```

**Pitfall: WSL cron daemon may not be running by default.** Start it with:
```bash
sudo service cron start
# Or add to /etc/wsl.conf for persistence:
# [boot]
# command = service cron start
```

**Pitfall: `/mnt/` drives may not be mounted when cron runs after WSL restart.** The watchdog script handles this with `mountpoint -q` checks, but ensure `systemd` or a boot command in `/etc/wsl.conf` handles automount.

## Pitfalls Summary

1. **`df` shows GiB not GB** — `-h` uses 1024-based units. Use `df -B1` for precise threshold checks (see Step 2).
2. **VHDX compaction needs PowerShell** — Cannot compact from inside WSL. Must `wsl --shutdown` first, then run from PowerShell Admin (see Step 3).
3. **NVIDIA DXCache is safe to delete** — Auto-regenerates on next game/driver load. Some files may be locked; skip them.
4. **Microsoft Store apps can't be moved easily** — No symlink/junction possible for `WindowsApps`. Use Windows Settings to move or uninstall.
5. **WSL cron may not be running** — Start with `sudo service cron start`; add to `/etc/wsl.conf` for persistence.
6. **`/mnt/` may not be mounted on WSL start** — Always check with `mountpoint -q` before targeting Windows drives in scripts.
7. **Locked files in AppData** — Use `find ... -delete` or `rm -rf ... ; true` to skip locked files gracefully.

## Related Skills

- **wsl-windows-storage** — Full migration workflow (move data + symlink), Steam game migration, VHDX move to secondary drive, robocopy usage.