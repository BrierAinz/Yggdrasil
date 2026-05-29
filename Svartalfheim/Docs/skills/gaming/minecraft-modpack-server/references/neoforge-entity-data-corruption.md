# NeoForge Entity Data Corruption Fix Reference

## The Bug: Alex's Caves BookProgress → SynchedEntityData Field Collision

### Affected Versions
- Minecraft 1.21.1 + NeoForge 21.1.x
- Alex's Caves `2.0.10` (current as of 2026-05)
- Citadel `1.21.1-2.7.6` (dependency)

### Mechanism
Alex's Caves stores book progress in `CitadelData` (a TAG_Compound on the player entity).
When the compendium update fails (player puts book in lectern, tries to add pages), 
the mod writes `AlexsCavesBookProgress: {Pages: [{Category:"alexscaves:primordial_caves", SubCategory:1}]}` 
as a CompoundTag into SynchedEntityData.

Minecraft vanilla field 15 = air supply counter (Integer, synched entity data).
The server serializes this CompoundTag into the `set_entity_data` packet, 
but the client's SynchedEntityData.assignValue() rejects it:
```
Invalid entity data item type for field 15 on entity LocalPlayer:
  old=0(class java.lang.Integer), new={AlexsCavesBookProgress:{Pages:[...]}}(class net.minecraft.nbt.CompoundTag)
```

Client crashes instantly on join → infinite reconnect loop.

### Player .dat File Structure
```
<UUID>.dat                    ← Primary player data (always present)
<UUID>.dat_old                ← Previous-state backup (server writes on save)
```
Located in: `world/playerdata/`

The corrupted field path: `Root → CitadelData → AlexsCavesBookProgress`

### NBT Edit Procedure (Python)
```python
import nbt.nbt as nbt

path = '/path/to/world/playerdata/UUID.dat'
nbtfile = nbt.NBTFile(path)

# Inspect CitadelData
cd = nbtfile['CitadelData']
for t in cd.tags:
    print(f'{t.name}: {type(t).__name__}')

# Remove corrupted entry
cd.tags = [t for t in cd.tags if t.name != 'AlexsCavesBookProgress']

# save (NBTFile.save_file() does NOT exist, use write_file())
nbtfile.write_file()
```

**Important**: Use `nbtfile.write_file()`, not `nbtfile.save_file()` — the latter 
doesn't exist on NBTFile (it's `write_file()` that writes back to the file path).

### Companion Fix: Remove Conflicting Mods
- `packetfixer` conflicts with `connectivity` on `@ModifyConstant` for 
  `ClientboundLevelChunkPacketData`. Remove `packetfixer`, keep `connectivity`.
- `lmft` (Load My F***ing Tags) should be removed if it spams errors on 
  every player join — indicates tag resolution failures.

### Prevention
- Warn players NOT to interact with the Alex's Caves compendium book in 
  lecterns until the mod is patched.
- Consider removing `alexscaves` entirely if the compendium feature is 
  important, as the bug is in the mod's entity data registration.