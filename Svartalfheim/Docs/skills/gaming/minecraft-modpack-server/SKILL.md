---
name: minecraft-modpack-server
description: "Host modded Minecraft servers (CurseForge, Modrinth)."
tags: [minecraft, gaming, server, neoforge, forge, modpack]
---

# Minecraft Modpack Server Setup

## When to use
- User wants to set up a modded Minecraft server from a server pack zip
- User needs help with NeoForge/Forge server configuration
- User asks about Minecraft server performance tuning or backups

## Gather User Preferences First
Before starting setup, ask the user for:
- **Server name / MOTD** — what should it say in the server list?
- **Seed** — specific seed or random?
- **Difficulty** — peaceful / easy / normal / hard?
- **Gamemode** — survival / creative / adventure?
- **Online mode** — true (Mojang auth, legit accounts) or false (LAN/cracked friendly)?
- **Player count** — how many players expected? (affects RAM & view distance tuning)
- **RAM allocation** — or let agent decide based on mod count & available RAM?
- **View distance / simulation distance** — or let agent pick based on player count & hardware?
- **PvP** — on or off?
- **Whitelist** — open server or whitelist only?
- **Backups** — want automated backups? How often?

Use sensible defaults if the user doesn't care, but always ask before generating the config.

## Steps

### 1. Download & Inspect the Pack
```bash
mkdir -p ~/minecraft-server
cd ~/minecraft-server
wget -O serverpack.zip "<URL>"
unzip -o serverpack.zip -d server
ls server/
```
Look for: `startserver.sh`, installer jar (neoforge/forge), `user_jvm_args.txt`, `mods/` folder.
Check the script to determine: mod loader type, version, and required Java version.

### 2. Install Java
- Minecraft 1.21+ → Java 21: `sudo apt install openjdk-21-jre-headless`
- Minecraft 1.18-1.20 → Java 17: `sudo apt install openjdk-17-jre-headless`
- Minecraft 1.16 and below → Java 8: `sudo apt install openjdk-8-jre-headless`
- Verify: `java -version`

### 3. Install the Mod Loader
Most server packs include an install script. Use the INSTALL_ONLY env var to install without launching:
```bash
cd ~/minecraft-server/server
ATM10_INSTALL_ONLY=true bash startserver.sh
# Or for generic Forge packs:
# java -jar forge-*-installer.jar --installServer
```
This downloads libraries, patches the server jar, etc.

### 4. Accept EULA
```bash
echo "eula=true" > ~/minecraft-server/server/eula.txt
```

### 5. Configure server.properties
Key settings for modded/LAN:
```properties
motd=\u00a7b\u00a7lServer Name \u00a7r\u00a78| \u00a7aModpack Name
server-port=25565
online-mode=true          # false for LAN without Mojang auth
enforce-secure-profile=true  # match online-mode
difficulty=hard            # most modpacks balance around hard
allow-flight=true          # REQUIRED for modded (flying mounts/items)
spawn-protection=0         # let everyone build at spawn
max-tick-time=180000       # modded needs longer tick timeout
enable-command-block=true
```

Performance settings (scale to hardware):
```properties
# 2 players, beefy machine:
view-distance=16
simulation-distance=10

# 4-6 players, moderate machine:
view-distance=10
simulation-distance=6

# 8+ players or weaker hardware:
view-distance=8
simulation-distance=4
```

### 6. Tune JVM Args (user_jvm_args.txt)
Scale RAM to player count and mod count. Rule of thumb for modded:
- 100-200 mods: 6-12GB
- 200-350+ mods: 12-24GB
- Leave at least 8GB free for the OS/other tasks

```
-Xms12G
-Xmx24G
-XX:+UseG1GC
-XX:+ParallelRefProcEnabled
-XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions
-XX:+DisableExplicitGC
-XX:+AlwaysPreTouch
-XX:G1NewSizePercent=30
-XX:G1MaxNewSizePercent=40
-XX:G1HeapRegionSize=8M
-XX:G1ReservePercent=20
-XX:G1HeapWastePercent=5
-XX:G1MixedGCCountTarget=4
-XX:InitiatingHeapOccupancyPercent=15
-XX:G1MixedGCLiveThresholdPercent=90
-XX:G1RSetUpdatingPauseTimePercent=5
-XX:SurvivorRatio=32
-XX:+PerfDisableSharedMem
-XX:MaxTenuringThreshold=1
```

### 7. Open Firewall
```bash
sudo ufw allow 25565/tcp comment "Minecraft Server"
```
Check with: `sudo ufw status | grep 25565`

### 8. Create Launch Script
```bash
cat > ~/start-minecraft.sh << 'EOF'
#!/bin/bash
cd ~/minecraft-server/server
java @user_jvm_args.txt @libraries/net/neoforged/neoforge/<VERSION>/unix_args.txt nogui
EOF
chmod +x ~/start-minecraft.sh
```
Note: For Forge (not NeoForge), the args file path differs. Check `startserver.sh` for the exact path.

### 9. Set Up Automated Backups
Create backup script:
```bash
cat > ~/minecraft-server/backup.sh << 'SCRIPT'
#!/bin/bash
SERVER_DIR="$HOME/minecraft-server/server"
BACKUP_DIR="$HOME/minecraft-server/backups"
WORLD_DIR="$SERVER_DIR/world"
MAX_BACKUPS=24
mkdir -p "$BACKUP_DIR"
[ ! -d "$WORLD_DIR" ] && echo "[BACKUP] No world folder" && exit 0
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/world_${TIMESTAMP}.tar.gz"
echo "[BACKUP] Starting at $(date)"
tar -czf "$BACKUP_FILE" -C "$SERVER_DIR" world
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[BACKUP] Saved: $BACKUP_FILE ($SIZE)"
BACKUP_COUNT=$(ls -1t "$BACKUP_DIR"/world_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    REMOVE=$((BACKUP_COUNT - MAX_BACKUPS))
    ls -1t "$BACKUP_DIR"/world_*.tar.gz | tail -n "$REMOVE" | xargs rm -f
    echo "[BACKUP] Pruned $REMOVE old backup(s)"
fi
echo "[BACKUP] Done at $(date)"
SCRIPT
chmod +x ~/minecraft-server/backup.sh
```

Add hourly cron:
```bash
(crontab -l 2>/dev/null | grep -v "minecraft/backup.sh"; echo "0 * * * * $HOME/minecraft-server/backup.sh >> $HOME/minecraft-server/backups/backup.log 2>&1") | crontab -
```

## Pitfalls
- ALWAYS set `allow-flight=true` for modded — mods with jetpacks/flight will kick players otherwise
- `max-tick-time=180000` or higher — modded servers often have long ticks during worldgen
- First startup is SLOW (several minutes for big packs) — don't panic
- "Can't keep up!" warnings on first launch are normal, settles after initial chunk gen
- If online-mode=false, set enforce-secure-profile=false too or clients get rejected
- The pack's startserver.sh often has an auto-restart loop — make a clean launch script without it
- Delete the world/ folder to regenerate with a new seed
- Some packs have env vars to control behavior (e.g., ATM10 uses ATM10_JAVA, ATM10_RESTART, ATM10_INSTALL_ONLY)

## Troubleshooting: Player Disconnection & Crash Diagnosis

### Invalid Entity Data Type (SynchedEntityData mismatch)
**Symptom**: Player joins, gets "Disconnected" within seconds. Client crash shows:
```
Invalid entity data item type for field N on entity LocalPlayer: 
old=0(class java.lang.Integer), new={...}(class net.minecraft.nbt.CompoundTag)
```
**Root cause**: A mod registers entity data serializers that conflict with vanilla's field IDs. The server sends a CompoundTag but the client expects an Integer at that position. Common culprit in NeoForge 1.21.1: **Alex's Caves** (`alexscaves`) corrupts field 15 (air supply) with `AlexsCavesBookProgress` CompoundTag.

**Fix — NBT edit the player .dat file**:
1. Stop the server (`stop` in console)
2. Find the player data file: `world/playerdata/<UUID>.dat` (and `UUID.dat_old`)
3. Install Python NBT library: `pip install nbt`
4. Inspect and remove corrupted data:
```python
import nbt.nbt as nbt
path = '/path/to/<UUID>.dat'
nbtfile = nbt.NBTFile(path)
# View CitadelData
cd = nbtfile['CitadelData']
for t in cd.tags:
    print(f'{t.name}: {type(t).__name__}')
# Remove the corrupted entry
cd.tags = [t for t in cd.tags if t.name != 'AlexsCavesBookProgress']
nbtfile.write_file()
```
5. Copy the fixed .dat back to `world/playerdata/`
6. Restart the server
**This preserves all player data** (inventory, XP, position, etc.) — only the Alex's Caves compendium progress is lost.

**Nuclear option**: Remove `alexscaves-*.jar` (and `citadel-*.jar` if no other Alex mod depends on it). Set `removeErroringEntities=true` and `removeErroringTileEntities=true` in `neoforge-common.toml` to clean orphaned blocks/entities on next load.

### Mixin Conflict: packetfixer vs connectivity
**Symptom**: `@ModifyConstant conflict` in log between `packetfixer` and `connectivity` on `ClientboundLevelChunkPacketData`.
**Fix**: Remove one of them — they serve similar purposes. Keep `connectivity`, remove `packetfixer`.

### "Load My F***ing Tags" (LMFT) Errors
**Symptom**: `[LMFTCommon]: some tags are a bit cooked` on every player join.
**Fix**: Verify LMFT version matches your NeoForge/MC version. If tags are broken due to a missing mod dependency, add the dependency or remove LMFT.

### "Can't keep up!" 139+ ticks behind
**Immediate mitigations**:
- Reduce `simulation-distance` to 4 in `server.properties`
- Increase RAM if under-allocated
- Use `spark` mod profiler (`/spark profiler start` → `/spark profiler stop` → `/spark profiler open`) to identify expensive ticks
- Consider removing heavy/tick-intensive mods if rarely used

### Key Reminder
- **Never use `rm` in Minecraft server console** — it's not a shell. File operations must be done from the OS.
- **Always backup .dat files before editing** — `cp UUID.dat UUID.dat.backup`

> **Reference**: `references/neoforge-entity-data-corruption.md` — detailed NBT editing procedure and the Alex's Caves BookProgress bug analysis.

## Verification
- `pgrep -fa neoforge` or `pgrep -fa minecraft` to check if running
- Check logs: `tail -f ~/minecraft-server/server/logs/latest.log`
- Look for "Done (Xs)!" in the log = server is ready
- Test connection: player adds server IP in Multiplayer
