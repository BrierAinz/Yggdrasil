---
name: wsl-windows-storage
version: 1.0.0
description: Manage Windows disk space from WSL — analyze, clean, migrate apps/games/models to secondary drives, create symlinks, compact VHDX.
tags: [wsl, windows, storage, disk-space, robocopy, steam, lm-studio, ollama, symlink, vhdx]
triggers:
  - disk full or nearly full on Windows C: drive
  - need to move large app data, AI models, or Steam games to another drive
  - migrate data from WSL while maintaining Windows app compatibility
  - compact WSL2 VHDX to reclaim space
---

# WSL → Windows Storage Management

## Overview

When a Windows drive (usually C:) is full and you're operating from WSL, you need to move large data to secondary drives (D:, E:) while keeping apps functional. This skill covers the complete workflow: analysis → cleanup → migration → symlink → verification.

## Step 1: Analyze Disk Usage

```bash
# Quick free space check (faster than PowerShell Get-PSDrive which can timeout)
df -h /mnt/c /mnt/d /mnt/e

# Find biggest directories in a Windows user profile
powershell.exe -Command "Get-ChildItem 'C:\Users\GAME_\AppData\Local' -Directory -ErrorAction SilentlyContinue | ForEach-Object { \$s = (Get-ChildItem \$_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum; if (\$s -gt 500MB) { Write-Host (\$_.Name + ' - ' + [math]::Round(\$s / 1GB, 2)) } }"

# Find biggest items in a specific path
powershell.exe -Command "Get-ChildItem 'C:\Users\GAME_' -Directory -ErrorAction SilentlyContinue | ForEach-Object { \$s = (Get-ChildItem \$_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum; if (\$s -gt 1GB) { Write-Host (\$_.Name + ' - ' + [math]::Round(\$s / 1GB, 2)) } }"
```

### PowerShell `$` Variable Escaping

**Pitfall:** WSL passes `$` to PowerShell literally unless escaped. Use `\$` inside `-Command` strings, OR write a `.ps1` script to `/tmp/` and run it:

```bash
cat > /tmp/scan_dirs.ps1 << 'EOF'
param($Path = "C:\Users\Game_")
Get-ChildItem $Path -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $s = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if ($s -gt 1GB) { Write-Host ($_.Name + " - " + [math]::Round($s / 1GB, 2)) }
}
EOF
powershell.exe -ExecutionPolicy Bypass -File /tmp/scan_dirs.ps1
```

## Step 2: Safe Cache Cleanup (No Risk)

These caches auto-regenerate and are safe to delete:

| Cache | Path | Typical Size |
|-------|------|-------------|
| NVIDIA DXCache | `C:\Users\Game_\AppData\Local\NVIDIA\DXCache` | 5-15GB |
| NVIDIA D3DSCache | `C:\Users\Game_\AppData\Local\NVIDIA\D3DSCache` | 1-5GB |
| pip cache | `C:\Users\Game_\AppData\Local\pip\cache` | 1-5GB |
| npm cache | `C:\Users\Game_\AppData\Local\npm-cache` | 1-3GB |
| Windows Temp | `C:\Users\Game_\AppData\Local\Temp` | 1-10GB |
| Crash Dumps | `C:\Users\Game_\AppData\Local\CrashDumps` | 0.5-2GB |
| Cursor backups | `C:\Users\Game_\AppData\Roaming\Cursor\User\globalStorage\state.vscdb.backup*` | 1-3GB |
| Cursor extensions trash | `C:\Users\Game_\AppData\Roaming\Cursor\CachedExtensionVSIXS\.trash\*` | 1-3GB |
| Overwolf | `C:\Users\Game_\AppData\Local\Overwolf` | 0.5-2GB |
| ms-playwright | `C:\Users\Game_\App_\AppData\Local\ms-playwright` | 0.5-1GB |

```bash
# Delete caches safely
rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/DXCache/*
rm -rf /mnt/c/Users/Game_/AppData/Local/NVIDIA/D3DSCache/*
```

**Note:** Some DXCache files may be locked by the GPU process. Delete what you can; skip locked files.

## Step 3: Migrate Large Data to Secondary Drive

### robocopy.exe — USE WINDOWS PATHS, NOT WSL PATHS

**Critical Pitfall:** `robocopy.exe` is a Windows tool and requires Windows paths (`C:\`, `E:\`). WSL paths like `/mnt/c/` will cause "path not found" errors when passed to robocopy directly.

```bash
# ✅ CORRECT — Windows paths
robocopy.exe "C:\Users\Game_\.lmstudio\models" "E:\LMStudio\models" /E /COPY:DAT /MT:8 /R:1 /W:1

# ❌ WRONG — WSL paths don't work with robocopy.exe
robocopy.exe "/mnt/c/Users/Game_/.lmstudio/models" "/mnt/e/LMStudio/models" /E /COPY:DAT
```

**robocopy exit codes:** Exit code 1 means "files were copied" (success). Only codes 8+ indicate errors.

**To move (copy + delete original):** Add `/MOVE` flag. robocopy copies all files first, then deletes originals.

**Background copies:** Use `terminal(background=true)` for large transfers. Monitor with `du -sh` on both source and destination.

### Verify Copy Integrity

```bash
# Compare file counts (must match)
find /mnt/c/SOURCE -type f | wc -l
find /mnt/e/DEST -type f | wc -l

# Compare total sizes
du -sh /mnt/c/SOURCE /mnt/e/DEST
```

## Step 4: Create Windows-Compatible Symlinks from WSL

**Key Discovery:** `ln -s` on WSL paths under `/mnt/c/` creates Windows-compatible **junctions** (visible as `<JUNCTION>` in `dir` output). This works WITHOUT admin privileges.

```bash
# Delete original data (AFTER verifying copy!)
rm -rf /mnt/c/Users/Game_/.lmstudio/models

# Create junction — app thinks data is still on C: but it lives on E:
ln -s /mnt/e/LMStudio/models /mnt/c/Users/Game_/.lmstudio/models

# Verify from both sides
ls /mnt/c/Users/Game_/.lmstudio/models/   # WSL access
cmd.exe /c "dir C:\Users\Game_\.lmstudio\models"  # Windows access (should show <JUNCTION>)
```

**Alternative (requires admin):** `cmd.exe /c "mklink /D "C:\path" "E:\path""` — but WSL `ln -s` is easier and doesn't need elevation.

## Step 5: Migrate Steam Games Between Libraries

Steam games require two things moved: the game folder + the appmanifest.

### 5a: Copy Game Folder

```bash
robocopy.exe "C:\Program Files (x86)\Steam\steamapps\common\GAME_NAME" "E:\SteamLibrary\steamapps\common\GAME_NAME" /E /COPY:DAT /MT:8 /R:1 /W:1
```

### 5b: Move Appmanifest

```bash
# Copy manifest to new library
cp "/mnt/c/Program Files (x86)/Steam/steamapps/appmanifest_APPID.acf" "/mnt/e/SteamLibrary/steamapps/"
# Delete from old location
rm "/mnt/c/Program Files (x86)/Steam/steamapps/appmanifest_APPID.acf"
# Delete original game folder (after verifying copy!)
rm -rf "/mnt/c/Program Files (x86)/Steam/steamapps/common/GAME_NAME"
```

### 5c: Update libraryfolders.vdf

Edit `C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf`:
1. Remove the appid entry from library "0" (C:) apps section
2. Add the appid entry to library "2" (E:\SteamLibrary) apps section

**Use Python for VDF editing** — the format is tricky with tabs and braces. See `references/steam-vdf-editing.md`.

### 5d: Find Steam App IDs

```bash
# List all games on C: with names and sizes
for f in /mnt/c/Program\ Files\ \(x86\)/Steam/steamapps/appmanifest_*.acf; do
  appid=$(grep -m1 '"appid"' "$f" | awk -F'"' '{print $4}')
  name=$(grep -m1 '"name"' "$f" | sed 's/.*"name".*"\(.*\)"/\1/')
  size=$(grep -m1 '"SizeOnDisk"' "$f" | sed 's/.*"SizeOnDisk".*"\(.*\)"/\1/')
  size_gb=$(echo "scale=2; $size / 1073741824" | bc 2>/dev/null)
  echo "$appid | $name | ${size_gb}GB"
done
```

**Important:** Steam must be closed before editing `libraryfolders.vdf`, or it will overwrite your changes on exit. If Steam is running, edits may get reverted.

## Step 6: Migrate AI Models (LM Studio, Ollama)

| App | Default Path | Target | Symlink |
|-----|-------------|--------|---------|
| LM Studio | `C:\Users\Game_\.lmstudio\models` | `E:\LMStudio\models` | `ln -s /mnt/e/LMStudio/models /mnt/c/Users/Game_/.lmstudio/models` |
| Ollama | `C:\Users\Game_\.ollama\models` | `E:\Ollama\models` | `ln -s /mnt/e/Ollama/models /mnt/c/Users/Game_/.ollama/models` |

**LM Studio extensions** (`~2.7GB` in `.lmstudio/extensions/`) can also be moved if needed, but are less critical.

**Ollama app uninstall:** The Windows uninstaller (`unins000.exe /VERYSILENT`) may require elevation. If it fails, use `robocopy /MOVE` to relocate the app folder to E:.

## Step 7: Compact WSL VHDX

The WSL2 virtual disk grows but never shrinks automatically. After freeing space inside WSL:

```powershell
# Must run from PowerShell (Admin) AFTER shutting down WSL
wsl --shutdown
# Then in PowerShell Admin:
diskpart
# select vdisk file="C:\Users\Game_\AppData\Local\wsl\{GUID}\ext4.vhdx"
# compact vdisk
# exit
```

Or one-liner from PowerShell Admin:
```powershell
wsl --shutdown; Optimize-VHD -Path "C:\Users\Game_\AppData\Local\wsl\{3531c4ab-20f2-447b-a7b7-a18e9fa2d4be}\ext4.vhdx" -Mode Full
```

**Important:** WSL must be completely shut down (`wsl --shutdown`) before compacting.

### Alternative: Move VHDX to Another Drive (More Space Saved)

Compacting only reclaims unused space inside the VHDX. Moving the entire VHDX to a secondary drive frees ALL its disk space on C:. The VHDX file (e.g., 111GB for a 106GB-used WSL instance) can live on any drive with a junction pointing to it.

```powershell
# From PowerShell Admin:
wsl --shutdown

# Find your VHDX (path varies by WSL distro GUID)
dir "C:\Users\Game_\AppData\Local\wsl\" /s /b | findstr ext4.vhdx

# Copy to E: drive (safer than move — verify before deleting)
robocopy "C:\Users\Game_\AppData\Local\wsl\{GUID}" "E:\WSL\{GUID}" ext4.vhdx /COPY:DAT /R:1 /W:1

# Verify sizes match, then delete original
del "C:\Users\Game_\AppData\Local\wsl\{GUID}\ext4.vhdx"

# Create junction back to E: (WSL expects the VHDX in its original location)
cmd /c mklink "C:\Users\Game_\AppData\Local\wsl\{GUID}\ext4.vhdx" "E:\WSL\{GUID}\ext4.vhdx"
```

**Warning:** This requires the user to manually shut down WSL and run these commands from PowerShell Admin. Cannot be done from inside WSL (you'd be shutting down your own session). The VHDX GUID varies by distro — always find it first with `dir ... ext4.vhdx`.

## References

- **Steam VDF Editing** (`references/steam-vdf-editing.md`) — Detailed guide for editing `libraryfolders.vdf` when moving Steam games, including Python script and pitfalls.
- **Scan Script** (`scripts/scan_dirs.ps1`) — Reusable PowerShell script to scan directories by size from WSL.

## Common Migration Targets

| Item | Location | Typical Size | Action |
|------|----------|-------------|--------|
| NVIDIA DXCache | AppData\Local\NVIDIA | 5-15GB | Delete (auto-regens) |
| LM Studio models | .lmstudio\models | 20-100GB | Move + symlink |
| Ollama models | .ollama\models | 5-20GB | Move + symlink |
| Ollama app | AppData\Local\Programs\Ollama | 5-10GB | Move + symlink or uninstall |
| Steam games | Program Files\Steam\steamapps\common | 10-50GB each | Move + manifest + VDF |
| Downloads | Users\Game_\Downloads | 5-20GB | Move + symlink |
| CurseForge | Users\Game_\curseforge | 5-15GB | Move + symlink |
| WSL VHDX | AppData\\Local\\wsl\\{GUID}\\ | 50-200GB | Compact or Move + junction |
| Cursor data | AppData\Roaming\Cursor | 2-5GB | Skippable (risk of breakage) |