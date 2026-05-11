# Workflow Dependency Verification

## Procedure for verifying all workflow node dependencies

### Step 1: Collect node types from workflows

```python
import json, os

wf_dirs = [
    "/path/to/ComfyUI/user/default/workflows",
    "/path/to/ComfyUI/workflows",
]

all_nodes = set()
for wf_dir in wf_dirs:
    for f in os.listdir(wf_dir):
        if f.endswith('.json'):
            with open(os.path.join(wf_dir, f)) as fh:
                wf = json.load(fh)
            # Editor format: nodes[].type
            for node in wf.get('nodes', []):
                t = node.get('type', '')
                if t: all_nodes.add(t)
            # API format: {id: {class_type: ...}}
            for k, v in wf.items():
                if isinstance(v, dict) and 'class_type' in v:
                    all_nodes.add(v['class_type'])
```

### Step 2: Get registered nodes from running ComfyUI

```bash
curl -s http://127.0.0.1:8188/object_info | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Total registered: {len(d)}')
"
```

If count is <300, many custom nodes failed to import (check startup logs).

### Step 3: Compute missing (exclude virtual/editor-only)

Virtual/editor-only nodes that are safe to ignore:
- `PrimitiveNode` — built-in virtual node
- `Reroute` — built-in virtual node  
- `SetNode` — built-in virtual node
- `Fast Groups Bypasser (rgthree)` — JS-only UI toggle
- `Label (rgthree)` — JS-only UI label
- `MarkdownNote` — UI annotation

```python
virtual = {'PrimitiveNode', 'Reroute', 'SetNode', 
           'Fast Groups Bypasser (rgthree)', 'Label (rgthree)', 'MarkdownNote'}
truly_missing = all_nodes - registered - virtual
```

### Step 4: Find source package for each missing node

Methods (in order of reliability):

1. **Local grep** — Check if a local package already defines it:
   ```bash
   grep -r "class NodeName" custom_nodes/*/
   ```

2. **ComfyUI Manager registry** — Download and search:
   ```bash
   curl -sL https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json
   ```
   Search for `sam2`, `math`, etc. in titles/references.

3. **GitHub code search** — Search for the exact class name:
   ```
   https://github.com/search?q=ClassName+language:Python&type=code
   ```

4. **comfy.org API** — Limited but useful:
   ```bash
   curl -s "https://api.comfy.org/nodes?search=NodeName"
   ```

5. **Check the node's interface** — Load the workflow JSON and inspect inputs/outputs/widgets_values of the missing node. This helps identify what package it belongs to:
   ```python
   for node in wf['nodes']:
       if node.get('type') == 'MissingNode':
           print(f"Inputs: {[i['name'] for i in node.get('inputs', [])]}")
           print(f"Outputs: {[o['name'] for o in node.get('outputs', [])]}")
           print(f"Widgets: {node.get('widgets_values', [])}")
   ```

## Known node name collisions

### SAM2 packages (both can coexist)

| Package | Node Class Names | Install |
|---------|-----------------|---------|
| `neverbiasu/ComfyUI-SAM2` | `SAM2ModelLoader (segment anything2)`, `GroundingDinoModelLoader`, `GroundingDinoSAM2Segment` | Already in custom_nodes/ |
| `kijai/ComfyUI-segment-anything-2` | `DownloadAndLoadSAM2Model`, `Sam2Segmentation`, `Sam2AutoSegmentation`, `Sam2VideoSegmentation` | `git clone https://github.com/kijai/ComfyUI-segment-anything-2.git` |

### FL_Math node

- `gitmylo/FlowNodes` (installed as `ComfyUI-FL-Nodes`) provides `Int Expression` and `Float Expression`, NOT `FL_Math`
- `6174/comflowy-nodes` also does NOT provide `FL_Math`
- **Solution**: Create a compatibility node at `custom_nodes/ComfyUI-Compat-Nodes/` (see SKILL.md pitfall #36)

## This session's verification results (2025-05-04)

- **11 workflows** scanned across `user/default/workflows/` and `workflows/`
- **114 unique node types** found
- **Initial registered nodes**: 269 (most custom nodes had IMPORT FAILED)
- **After installing Python deps**: 2414 nodes registered
- **After installing kijai/ComfyUI-segment-anything-2 + ComfyUI-Compat-Nodes**: 2421 nodes
- **Final missing nodes**: 0 (excluding 6 virtual/editor-only)

### Python packages installed to fix IMPORT FAILED

The following packages were installed to resolve 11 custom nodes that had import errors:
`rotary_embedding_torch`, `einops`, `timm`, `addict`, `yapf`, `hydra-core`, `iopath`, `matplotlib`, `opencv-python`, `scikit-image`, `piexif`, `dill`, `deepdiff`, `pynvml`, `py-cpuinfo`, `clip_interrogator`, `lark`, `onnxruntime`, `sentencepiece`, `spandrel`, `omegaconf`, `gguf`, `peft`, `diffusers`, `accelerate`, `albumentations`, `ultralytics`, `segment-anything`, `sam2` (via Facebook Research), `gitpython`, `natsort`, `aiosqlite`, `beautifulsoup4`, `platformdirs`, `pyyaml`

### Custom nodes installed

1. **kijai/ComfyUI-segment-anything-2** — provides `DownloadAndLoadSAM2Model`, `Sam2Segmentation`
2. **ComfyUI-Compat-Nodes** (local) — provides `FL_Math` compatibility node