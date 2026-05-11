# Steam libraryfolders.vdf Editing Reference

## File Location
`C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf`

## Format (Key-Value / VDF)

```vdf
"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Program Files (x86)\\Steam"
		...
		"apps"
		{
			"228980"		"412131240"
			"728880"		"8506963703"
		}
	}
	"2"
	{
		"path"		"E:\\SteamLibrary"
		...
		"apps"
		{
			"220"		"6538432243"
		}
	}
}
```

Each app entry is: `"appid"\t\t"SizeOnDisk_in_bytes"`

## Moving a Game Between Libraries

When moving a game from C: (library "0") to E: (library "2"):

1. Remove the appid line from library "0"'s `apps` block
2. Add the appid line to library "2"'s `apps` block
3. **Braces must stay balanced** — count opens vs closes after editing

## Python Script for Safe VDF Editing

```python
import re

vdf_path = '/mnt/c/Program Files (x86)/Steam/steamapps/libraryfolders.vdf'
# ALWAYS BACK UP FIRST
# cp vdf_path vdf_path.bak

with open(vdf_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Remove appid from library 0
content = re.sub(r'\t\t\t"APPID"\t\t"\d+"\n', '', content)

# Add to library 2's apps — find the last app entry and append
# Best approach: find the closing sequence of library 2's apps block
# and insert before it
old = '\t\t\t"LAST_APPID_HERE"\t\t"SIZE"\n\t\t}\n\t}\n}'
new = '\t\t\t"LAST_APPID_HERE"\t\t"SIZE"\n\t\t\t"APPID"\t\t"SIZE"\n\t\t}\n\t}\n}'
content = content.replace(old, new)

with open(vdf_path, 'w', encoding='utf-8') as f:
    f.write(content)

# VERIFY: count braces
opens = content.count('{')
closes = content.count('}')
assert opens == closes, f"Brace mismatch: {opens} opens vs {closes} closes"
```

## Finding the SizeOnDisk for a Game

Read it from the game's appmanifest:

```bash
grep -m1 '"SizeOnDisk"' "/mnt/c/Program Files (x86)/Steam/steamapps/appmanifest_APPID.acf"
```

## Pitfalls

1. **Steam overwrites VDF on exit.** Edit only when Steam is NOT running, or your changes will be lost.
2. **Indentation matters.** App entries use 3 tabs (`\t\t\t`), blocks use 1-2 tabs. Wrong indentation can break Steam.
3. **Always backup before editing.** `cp libraryfolders.vdf libraryfolders.vdf.bak`
4. **Validate brace balance.** `{` count must equal `}` count.
5. **Appmanifest must exist in the target library's steamapps folder.** Copy the `.acf` file there and delete from the source.
6. **Game folder name in `installdir` field** of the appmanifest must match the actual folder name in `common/`.