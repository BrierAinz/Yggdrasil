# 🗒 Lilith's Quick Notes

Notas rápidas que no van en memoria permanente pero valen la pena conservar.

---

## ComfyUI NSFW Pipeline — Estado Actual (May 17, 2026)

### Modelos descargados
- `unstableEvolution_Fp8.safetensors` (11.1GB) — NSFW checkpoint, preserva caras
- `getphatFLUXReality_v11SoftcoreFP8.safetensors` (11.1GB) — NSFW #1 rated, piel fotorrealista
- `flux1-fill-dev.safetensors` — ⚠️ GATED, necesita HF auth (descarga falló)
- `yolov8n.pt` (6.3MB) — Face detection para FaceDetailer

### Pipeline v19 (pendiente de testear)
- unStable Evolution FluXXX + PuLID + CLIPSeg mask + NSFW LoRA (0.7)
- Sin ControlNet Depth (OOM en RTX 3060 con modelo de 11GB)
- Workflow guardado en: `/tmp/v19_unstable_nodpeth_wrapped.json`
- Resultado: **No completó** — ComfyUI detenido por usuario

### Pipeline v18d (último resultado exitoso)
- XLabs ControlNet Depth + CLIPSeg mask + NSFW LoRA
- Output: `nsfw_v18d_depth_only_00001_.png`
- Resultado: Preserva forma corporal pero pierde cara (sin PuLID)

### Pipeline v17 (último con PuLID)
- PuLID 0.85 + smooth mask + skin color prompts
- Output: `nsfw_v17_pulid_smooth_mask_00001_.png`
- Resultado: Preserva cara, color mismatch en piel

### Pendiente
- [ ] Testear v19 (unStable + PuLID + CLIPSeg, sin ControlNet)
- [ ] Probar getphat FLUX Reality NSFW como alternativa
- [ ] Agregar FaceDetailer post-processing (si PuLID no es suficiente)
- [ ] Pipeline 3-pass: Pass1(NSFW checkpoint) → Pass2(FLUX Fill skin blend) → Pass3(FaceDetailer)
- [ ] FLUX Fill necesita HF auth — resolver para Pass 2

### 3-pass Pipeline Design (objetivo final)
```
Pass 1: unStable FluXXX + CLIPSeg mask + NSFW LoRA + PuLID → genera cuerpo
Pass 2: FLUX.1-Fill-dev + gradient mask → harmoniza piel en bordes
Pass 3: FaceDetailer + PuLID → restaura cara 100%
```

---

## GameMaster Agent — Ideas para Personajes

### Plataformas objetivo
- **Caveduck** (caveduck.io) — Original chars, BL/noir, stamps monetization
- **Tipsy Chat** (tipsy.chat) — Anime/NSFW, "Limitless" mode, longer descriptions

### Estrategia de monetización
1. Contest wins → coins/stamps + visibility
2. Volume portfolio → 10-20 chars across niches
3. Official Creator badge → featured placement (after 5+ originals)
4. Engagement hooks → cliffhanger scenarios = return visits

### Personajes pendientes de crear
- [ ] Lilith — dark fantasy goddess of Yggdrasil (transmedia synergy)
- [ ] Freya — goth honey-eyed character (use existing LoRA refs)
- [ ] Norse noir detective — original, fits Caveduck trending genres
- [ ] Isekai reverse harem — Tipsy priority, anime-heavy

---

## Herramientas Instaladas (ComfyUI)
- FaceDetailer (Impact Pack) ✅
- IC-Light Native ✅
- CLIPSeg+ ✅
- PuLID Flux v0.9.1 ✅
- SAM2 + GroundingDINO (GroundingDINO tokenizer issues, usar CLIPSeg)
- Shakker-Labs ControlNet Depth ✅
- XLabs ControlNet Depth v3 ✅

---

---

## Radar — 2026-05-17 12:22 PM

### Key Releases
- **pydantic-ai v1.97.0** (May 15) — Approaching v2.0. Review changelog for breaking changes before updating Yggdrasil agents/MCP.
- **diffusers 0.38.0** (May 1) — Stable release with new image/audio pipelines. Migrate from dev version if still on `0.38.0.dev0`.
- **langgraph 1.2.0** (May 12) — NEW in radar. If Yggdrasil explores graph-based agent orchestration, this is worth testing.
- **textual v8.2.6** (May 13) — Patch release. Update from 8.2.5 in TUI realm.
- **dify 1.14.1** (May 12) — Security hardening + workflow stability. Not directly in stack but useful reference for dashboard patterns.
- **llama_index v0.14.22** (May 14) —.NEW in radar. Relevance if expanding RAG capabilities.

### Trending Repos (Δ since last scan)
- **comfyui-mesh** ⭐68 (↑ from 52) — FLUX.2/LTX 2.3 multi-GPU distribution via NVENC. Growing fast. **Action:** Test for Yggdrasil inference distribution.
- **Anima-TrainFlow** ⭐29 (↑ from 23) — LoRA trainer for Anima 2B, 6GB VRAM. **Action:** Evaluate as lightweight alternative to ai-toolkit.
- **Pixal3D-ComfyUI** ⭐21 (↑ from 15) — TencentARC image-to-3D ComfyUI nodes. **Action:** Potential for 3D Lilith assets.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐148 — NEW. Combined A1111/ComfyUI setup GUI. Lower priority (setup tool, not new capability).
- **LATO** ⭐23 — 3D mesh flow matching. Academic but relevant if Yggdrasil explores 3D generation.

### Action Items
- [ ] Update textual to 8.2.6 in TUI workspace
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference
- [ ] Evaluate Anima-TrainFlow for low-VRAM LoRA training
- [ ] Review pydantic-ai v1.97.0 changelog for breaking API changes
- [ ] Pin/migrate diffusers from 0.38.0.dev0 → 0.38.0 stable

*Última actualización: May 17, 2026*

---

## Radar — 2026-05-18

### Key Releases (Δ since May 17)
- **🆕 kohya-ss/sd-scripts v0.10.5** (May 7) — LoRA training toolkit update. Review changelog for new FLUX.2/Anima training options.
- **🆕 huggingface/transformers v5.8.1** (May 13) — Patch release. Low-risk update for model loading.
- **pydantic-ai v1.97.0** (May 15) — No change. Still approaching v2.0; review API changelog.
- **diffusers 0.38.0** (May 1) — No change. Pin stable release.
- **langgraph 1.2.0** (May 12) — No change.
- **uv 0.11.14**, **textual v8.2.6**, **dify 1.14.1**, **llama_index v0.14.22** — No change.

### Trending Repos (Δ since last scan)
- **comfyui-mesh** ⭐72 (↑4) — Multi-GPU FLUX.2/LTX 2.3 via NVENC. **Action: Test for Yggdrasil inference distribution.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐25 (↑4) — TencentARC Pixal3D nodes. **Action: Potential 3D Lilith asset pipeline.**
- **Anima-TrainFlow** ⭐30 (↑1) — LoRA trainer Anima 2B, 6GB VRAM. **Action: Evaluate vs ai-toolkit.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐239 (↑91 🔺) — Installer GUI. Low priority — not a new capability.
- **dreamrec/ComfyUI-Pixal3D** ⭐9 (NEW) — Alt Pixal3D wrapper, RTX 30/40/50. Watch.
- **LATO** ⭐23 — 3D mesh flow matching. Academic.

### Action Items
- [ ] Update transformers to v5.8.1
- [ ] Review kohya sd-scripts v0.10.5 changelog for new training features
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference
- [ ] Evaluate Anima-TrainFlow for 6GB VRAM LoRA training
- [ ] Watch dreamrec/ComfyUI-Pixal3D as alternative 3D pipeline

---

## Radar — 2026-05-18 (PM Scan)

### Key Releases (Δ since AM scan)
- **No new releases** since this morning's scan. All watched repos unchanged.
- **Stable carryovers:** kohya sd-scripts v0.10.5, transformers v5.8.1, pydantic-ai v1.97.0, diffusers 0.38.0, langgraph 1.2.0, uv 0.11.14, textual v8.2.6, dify 1.14.1, llama_index v0.14.22

### Trending Repos (Δ since AM scan)
- **comfyui-mesh** ⭐80 (↑8) — Multi-GPU FLUX.2/LTX 2.3. Still growing steadily. **Test it.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐342 (↑103 🔺) — Installer GUI. Viral spike but not a capability gain. Ignore.
- **ThetaCursed/Anima-TrainFlow** ⭐34 (↑4) — LoRA trainer Anima 2B, 6GB VRAM. **Evaluate vs ai-toolkit.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐29 (↑4) — Pixal3D nodes. **Test for 3D Lilith pipeline.**
- **TianhaoZhao668/LATO** ⭐26 (↑3) — 3D mesh flow matching. Academic. Watch only.
- **dreamrec/ComfyUI-Pixal3D** ⭐9 — No change. Continue watching.

### Action Items (no new actions — repeating from AM)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference
- [ ] Evaluate Anima-TrainFlow for 6GB VRAM LoRA training
- [ ] Review kohya sd-scripts v0.10.5 changelog
- [ ] Update transformers to v5.8.1

---

## Radar — 2026-05-18 (06:32 AM Scan)

### Key Releases (Δ since PM scan)
- **No new releases** since PM scan. All watched repos unchanged.
- **Stable carryovers:** kohya sd-scripts v0.10.5, transformers v5.8.1, pydantic-ai v1.97.0, diffusers 0.38.0, langgraph 1.2.0, uv 0.11.14, textual v8.2.6, dify 1.14.1, llama_index v0.14.22
- **ComfyUI-3D-Pack** v0.1.6 appeared in scanner but is from Aug 2025 — stale, no action needed.

### Trending Repos (Δ since PM scan)
- **comfyui-mesh** ⭐83 (↑3) — Multi-GPU FLUX.2/LTX 2.3. Steady growth. **Test it.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐389 (↑47 🔺) — Installer GUI viral spike. Not a capability gain — ignore.
- **Saganaki22/Pixal3D-ComfyUI** ⭐31 (↑2) — Pixal3D nodes. **Test for 3D Lilith pipeline.**
- **ThetaCursed/Anima-TrainFlow** ⭐34 (flat) — LoRA trainer Anima 2B, 6GB VRAM. **Evaluate vs ai-toolkit.**
- **TianhaoZhao668/LATO** ⭐29 (↑3) — 3D mesh flow matching. Academic. Watch.
- **dreamrec/ComfyUI-Pixal3D** ⭐9 (flat) — Alt Pixal3D wrapper. Continue watching.

### Action Items (no new actions — carryovers from PM)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference
- [ ] Evaluate Anima-TrainFlow for 6GB VRAM LoRA training
- [ ] Review kohya sd-scripts v0.10.5 changelog
- [ ] Update transformers to v5.8.1

---

## Radar — 2026-05-18 (06:45 PM Scan)

### Key Releases
- **No new releases** since AM scan. All watched repos unchanged.
- Stable carryovers: kohya sd-scripts v0.10.5, transformers v5.8.1, pydantic-ai v1.97.0, diffusers 0.38.0, langgraph 1.2.0, uv 0.11.14, textual v8.2.6, dify 1.14.1, llama_index v0.14.22.

### Trending Repos (Δ since 06:32 AM scan)
- **comfyui-mesh** ⭐85 (↑2) — Multi-GPU FLUX.2/LTX 2.3. Steady growth. Still worth testing.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐420 (↑31 🔺) — Installer GUI viral spike continues. Not a capability gain — ignore.
- **Saganaki22/Pixal3D-ComfyUI** ⭐33 (↑2) — Pixal3D nodes. Evaluate for 3D Lilith pipeline.
- **ThetaCursed/Anima-TrainFlow** ⭐34 (flat) — LoRA trainer. Stalled growth. Still evaluate.
- LATO, dreamrec/ComfyUI-Pixal3D — unchanged. Watch only.

### Action Items (carryovers — no new actions)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference
- [ ] Evaluate Anima-TrainFlow for 6GB VRAM LoRA training
- [ ] Review kohya sd-scripts v0.10.5 changelog
- [ ] Update transformers to v5.8.1

---

## Radar — 2026-05-18 06:51 PM

### Key Releases (Δ since 06:45 PM scan)
- **🆕 uv 0.11.15** (May 18) — Bumped from 0.11.14. Low-risk update.
- **🆕 ComfyUI v0.21.1** (May 13) — Not in previous scans. **Check changelog for node API changes.**
- **🆕 fastmcp v3.3.1** (May 15) — "Loop There It Is" release. Yggdrasil uses fastmcp in .venv — test compatibility.
- **🆕 Anima-TrainFlow v1.0.1** (May 14) — First tagged release of 6GB VRAM LoRA trainer.
- Stable carryovers: diffusers 0.38.0, kohya sd-scripts v0.10.5, pydantic-ai v1.97.0, transformers v5.8.1, langgraph 1.2.0, textual v8.2.6, dify 1.14.1, llama_index v0.14.22, fastapi 0.136.1

### Trending Repos (Δ since 06:45 PM scan)
- **comfyui-mesh** ⭐86 (↑1) — Multi-GPU FLUX.2/LTX 2.3. Steady growth continues.
- **Saganaki22/Pixal3D-ComfyUI** ⭐35 (↑2) — Pixal3D ComfyUI nodes. Growing.
- **ThetaCursed/Anima-TrainFlow** ⭐36 (↑2) — LoRA trainer Anima 2B, 6GB VRAM. Released v1.0.1.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐436 (↑16) — Installer GUI viral. Not capability gain — ignore.
- **TianhaoZhao668/LATO** ⭐30 — 3D mesh flow matching. Academic. Watch.
- **dreamrec/ComfyUI-Pixal3D** ⭐9 — Alt Pixal3D wrapper. Stalled. Watch only.

### Action Items
- [ ] Update uv to 0.11.15
- [ ] Check ComfyUI v0.21.1 changelog for node API changes
- [ ] Test fastmcp v3.3.1 compatibility with Yggdrasil .venv
- [ ] Evaluate Anima-TrainFlow v1.0.1 for 6GB VRAM LoRA training (first release)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over)
- [ ] Update transformers to v5.8.1 (carried over)

---

## Radar — 2026-05-19 (12:54 AM Scan)

### Key Releases (Δ since May 18 06:51 PM scan)
- **🆕 pydantic-ai v1.98.0** (May 19) — JUST RELEASED. **Breaking:** `tool_retries=`/`output_retries=` replaced with `retries: int | AgentRetries`. Bug fix: MCP `fastmcp.server` no longer required at runtime. V2 prep: deprecated `pydantic_ai.ext.aci`. **ACTION: Review breaking changes before updating Yggdrasil agents.**
- **🆕 OpenAI Agents Python v0.17.3** (May 19) — Sandbox credential fix, memory import error handling. Not in stack directly but relevant for agent ecosystem monitoring.
- Stable carryovers: diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, textual 8.2.6, llama_index 0.14.22, kohya sd-scripts v0.10.5, ComfyUI v0.21.1, fastapi 0.136.1

### Trending Repos (Δ since last scan)
- **shootthesound/comfyui-mesh** ⭐86 (↑1) — FLUX.2/LTX 2.3 multi-GPU distributed inference via NVENC. No tagged releases yet. Still growing. **Test it.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐469 (↑33 🔺) — Installer GUI viral spike continues. Not a capability gain. Ignore.
- **Saganaki22/Pixal3D-ComfyUI** ⭐35 (flat) — Pixal3D ComfyUI nodes. Evaluate for 3D Lilith pipeline.
- **ThetaCursed/Anima-TrainFlow** ⭐36 (flat) — LoRA trainer Anima 2B, 6GB VRAM. has v1.0.1 tag.
- **TianhaoZhao668/LATO** ⭐33 (flat) — 3D mesh flow matching. Academic. Watch.
- **dreamrec/ComfyUI-Pixal3D** ⭐9 (flat) — Alt Pixal3D wrapper. Stalled. Watch only.

### Action Items
- [ ] **⚠️ Review pydantic-ai v1.98.0 breaking changes** — `retries` API replaced `tool_retries`/`output_retries`. Audit Yggdrasil agent code before updating.
- [ ] Update pydantic-ai to v1.98.0 (after breaking change review)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over ×4)
- [ ] Evaluate Anima-TrainFlow for 6GB VRAM LoRA training (carried over ×4)
- [ ] Check ComfyUI v0.21.1 changelog for node API changes (carried over ×2)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×2)
- [ ] Update transformers to v5.8.1 (carried over ×2)
- [ ] Update textual to v8.2.7 (from v8.2.6)
- [ ] Review dify v1.14.2 security fixes

---

## Radar — 2026-05-19 (02:49 PM Scan)

### Key Releases (Δ since 07:06 AM scan)
- **pydantic-ai v1.98.0** — No change from AM. ⚠️ Breaking `retries` API still needs audit.
- **textual v8.2.7** — No change. Kitty key protocol + TextArea shortcuts.
- **dify v1.14.2** — No change. Security hardening, db migration required.
- **OpenAI Agents v0.17.3** — No change from AM. Bug fixes only.
- **ComfyUI v0.21.1** — No change. **Key: Anima TE LoRA kohya format support, Save3D vertex colors/textures, HiDream-O1, reverted breaking changes from v0.21.0.**
- **fastmcp v3.3.1** — No change.
- Stable carryovers: diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, kohya sd-scripts v0.10.5, uv 0.11.15

### Trending Repos (Δ since AM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐50 (↑8 🔺) — **Accelerating growth.** TencentARC Pixal3D → textured GLB. **Elevated priority for 3D Lilith pipeline.**
- **shootthesound/comfyui-mesh** ⭐90 (↑2) — Multi-GPU FLUX.2/LTX 2.3. Steady. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐41 (↑5) — LoRA trainer Anima 2B, 6GB VRAM. Growing.
- **🆕 OpenPipe/ART** ⭐9,476 — Agent Reinforcement Trainer (GRPO). Train multi-step agents. Ecosystem-relevant, not directly in stack.
- **🆕 PozzettiAndrea/ComfyUI-LiTo** ⭐4 — Apple Research LiTo → 3D Gaussian Splat (ICLR 2026). Early but promising for 3D assets.
- **🆕 citronlegacy/citron-anima-lora-trainer-ui** ⭐30 — Gradio UI for Anima LoRA training, 6GB VRAM. Alternative to Anima-TrainFlow.
- **dreamrec/ComfyUI-Pixal3D** ⭐12 (↑3) — Alt Pixal3D wrapper. Slow growth.
- **TianhaoZhao668/LATO** ⭐33 (flat) — 3D mesh flow matching, academic. Watch only.

### ComfyUI v0.21.1 — Key Changes for Yggdrasil
- ✅ **Anima TE LoRA kohya format support** — directly impacts LoRA training pipeline
- ✅ **Save3D extended** — exports vertex colors + textures (3D asset export)
- ✅ **HiDream-O1-Image** support — new model
- ✅ Some breaking changes from v0.21.0 reverted

### Action Items
- [ ] ⚠️ Audit pydantic-ai v1.98.0 `retries` API before updating (carried over ×3)
- [ ] **Check ComfyUI v0.21.1** — Anima TE LoRA + Save3D changes relevant to pipeline
- [ ] **Test Pixal3D-ComfyUI ⭐50** — surging, elevated priority for 3D Lilith
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over ×5)
- [ ] Evaluate Anima-TrainFlow vs ai-toolkit for 6GB VRAM LoRA training (carried over ×5)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×3)
- [ ] Update transformers to v5.8.1 (carried over ×3)
- [ ] Update textual to v8.2.7 (TUI workspace)
- [ ] Watch ComfyUI-LiTo — Apple Research 3D Gaussian Splat for ComfyUI

---

## Radar — 2026-05-19 (05:54 PM Scan)

### Key Releases (Δ since 02:49 PM scan)
- **No new releases** since previous scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v1.98.0 (⚠️ breaking `retries` API), diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, llama_index 0.14.22, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1

### Trending Repos (Δ since 02:49 PM scan)
- **shootthesound/comfyui-mesh** ⭐91 (↑1) — Multi-GPU FLUX.2/LTX 2.3. Steady. **Test it.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐54 (↑4 🔺) — Pixal3D ComfyUI nodes. Still growing. **Priority test for 3D Lilith pipeline.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐531 (↑43 🔺) — Installer GUI viral. Not capability gain. Ignore.
- **🆕 japp-fi/polymarket-mcp-server** ⭐155 — MCP server for Polymarket. Interesting MCP ecosystem growth but not Yggdrasil-relevant.
- **🆕 mdowis/anansi** ⭐81 — Self-healing web scraper. Could be useful for data collection pipelines. Watch.
- **🆕 HuTa0kj/skill-scanner-agent** ⭐32 — Agent skill scanning/assessment. Tangentially relevant to Hermes plugin ecosystem.
- **🆕 adner/GenUI_MCP** ⭐7 — MCP server for UI generation from descriptions. Interesting MCP pattern.
- **🆕 jangyuxue/hermes-soul-governance** ⭐7 — SOUL.md governance framework for Hermes Agent. Ecosystem curiosity.
- Anima-TrainFlow, LATO, ComfyUI-Pixal3D (dreamrec) — not surfaced this scan. Carryovers from previous.

### Action Items (no new critical actions — carryovers persist)
- [ ] ⚠️ Audit pydantic-ai v1.98.0 `retries` API before updating (carried over ×4)
- [ ] **Test Pixal3D-ComfyUI** ⭐54 — still growing, priority for 3D Lilith pipeline (carried over ×3)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over ×6)
- [ ] Evaluate Anima-TrainFlow vs ai-toolkit for 6GB VRAM LoRA training (carried over ×6)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×3)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×4)
- [ ] Update transformers to v5.8.1 (carried over ×4)
- [ ] Update textual to v8.2.7 (carried over ×3)
- [ ] Watch ComfyUI-LiTo — Apple Research 3D Gaussian Splat for ComfyUI (carried over ×2)

---

## Radar — 2026-05-19 (07:06 AM Scan)

### Key Releases (Δ since May 19 12:54 AM scan)
- **🆕 textual v8.2.7** (May 19) — "The more Kitty Release". Bumped from v8.2.6. Low-risk update.
- **🆕 dify v1.14.2** (May 19) — Security fixes + agent groundwork + workflow reliability. Bumped from v1.14.1.
- pydantic-ai v1.98.0 — No change (already tracked). **⚠️ Breaking `retries` API still needs review.**
- Stable carryovers: diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, llama_index 0.14.22, kohya sd-scripts v0.10.5, ComfyUI v0.21.1, fastapi 0.136.1, uv 0.11.15

### Trending Repos (Δ since last scan)
- **shootthesound/comfyui-mesh** ⭐88 (↑2) — Multi-GPU distributed FLUX.2/LTX 2.3. Steady growth. **Test it.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐42 (↑7 🔺) — Pixal3D nodes. **Growing fast — priority test for 3D Lilith pipeline.**
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐488 (↑19) — Installer GUI. Viral. Not capability gain. Ignore.
- ThetaCursed/Anima-TrainFlow, TianhaoZhao668/LATO, dreamrec/ComfyUI-Pixal3D — not in trending this scan. Carryovers from previous.

### Action Items
- [ ] Update textual to v8.2.7 (TUI workspace)
- [ ] Note dify v1.14.2 security fixes (reference for dashboard patterns)
- [ ] **⚠️ Review pydantic-ai v1.99.0 breaking changes** — v1.98.0 had `retries` API break; v1.99.0 adds `gemini-3.5-flash` + OpenAI regex fix. Audit both before updating. (carried over ×5)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over ×6)
- [ ] Evaluate Pixal3D-ComfyUI ⭐60 growing fast — **elevated priority** for 3D Lilith pipeline
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×6)
- [ ] Check ComfyUI v0.21.1 changelog (carried over ×3)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×4)
- [ ] Update transformers to v5.8.1 (carried over ×4)

---

## Radar — 2026-05-19 08:59 PM

### Key Releases (Δ since 05:54 PM scan)
- **🆕 pydantic-ai v1.99.0** (May 20) — Rapid fire release (v1.97→v1.98→v1.99 in 5 days). Adds `gemini-3.5-flash` model, fixes OpenAI strict schemas with regex lookarounds. No new breaking changes, but v1.98.0 `retries` API break still un-audited. **ACTION: Audit v1.98.0 + v1.99.0 together before updating.**
- Stable carryovers: diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1 (no tagged releases), textual v8.2.7, dify 1.14.2, llama_index 0.14.22, kohya sd-scripts v0.10.5, uv 0.11.15, OpenAI Agents v0.17.3, edge-tts 7.2.8, fastapi 0.136.1
- ComfyUI — no GitHub releases (uses custom update system). Latest from earlier scan: v0.21.1 with Anima TE LoRA kohya format + Save3D.

### Trending Repos (Δ since 05:54 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐60 (↑6 🔺) — Pixal3D → textured GLB. **Still accelerating. Priority for 3D Lilith pipeline.**
- **shootthesound/comfyui-mesh** ⭐92 (↑2) — Multi-GPU FLUX.2/LTX 2.3 via NVENC. Steady. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐42 (↑6) — LoRA trainer 6GB VRAM. Surging.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐535 (↑4) — Installer GUI. Not capability gain — ignore.
- **🆕 bytedance/Lance** ⭐334 — 3B native multimodal model (image + video understanding). New this week. Could be Yggdrasil-relevant for multimodal agent perception.
- **🆕 gregowahoo/comfyui-workflow-finder** ⭐32 — Semantic search for ComfyUI workflows. Useful tooling.
- **🆕 FranckyB/ComfyUI-DramaBox** ⭐28 — Port of resemble-ai's DramaBox for ComfyUI. Interesting for narrative generation.
- **🆕 agentic-in/elephant-agent** ⭐345 — "Self Evolving AI Agent." Ecosystem curiosity, potentially relevant to Hermes agent architecture.
- **🆕 ZJU-REAL/SDAR** ⭐105 — Self-Distilled Agentic Reinforcement Learning. Academic but relevant for agent training methods.
- MCP ecosystem (watch only): japp-fi/polymarket-mcp-server ⭐156, mdowis/anansi ⭐81, DomDemetz/claude-soul ⭐75, Episkey-G/GrokSearch-rs ⭐48
- LATO ⭐33, dreamrec/ComfyUI-Pixal3D ⭐12, PozzettiAndrea/ComfyUI-LiTo ⭐4, citronlegacy/citron-anima-lora-trainer-ui ⭐31 — carryovers.

### Action Items
- [ ] **⚠️ Audit pydantic-ai v1.98.0 + v1.99.0** — `retries` API breaking change + rapid releases. Before updating Yggdrasil agents. (carried over ×5)
- [ ] **Test Pixal3D-ComfyUI ⭐60** — still surging, priority for 3D Lilith pipeline (carried over ×4)
- [ ] Test comfyui-mesh for multi-GPU FLUX.2 inference (carried over ×6)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training — growing (carried over ×6)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×3)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×4)
- [ ] Update transformers to v5.8.1 (carried over ×4)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×3)
- [ ] Watch bytedance/Lance ⭐334 for multimodal agent use cases
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline

---

## Radar — 2026-05-20 (12:08 AM Scan)

### Key Releases (Δ since May 19 08:59 PM scan)
- **pydantic-ai v1.99.0** (May 20) — Published May 20, adds `gemini-3.5-flash` model, fixes OpenAI strict schemas with regex lookarounds. No new breaking changes beyond v1.98.0 `retries` API. **ACTION: Audit v1.98.0 + v1.99.0 together before updating.**
- Stable carryovers: diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, llama_index 0.14.22, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1
- No changes to: edge-tts 7.2.8, ComfyUI-3D-Pack v0.1.6 (stale)

### Trending Repos (Δ since May 19 08:59 PM scan)
- **shootthesound/comfyui-mesh** ⭐93 (↑1) — FLUX.2/LTX 2.3 multi-GPU via NVENC. Steady growth. **Test it.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐60 (flat) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐368 (↑34 🔺) — 3B multimodal model. Surging. Relevance for multimodal perception.
- **ThetaCursed/Anima-TrainFlow** ⭐42 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐548 (↑13) — Installer GUI. Still viral. Not capability gain. Ignore.
- **gregowahoo/comfyui-workflow-finder** ⭐32 (↑0) — Semantic ComfyUI workflow search. Useful tooling.
- **FranckyB/ComfyUI-DramaBox** ⭐28 — DramaBox for ComfyUI narrative generation. Watch.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐4 — Apple Research LiTo → 3D Gaussian Splat. Early.
- **agentic-in/elephant-agent** ⭐350 (↑5) — Self-evolving AI agent. Ecosystem curiosity.
- **ZJU-REAL/SDAR** ⭐107 (↑2) — Self-Distilled Agentic RL. Academic relevance.

### Action Items
- [ ] **⚠️ Audit pydantic-ai v1.98.0 + v1.99.0** — `retries` API breaking change + rapid releases. (carried over ×6)
- [ ] **Test Pixal3D-ComfyUI ⭐60** — priority for 3D Lilith pipeline (carried over ×5)
- [ ] Test comfyui-mesh ⭐93 for multi-GPU FLUX.2 inference (carried over ×7)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×7)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×4)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×5)
- [ ] Update transformers to v5.8.1 (carried over ×5)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×4)
- [ ] Watch bytedance/Lance ⭐368 — surging multimodal model for agent perception
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline

---

## Radar — 2026-05-20 (09:14 AM Scan)

### Key Releases (Δ since May 20 12:08 AM scan)
- **No new releases** since midnight scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v1.99.0 (⚠️ audit v1.98.0 breaking `retries` API), diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, llama_index 0.14.22, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1, edge-tts 7.2.8

### Trending Repos (Δ since midnight scan)
- **shootthesound/comfyui-mesh** ⭐94 (↑1) — FLUX.2/LTX 2.3 multi-GPU via NVENC. Steady growth. **Test it.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐61 (↑1) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐400 (↑32 🔺) — 3B multimodal model. **Still surging fast.** Watch for agent perception use cases.
- **ThetaCursed/Anima-TrainFlow** ⭐42 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **agentic-in/elephant-agent** ⭐353 (↑3) — Self-evolving AI agent. Ecosystem curiosity.
- **ZJU-REAL/SDAR** ⭐107 (flat) — Self-Distilled Agentic RL. Academic relevance.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐559 (↑11) — Installer GUI viral. Not capability gain. Ignore.
- **japp-fi/polymarket-mcp-server** ⭐153 — MCP server for Polymarket. Not Yggdrasil-relevant.
- **mdowis/anansi** ⭐81 — Self-healing web scraper. Interesting for data pipelines. Watch.
- **gregowahoo/comfyui-workflow-finder** ⭐32 (flat) — Semantic ComfyUI workflow search. Useful tooling.
- **FranckyB/ComfyUI-DramaBox** ⭐28 (flat) — DramaBox for narrative generation. Watch.
- **citronlegacy/citron-anima-lora-trainer-ui** ⭐31 (flat) — Gradio UI for Anima LoRA training. Alternative to Anima-TrainFlow.
- **TianhaoZhao668/LATO** ⭐35 (↑2) — 3D mesh flow matching. Academic. Watch.
- **dreamrec/ComfyUI-Pixal3D** ⭐12 (flat) — Alt Pixal3D wrapper. Stalled.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐4 (flat) — Apple Research 3D Gaussian Splat. Early.

### Action Items (carryovers — no new critical actions)
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×7)
- [ ] **Test Pixal3D-ComfyUI ⭐61** — priority for 3D Lilith pipeline (carried over ×6)
- [ ] Test comfyui-mesh ⭐94 for multi-GPU FLUX.2 inference (carried over ×8)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×8)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×5)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×6)
- [ ] Update transformers to v5.8.1 (carried over ×6)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×5)
- [ ] Watch bytedance/Lance ⭐419 🔺 — surging multimodal model for agent perception
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline
- [ ] Watch Doorman11991/smallcode ⭐769 — small LLM agent, ecosystem relevance

---

## Radar — 2026-05-20 (12:20 PM Scan)

### Key Releases (Δ since 09:14 AM scan)
- **No new releases** since AM scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v1.99.0 (⚠️ audit v1.98.0 breaking `retries` API), diffusers 0.38.0, transformers 5.8.1, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, llama_index 0.14.22, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1, edge-tts 7.2.8

### Trending Repos (Δ since 09:14 AM scan)
- **shootthesound/comfyui-mesh** ⭐95 (↑1) — FLUX.2/LTX 2.3 multi-GPU via NVENC. Steady. **Test it.**
- **Saganaki22/Pixal3D-ComfyUI** ⭐61 (flat) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐419 (↑19 🔺) — 3B multimodal model. **Still surging fast.** Watch for agent perception use cases.
- **ThetaCursed/Anima-TrainFlow** ⭐42 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **agentic-in/elephant-agent** ⭐356 (↑3) — Self-evolving AI agent. Ecosystem curiosity.
- **ZJU-REAL/SDAR** ⭐108 (flat) — Self-Distilled Agentic RL. Academic relevance.
- **🆕 Doorman11991/smallcode** ⭐769 — AI coding agent optimized for small LLMs (4B-active, 87% benchmark). Ecosystem curiosity for lightweight agent patterns.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐564 (↑5) — Installer GUI viral. Not capability gain. Ignore.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐6 (↑2) — Apple Research LiTo → 3D Gaussian Splat. Early. Watch.
- **dreamrec/ComfyUI-Pixal3D** ⭐12 (flat) — Alt Pixal3D wrapper. Stalled.
- **japp-fi/polymarket-mcp-server** ⭐153 — Not Yggdrasil-relevant.
- **mdowis/anansi** ⭐82 — Self-healing web scraper. Data pipeline utility. Watch.
- **gregowahoo/comfyui-workflow-finder** ⭐32 (flat) — Semantic ComfyUI workflow search. Useful tooling.
- **FranckyB/ComfyUI-DramaBox** ⭐28 (flat) — DramaBox for narrative generation. Watch.
- **TianhaoZhao668/LATO** ⭐35 (flat) — 3D mesh flow matching. Academic.

### Action Items (carryovers — no new critical actions)
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×8)
- [ ] **Test Pixal3D-ComfyUI ⭐61** — priority for 3D Lilith pipeline (carried over ×7)
- [ ] Test comfyui-mesh ⭐95 for multi-GPU FLUX.2 inference (carried over ×9)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×9)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×6)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×7)
- [ ] Update transformers to v5.8.1 (carried over ×7)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×6)
- [ ] Watch bytedance/Lance ⭐419 🔺 — surging multimodal model for agent perception
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline
- [ ] Watch Doorman11991/smallcode ⭐769 — small LLM agent, ecosystem relevance

---

## Radar — 2026-05-20 (09:42 AM Scan)

### Key Releases (Δ since 12:20 PM May 20 scan)
- **🆕 transformers v5.9.0** (May 20) — JUST RELEASED. Bumped from v5.8.1. Adds Cohere2Moe model (MoE architecture). **ACTION: Update from v5.8.1 → v5.9.0.**
- **pydantic-ai v1.99.0** (May 20) — No change. ⚠️ Breaking `retries` API from v1.98.0 still un-audited.
- Stable carryovers: diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify v1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since 12:20 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐70 (↑9 🔺) — **Accelerating.** TencentARC Pixal3D → textured GLB. Updated today. **Priority for 3D Lilith pipeline.**
- **bytedance/Lance** ⭐441 (↑22 🔺) — 3B multimodal model. Still surging fast. Watch for agent perception.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐14 (↑8 🔺) — Apple Research LiTo → 3D Gaussian Splat for ComfyUI. Growing fast. Watch for 3D Lilith.
- **shootthesound/comfyui-mesh** ⭐95 (flat) — Multi-GPU FLUX.2/LTX 2.3. Steady. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐42 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **agentic-in/elephant-agent** ⭐360 (↑4) — Self-evolving agent. Ecosystem curiosity.
- **Doorman11991/smallcode** ⭐792 (↑23 🔺) — Small LLM agent (4B). Ecosystem relevance.
- **OpenPipe/ART** ⭐9482 — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **🆕 evilsocket/audit** ⭐347 — 8-stage vulnerability-discovery agent. Created May 18. Security relevance for Hermes architecture.
- **🆕 sapientinc/HRM-Text** ⭐532 — 1B text model based on HRM architecture. Created May 18. Niche.
- **Tencent-Hunyuan/HunyuanWorld** ⭐1121 — [ICML 2026] WorldMirror 3D reconstruction. Updated May 19. Watch for 3D Lilith pipeline.
- **FranckyB/ComfyUI-DramaBox** ⭐28 — Updated today (May 20). Narrative generation for ComfyUI.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐574 — Installer GUI. Not capability gain. Ignore.
- LATO ⭐35, dreamrec/ComfyUI-Pixal3D ⭐12, comfyui-workflow-finder ⭐32 — carryovers, no significant movement.

### Action Items
- [ ] **🆕 Update transformers v5.8.1 → v5.9.0** — New Cohere2Moe model added
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×9 ⚠️ OVERDUE)
- [ ] **Test Pixal3D-ComfyUI ⭐70 🔺** — accelerating, priority for 3D Lilith pipeline (carried over ×8)
- [ ] Test comfyui-mesh ⭐95 for multi-GPU FLUX.2 inference (carried over ×10)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×10)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×7)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×8)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×7)
- [ ] Watch ComfyUI-LiTo ⭐14 (↑8) — Apple Research 3D Gaussian Splat for ComfyUI
- [ ] Watch bytedance/Lance ⭐441 🔺 — surging multimodal model for agent perception
- [ ] Watch HunyuanWorld ⭐1121 — [ICML 2026] 3D reconstruction model
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline

---

## Radar — 2026-05-20 (12:58 PM Scan)

### Key Releases (Δ since 09:42 AM scan)
- **No new releases** since AM scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v1.99.0 (⚠️ audit v1.98.0 breaking `retries` API), transformers v5.9.0 (🆕 from AM), diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, ComfyUI v0.21.1, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since 09:42 AM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐75 (↑5 🔺) — Still accelerating. Updated today (May 20). **Priority for 3D Lilith pipeline.**
- **bytedance/Lance** ⭐475 (↑34 🔺) — 3B multimodal model. **Surging fast.** Watch for agent perception use cases.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐20 (↑6 🔺) — Apple Research LiTo → 3D Gaussian Splat. Growing fast. **Watch for 3D Lilith.**
- **shootthesound/comfyui-mesh** ⭐95 (flat) — Multi-GPU FLUX.2/LTX 2.3. Steady. **Test it.**
- **Doorman11991/smallcode** ⭐808 (↑16) — 4B active-param coding agent. Ecosystem relevance.
- **evilsocket/audit** ⭐355 (↑8) — 8-stage vulnerability-discovery agent. Security relevance for Hermes.
- **ZJU-REAL/SDAR** ⭐111 (↑3) — Self-Distilled Agentic RL. Academic relevance.
- **Tencent-Hunyuan/HunyuanWorld-1.0** ⭐2819 — Discovered. Full immersive 3D world generation. Larger scope than previously tracked HunyuanWorld-Mirror (⭐1121).
- **Tencent-Hunyuan/HunyuanWorld-Mirror** ⭐1121 — [ICML 2026] WorldMirror 3D reconstruction. Updated May 19.
- **agentic-in/elephant-agent** ⭐361 (↑1) — Self-evolving agent. Ecosystem curiosity.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐585 — Installer GUI. Not capability gain. Ignore.
- **FranckyB/ComfyUI-DramaBox** ⭐28 (updated May 20) — DramaBox narrative generation. Watch.
- **ThetaCursed/Anima-TrainFlow** ⭐42 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **TianhaoZhao668/LATO** ⭐35 (flat) — 3D mesh flow matching. Academic.

### Action Items (no new critical actions)
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×10 ⚠️ CRITICALLY OVERDUE)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (new from AM scan)
- [ ] **Test Pixal3D-ComfyUI ⭐75** — accelerating, 3D Lilith pipeline (carried over ×9)
- [ ] Test comfyui-mesh ⭐95 for multi-GPU FLUX.2 inference (carried over ×11)
- [ ] Evaluate Anima-TrainFlow ⭐42 for 6GB VRAM LoRA training (carried over ×11)
- [ ] Check ComfyUI v0.21.1 changelog — Anima TE LoRA + Save3D (carried over ×8)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×9)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×8)
- [ ] Watch ComfyUI-LiTo ⭐20 (↑6) — Apple Research 3D Gaussian Splat growing fast
- [ ] Watch bytedance/Lance ⭐475 🔺 — surging multimodal model for agent perception
- [ ] Watch HunyuanWorld-1.0 ⭐2819 — full 3D world generation ecosystem
- [ ] Watch ComfyUI-DramaBox for narrative generation pipeline

---

## Radar — 2026-05-20 (04:59 PM Scan)

### Key Releases (Δ since 12:58 PM scan)
- **🆕 ComfyUI v0.22.0** (May 20) — JUST RELEASED. MoGe 3D reconstruction support, IC-LoRA for LTX 2.3, reduced LTX 2.3 peak VRAM, audio node None-input handling, negative batch_index, SECURITY.md added. **ACTION: Update from v0.21.1 → v0.22.0. Review MoGe + IC-LoRA for Yggdrasil pipeline.**
- **transformers v5.9.0** — No change. Confirmed. Adds Cohere2Moe model.
- **pydantic-ai v1.99.0** — No change. ⚠️ Breaking `retries` API from v1.98.0 still un-audited.
- Stable carryovers: diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index 0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since 12:58 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐80 (↑5) — Pixal3D → textured GLB. Updated today (May 20). **Priority for 3D Lilith pipeline.**
- **bytedance/Lance** ⭐508 (↑33 🔺) — 3B multimodal model. **Still surging.** Watch for agent perception.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐25 (↑5) — Apple Research LiTo → 3D Gaussian Splat. Growing solidly. Watch for 3D Lilith.
- **Doorman11991/smallcode** ⭐833 (↑25 🔺) — 4B active-param coding agent. Still viral.
- **shootthesound/comfyui-mesh** ⭐95 (flat) — Multi-GPU FLUX.2/LTX 2.3. **Test it.**
- **OpenPipe/ART** ⭐9483 (↑) — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **agentic-in/elephant-agent** ⭐364 (↑4) — Self-evolving agent. Ecosystem curiosity.
- **evilsocket/audit** ⭐367 (↑) — 8-stage vulnerability-discovery agent. Security relevance.
- **ThetaCursed/Anima-TrainFlow** ⭐43 (↑1) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐595 — Installer GUI viral. Not capability gain. Ignore.
- **Tencent-Hunyuan/HunyuanWorld-1.0** ⭐2819 — Full 3D world generation. Watch.
- **FranckyB/ComfyUI-DramaBox** ⭐28 (updated May 20) — DramaBox narrative generation. Watch.

### ComfyUI v0.22.0 — Key Changes for Yggdrasil
- ✅ **MoGe 3D reconstruction** (CORE-168) — depth estimation + 3D mesh. Potential for 3D Lilith assets.
- ✅ **IC-LoRA support for LTX 2.3** (CORE-102) — downscaled IC-LoRA + LTX2.3 video pipeline.
- ✅ **Reduced LTX 2.3 peak VRAM** when guide_mask is in use (CORE-166) — helps RTX 3060.
- ✅ **Audio nodes handle None inputs** — kijai contribution, better error handling.
- ✅ **Negative batch_index** for ImageFromBatch/LatentFromBatch.
- ✅ **preserve noise_scale across chained model_sampling patches** — kijai, better flux quality.
- 🆕 **SECURITY.md** — ComfyUI now has formal security policy.

### Action Items
- [ ] **🆕 Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix
- [ ] **🆕 Test MoGe 3D node** for Lilith 3D asset pipeline (replaces or complements Pixal3D)
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×11 ⚠️ CRITICALLY OVERDUE)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×2)
- [ ] **Test Pixal3D-ComfyUI ⭐80** — 3D Lilith pipeline (carried over ×10)
- [ ] Test comfyui-mesh ⭐95 for multi-GPU FLUX.2 inference (carried over ×12)
- [ ] Evaluate Anima-TrainFlow ⭐43 for 6GB VRAM LoRA training (carried over ×12)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×10)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×9)
- [ ] Watch ComfyUI-LiTo ⭐25 — Apple Research 3D Gaussian Splat growing
- [ ] Watch bytedance/Lance ⭐528 🔺 — surging multimodal model for agent perception

---

## Radar — 2026-05-20 (08:34 PM Scan)

### Key Releases (Δ since 04:59 PM scan)
- **No new releases** since PM scan. All watched repos unchanged.
- Stable carryovers: ComfyUI v0.22.0 (🆕 MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix), transformers v5.9.0, pydantic-ai v1.99.0 (⚠️ audit v1.98.0 breaking `retries` API), diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify v1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since 04:59 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐83 (↑3) — Pixal3D → textured GLB. **Priority for 3D Lilith pipeline.**
- **shootthesound/comfyui-mesh** ⭐96 (↑1) — FLUX.2/LTX 2.3 multi-GPU via NVENC. **Test it.**
- **bytedance/Lance** ⭐528 (↑20 🔺) — 3B multimodal model. **Still surging.** Watch for agent perception.
- **Doorman11991/smallcode** ⭐846 (↑13) — 4B coding agent. Still viral. Ecosystem relevance.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐35 (↑10 🔺) — Apple Research LiTo → 3D Gaussian Splat. **Fast growth — elevated to watch-for-testing.**
- **OpenPipe/ART** ⭐9483 — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **agentic-in/elephant-agent** ⭐367 — Self-evolving agent. Ecosystem curiosity.
- **evilsocket/audit** ⭐374 — 8-stage vulnerability-discovery agent. Security relevance.
- **sapientinc/HRM-Text** ⭐570 — 1B text model. Niche.
- **Tencent-Hunyuan/HunyuanWorld-1.0** ⭐2820 — Full 3D world generation. Watch.
- **ZJU-REAL/SDAR** ⭐111 — Self-Distilled Agentic RL. Academic.
- **ThetaCursed/Anima-TrainFlow** ⭐43 (↑1) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **FranckyB/ComfyUI-DramaBox** ⭐29 (↑1) — DramaBox narrative generation for ComfyUI.
- **TianhaoZhao668/LATO** ⭐35 — 3D mesh flow matching. Academic.
- **DomDemetz/claude-soul** ⭐76 — Self-correcting learning engine for Claude Code. Ecosystem curiosity.

### 🆕 New Repos Worth Noting (past 3 days)
- **T8mars/comfyui-anima-t8** ⭐26 (May 19) — Anima model ComfyUI integration. Watch.
- **ruwwww/ComfyUI-SPEED** ⭐9 (May 20) — Spectral Progressive Diffusion for ComfyUI. Early but interesting.
- **BlackSnowSkill/ANIMA_BOOSTER** ⭐9 (May 20) — High-performance optimization for Anima DiT 2B. **Could help RTX 3060 performance.**
- **shootthesound/ComfyUI-Angelo** ⭐7 (May 20) — Click-to-refine + smart inpaint sampler (FLUX 2 Klein). Watch for pipeline improvements.

### Action Items
- [ ] ⚠️ Audit pydantic-ai v1.98.0 + v1.99.0 — `retries` API breaking change (carried over ×12 ⚠️ CRITICALLY OVERDUE)
- [ ] **🆕 Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×2)
- [ ] **🆕 Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×2)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×3)
- [ ] **Test Pixal3D-ComfyUI ⭐83** — 3D Lilith pipeline (carried over ×11)
- [ ] Test comfyui-mesh ⭐96 for multi-GPU FLUX.2 inference (carried over ×13)
- [ ] Evaluate Anima-TrainFlow ⭐43 for 6GB VRAM LoRA training (carried over ×13)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×11)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×10)
- [ ] **Watch ANIMA_BOOSTER ⭐9** — Anima DiT 2B optimization, could help RTX 3060
- [ ] Watch ComfyUI-LiTo ⭐35 (↑10) — Apple Research 3D Gaussian Splat, growing fast
- [ ] Watch bytedance/Lance ⭐528 🔺 — surging multimodal model for agent perception
- [ ] Watch HunyuanWorld-1.0 ⭐2820 — full 3D world generation ecosystem

---

## Radar — 2026-05-21

### Key Releases (Δ since May 20 08:34 PM scan)
- **🆕🔥 pydantic-ai v2.0.0b1** (May 21) — **MAJOR: V2 BETA 1 released.** Harness-first design with `capabilities` as core primitive. Composable units bundle tools, lifecycle hooks, instructions, model settings. Supersedes ALL previous v1.98/v1.99 breaking change concerns — migration target is now v2.0. **ACTION: Read V2 migration guide before any pydantic-ai updates.**
- ComfyUI v0.22.0 — No change (from May 20). MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix.
- transformers v5.9.0 — No change. Cohere2Moe model.
- Stable carryovers: diffusers 0.38.0, langgraph 1.2.0, fastmcp v3.3.1, textual v8.2.7, dify v1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since May 20 08:34 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐86 (↑3) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐556 (↑28 🔺) — 3B multimodal model. **Still surging fast.**
- **PozzettiAndrea/ComfyUI-LiTo** ⭐43 (↑8 🔺) — Apple Research LiTo → 3D Gaussian Splat. **Fast growth.** Watch for 3D Lilith.
- **shootthesound/comfyui-mesh** ⭐97 (↑1) — Multi-GPU FLUX.2/LTX 2.3. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐44 (↑1) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **🆕 kat3ri/ComfyUI-DramaBox** ⭐15 — DramaBox TTS nodes for ComfyUI (different from FranckyB's repo).
- **🆕 panterathehacker/marble-runner** ⭐15 — Walk around Gaussian splat worlds in third-person. 3D navigation.
- **🆕 hunhee98/pluck** ⭐34 — MCP-native code retrieval for AI agents (84-88% fewer read tokens).
- **🆕 DomDemetz/claude-soul** ⭐76 — Self-correcting learning engine for Claude Code. Ecosystem curiosity.
- **🆕 zyadhajaji/meshy-mcp** ⭐3 — MCP server for 3D model generation via Meshy. Early but relevant for 3D pipeline.
- **Doorman11991/smallcode** ⭐869 (↑23) — 4B coding agent. Viral. Ecosystem relevance.

### Action Items
- [ ] **🔥 READ pydantic-ai V2 migration guide** — v2.0.0b1 introduces `capabilities` architecture. Supersedes v1.98/v1.99 audit.
- [ ] **Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×3)
- [ ] **Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×3)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×4)
- [ ] **Test Pixal3D-ComfyUI ⭐86** — 3D Lilith pipeline (carried over ×12)
- [ ] Test comfyui-mesh ⭐97 for multi-GPU FLUX.2 inference (carried over ×14)
- [ ] Evaluate Anima-TrainFlow ⭐44 for 6GB VRAM LoRA training (carried over ×14)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×12)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×11)
- [ ] Watch ComfyUI-LiTo ⭐43 (↑8) — Apple Research 3D Gaussian Splat, growing fast
- [ ] Watch bytedance/Lance ⭐556 🔺 — surging multimodal model for agent perception

---

## Radar — 2026-05-21 (02:49 AM Scan)

### Key Releases (Δ since May 20 08:34 PM scan)
- **🆕🔥 pydantic-ai v1.100.0** (May 21) — SSRF cloud-metadata bypass fix (GHSA-cqp8-fcvh-x7r3), Bedrock native JSON output + strict tool calls, V2 deprecation warnings (`gateway/gemini:` → `gateway/google-cloud:`, positional evals constructors, `evaluation_name`/`evaluator_version` deprecated). **ACTION: Update from v1.99.0 → v1.100.0. This supersedes the v1.98.0 `retries` API audit — both v1.98 + v1.99 + v1.100 should be applied together.**
- **🔥 pydantic-ai v2.0.0b1** (May 21) — Harness-first design with `capabilities` core primitive. Composable units bundle tools, lifecycle hooks, instructions, model settings. **ACTION: Read V2 migration guide for long-term planning. Do NOT upgrade yet (beta).**
- ComfyUI v0.22.0 — No change (May 20). MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix.
- transformers v5.9.0 — No change. Cohere2Moe model.
- Stable carryovers: diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify v1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since May 20 08:34 PM scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐89 (↑3) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐591 (↑35 🔺) — 3B multimodal model. **Still surging fast.** Watch for agent perception.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐46 (↑3) — Apple Research LiTo → 3D Gaussian Splat. Growing solidly.
- **shootthesound/comfyui-mesh** ⭐98 (↑1) — Multi-GPU FLUX.2/LTX 2.3. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐44 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **BlackSnowSkill/ANIMA_BOOSTER** ⭐14 — Anima DiT 2B optimization suite. **Could help RTX 3060 performance.**
- **Doorman11991/smallcode** ⭐917 (↑23 🔺) — 4B active-param coding agent. 87% benchmark. Viral.
- **OpenPipe/ART** ⭐9483 — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **evilsocket/audit** ⭐384 (↑10) — 8-stage vulnerability-discovery agent. Security relevance for Hermes.
- **DomDemetz/claude-soul** ⭐76 — Self-correcting learning engine for Claude Code. Ecosystem curiosity.
- **hunhee98/pluck** ⭐34 — MCP-native code retrieval. 84-88% fewer read tokens. Relevant for Hermes tooling.
- **panterathehacker/marble-runner** ⭐15 — Walk around Gaussian splat worlds. 3D navigation. Niche.
- **zyadhajaji/meshy-mcp** ⭐3 — MCP server for 3D model generation via Meshy. Early.
- **T8mars/comfyui-anima-t8** ⭐30 — Anima model ComfyUI integration. Watch.
- BasZ4ll/Stable-Diffusion-WebUI ⭐633 — Installer GUI. Not capability gain. Ignore.

### pydantic-ai v1.100.0 — Key Changes for Yggdrasil
- 🛡️ **SSRF fix** — IPv6 transition forms normalized in URL validation (GHSA-cqp8-fcvh-x7r3). Only affects `FileUrl` with `force_download='allow-local'`.
- 🆕 **Bedrock native JSON output** + strict tool calls support
- ⚠️ **V2 deprecation warnings added** — `gateway/gemini:` → `gateway/google-cloud:`, positional evals constructors deprecated, `evaluation_name`/`evaluator_version` pattern deprecated
- Bug fix: Vercel AI thinking parts signature handling

### Action Items
- [ ] **🆕 Update pydantic-ai → v1.100.0** — SSRF security fix + supersedes v1.98/v1.99 audit (all three versions should be applied together)
- [ ] **🔥 Read pydantic-ai V2 migration guide** — `capabilities` architecture planning (beta, don't upgrade yet)
- [ ] **Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×4)
- [ ] **Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×4)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×5)
- [ ] **Test Pixal3D-ComfyUI ⭐89** — 3D Lilith pipeline (carried over ×13)
- [ ] Test comfyui-mesh ⭐98 for multi-GPU FLUX.2 inference (carried over ×15)
- [ ] Evaluate Anima-TrainFlow ⭐44 for 6GB VRAM LoRA training (carried over ×15)
- [ ] Evaluate **ANIMA_BOOSTER ⭐14** for RTX 3060 Anima optimization
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×13)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×12)
- [ ] Watch ComfyUI-LiTo ⭐49 (↑3) — Apple Research 3D Gaussian Splat growing
- [ ] Watch bytedance/Lance ⭐613 🔺 — surging multimodal model for agent perception

---

## Radar — 2026-05-21 (05:54 AM Scan)

### Key Releases (Δ since 02:49 AM scan)
- **No truly new releases** since 02:49 AM scan. pydantic-ai v1.100.0 and v2.0.0b1 already captured.
- **pydantic-ai v1.100.0** — Confirmed published May 21 03:52 UTC. SSRF security fix supersedes older audit chain. **ACTION: Update from v1.99.0 → v1.100.0.**
- **pydantic-ai v2.0.0b1** — Confirmed published May 21 04:17 UTC. Beta. Do NOT upgrade yet — read V2 migration guide for planning.
- Stable carryovers: ComfyUI v0.22.0 (MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix), transformers v5.9.0, diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify v1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since 02:49 AM scan)
- **bytedance/Lance** ⭐613 (↑22 🔺) — 3B multimodal model. **Still surging hard.** Watch for agent perception.
- **Saganaki22/Pixal3D-ComfyUI** ⭐91 (↑2) — Pixal3D → textured GLB. Priority for 3D Lilith pipeline.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐49 (↑3) — Apple Research LiTo → 3D Gaussian Splat. Growing solidly.
- **shootthesound/comfyui-mesh** ⭐98 (flat) — Multi-GPU FLUX.2/LTX 2.3. **Test it.**
- **ThetaCursed/Anima-TrainFlow** ⭐44 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **Doorman11991/smallcode** ⭐964 (↑47 🔺) — 4B coding agent. Still viral.
- **evilsocket/audit** ⭐388 (↑4) — 8-stage vulnerability-discovery agent. Security relevance.
- **BlackSnowSkill/ANIMA_BOOSTER** ⭐15 (↑1) — Anima DiT 2B optimization. Potentially helpful for RTX 3060.

### 🆕 New Repos (past 24h)
- **T8mars/comfyui-megastyle-T8** ⭐5 (May 21) — Anima style transfer for ComfyUI. Early. Watch.
- **Satsuj1n/xp-mcp** ⭐11 — MCP server for XP Investimentos. Niche pattern.
- **mobbin/mobbin-mcp-server** ⭐10 — Mobbin design reference MCP. Interesting MCP ecosystem growth.

### Action Items
- [ ] **⚡ Update pydantic-ai → v1.100.0** — SSRF security fix (supersedes v1.98/v1.99 audit; all three versions should be applied together)
- [ ] **🔥 Read pydantic-ai V2 migration guide** — `capabilities` architecture planning (beta, don't upgrade yet)
- [ ] **Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×5)
- [ ] **Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×5)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×6)
- [ ] **Test Pixal3D-ComfyUI ⭐91** — 3D Lilith pipeline (carried over ×14)
- [ ] Test comfyui-mesh ⭐98 for multi-GPU FLUX.2 inference (carried over ×16)
- [ ] Evaluate Anima-TrainFlow ⭐44 for 6GB VRAM LoRA training (carried over ×16)
- [ ] Evaluate **ANIMA_BOOSTER ⭐15** for RTX 3060 Anima optimization (carried over ×2)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×14)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×13)
- [ ] Watch ComfyUI-LiTo ⭐49 (↑3) — Apple Research 3D Gaussian Splat growing

---

## Radar — 2026-05-21 08:59 UTC

### Releases
- All watched repos **unchanged** since early morning scan. No new version bumps.
- pydantic-ai v2.0.0b1, diffusers 0.38.0, transformers v5.9.0, langgraph 1.2.0 — all stable.
- facechain v2.0.0 dormant since Dec 2023. Consider removing from watch list.

### Trending
- shootthesound/comfyui-mesh ⭐98 (flat) — No growth. Still worth testing for multi-GPU FLUX.2.
- BasZ4ll/Stable-Diffusion-WebUI ⭐585 — Wrapper/installer only. Not stack-relevant. Skip.
- 2aronS/sd-faceswap ⭐7 — Too early, low stars. Ignore.
- GitHub Trending API was down — no data this cycle.

### Action Items
- [Carried] All items from previous scan remain active. No new action items this cycle.
- [ ] Drop facechain from watch list (no releases since Dec 2023)
- [ ] Watch bytedance/Lance ⭐613 🔺 — surging multimodal model for agent perception

---

## Radar — 2026-05-21 (06:04 PM UTC)

### Key Releases (Δ since 08:59 UTC scan)
- **No new releases** since AM scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v2.0.0b1 (beta) + v1.100.0 (⚡ SSRF fix), ComfyUI v0.22.0 (MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix), transformers v5.9.0, diffusers 0.38.0, langgraph 1.2.0, fastmcp 3.3.1, textual v8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, uv 0.11.15, fastapi 0.136.1, llama_index v0.14.22, edge-tts 7.2.8
- facechain v2.0.0 — dormant since Dec 2023. **Remove from watch list.**

### Trending Repos (Δ since 08:59 UTC scan)
- **Saganaki22/Pixal3D-ComfyUI** ⭐95 (↑6) — Pixal3D → textured GLB. **Growing steadily.** Priority for 3D Lilith pipeline.
- **bytedance/Lance** ⭐642 (↑29 🔺) — 3B multimodal model. **Surging hard.** Watch for agent perception use cases.
- **PozzettiAndrea/ComfyUI-LiTo** ⭐55 (↑6) — Apple Research LiTo → 3D Gaussian Splat. **Growing fast.** Watch for 3D Lilith.
- **shootthesound/comfyui-mesh** ⭐98 (flat) — Multi-GPU FLUX.2/LTX 2.3 via NVENC. Steady. **Test it.**
- **Doorman11991/smallcode** ⭐1017 (↑53 🔺) — 4B active-param coding agent. Viral. Ecosystem relevance.
- **OpenPipe/ART** ⭐9591 (↑108) — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **evilsocket/audit** ⭐398 (↑10) — 8-stage vulnerability-discovery agent. Security relevance for Hermes.
- **agentic-in/elephant-agent** ⭐382 (↑15) — Self-evolving agent. Ecosystem curiosity.
- **ZJU-REAL/SDAR** ⭐120 (↑9) — Self-Distilled Agentic RL. Academic.
- **ThetaCursed/Anima-TrainFlow** ⭐44 (flat) — LoRA trainer 6GB VRAM. Evaluate vs ai-toolkit.
- **BlackSnowSkill/ANIMA_BOOSTER** ⭐15 (flat) — Anima DiT 2B optimization. Could help RTX 3060.
- **ruwwww/ComfyUI-SPEED** ⭐22 (↑13 🔺) — Spectral Progressive Diffusion for ComfyUI. **Fast growth — watch for quality/speed gains.**
- **T8mars/comfyui-anima-t8** ⭐32 (↑2) — Anima model ComfyUI integration. Watch.
- **FranckyB/ComfyUI-DramaBox** ⭐31 (↑2) — DramaBox narrative generation for ComfyUI. Watch.
- **hunhee98/pluck** ⭐34 (flat) — MCP-native code retrieval for AI agents. Relevant for Hermes tooling.

### 🆕 New Repos (past 72h)
- **🆕 shootthesound/ComfyUI-Angelo** ⭐41 (May 20) — Click-to-refine + smart inpaint sampler (FLUX 2 Klein). **Potentially useful for Yggdrasil pipeline.**
- **🆕 BlackSnowSkill/ComfyUI-BSS_FLSampler** ⭐5 (May 21) — Foveated Latent Sampler for ComfyUI. Early but interesting for speed optimizations.
- **🆕 AI-KSK/ComfyUI-AnimaBatchLoraTrainer** ⭐2 (May 19) — Batch LoRA trainer for Anima. Evaluate vs Anima-TrainFlow.
- **🆕 vthiruveedhi/scene-companion-bot** ⭐3 (May 19) — Local-first multimodal roleplay companion with ComfyUI. Niche but interesting pattern.

### Action Items
- [ ] ⚡ **Update pydantic-ai → v1.100.0** — SSRF security fix (supersedes v1.98/v1.99 audit; all three versions should be applied together) (carried over ×6 ⚠️ CRITICALLY OVERDUE)
- [ ] 🔥 **Read pydantic-ai V2 migration guide** — `capabilities` architecture planning (beta, don't upgrade yet) (carried over ×4)
- [ ] **Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×6)
- [ ] **Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×6)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×7)
- [ ] **Test Pixal3D-ComfyUI ⭐95** — 3D Lilith pipeline (carried over ×15)
- [ ] Test comfyui-mesh ⭐98 for multi-GPU FLUX.2 inference (carried over ×17)
- [ ] Evaluate Anima-TrainFlow ⭐44 for 6GB VRAM LoRA training (carried over ×17)
- [ ] Evaluate ANIMA_BOOSTER ⭐15 for RTX 3060 Anima optimization (carried over ×3)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×15)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×14)
- [ ] **Watch ComfyUI-SPEED ⭐22 (↑13 🔺)** — Spectral Progressive Diffusion, fast growth
- [ ] **Watch ComfyUI-Angelo ⭐41** — Click-to-refine inpaint sampler for FLUX 2 Klein
- [ ] Watch ComfyUI-LiTo ⭐55 (↑6) — Apple Research 3D Gaussian Splat growing
- [ ] Watch bytedance/Lance ⭐642 🔺 — surging multimodal model for agent perception
- [ ] Drop facechain from watch list (no releases since Dec 2023)

---

## Radar — 2026-05-24 (Scheduled Scan)

### Key Releases (Δ since May 21 06:04 PM scan)

- **🔥🆕 pydantic-ai v1.102.0** (May 23) — TWO versions since v1.100.0! v1.101.0 adds pending message queue (`ctx.enqueue`), MCP background tasks (SEP-1686), XSearch model-agnostic, `top_k` model setting for Google/Anthropic/Cohere. v1.102.0 patches **another SSRF vulnerability** (GHSA-cg7w-rg45-pc59 — IPv6 transition forms in URL validation), fixes Bedrock strict mode, VercelAIAdapter, and `WebFetchTool` domain matching. **ACTION: Update from v1.99.0 → v1.102.0. All four versions (v1.99→v1.100→v1.101→v1.102) should be applied together.**
- **🔥🆕 pydantic-ai v2.0.0b3** (May 23) — V2 beta has gone from b1→b2→b3 in 3 days. Pulls in v1.102.0 SSRF fix. **ACTION: Read V2 migration guide. Do NOT upgrade yet (beta).**
- **🆕 langgraph v1.2.1** (May 22) — Minor bump from v1.2.0. Low-risk update.
- **🆕 langgraph-checkpoint v4.1.1** (May 22) — New checkpoint library version.
- **🆕 uv v0.11.16** — Bumped from v0.11.15. Low-risk update.
- **🆕 fastapi v0.136.3** — Bumped from v0.136.1. Low-risk update.
- ComfyUI v0.22.0 — No change (MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix).
- transformers v5.9.0 — No change.
- Stable carryovers: diffusers 0.38.0, fastmcp 3.3.1, textual 8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, llama_index v0.14.22, edge-tts 7.2.8

### Trending Repos (Δ since May 21 06:04 PM scan)

- **🔥 Saganaki22/Pixal3D-ComfyUI** ⭐119 (↑24 🔺) — **Explosive growth.** TencentARC Pixal3D → textured GLB. **PRIORITY: Test for 3D Lilith pipeline.**
- **🔥 bytedance/Lance** ⭐854 (↑212 🔺🔺) — 3B multimodal model. **Viral surge continues.** Watch for agent perception use cases.
- **🔥 PozzettiAndrea/ComfyUI-LiTo** ⭐108 (↑53 🔺) — Apple Research LiTo → 3D Gaussian Splat for ComfyUI. **Massive growth — elevate to test priority for 3D Lilith pipeline.**
- **shootthesound/comfyui-mesh** ⭐106 (↑8) — Multi-GPU FLUX.2/LTX 2.3 via NVENC. Steady growth. **Test it.**
- **shootthesound/ComfyUI-Angelo** ⭐72 (↑31 🔺) — Click-to-refine + smart inpaint sampler (FLUX 2 Klein). **Fast growth — useful for Yggdrasil pipeline.**
- **Doorman11991/smallcode** ⭐1393 (↑376 🔺) — 4B active-param coding agent. Viral explosion. Ecosystem relevance only.
- **OpenPipe/ART** ⭐9819 (↑228) — Agent Reinforcement Trainer (GRPO). Ecosystem-scale.
- **evilsocket/audit** ⭐471 (↑73) — 8-stage vulnerability-discovery agent. Security relevance for Hermes.
- **agentic-in/elephant-agent** ⭐463 (↑81) — Self-evolving agent. Ecosystem curiosity.
- **BlackSnowSkill/ANIMA_BOOSTER** ⭐26 (↑11) — Anima DiT 2B optimization. **Growing — helpful for RTX 3060 performance.**
- **ruwwww/ComfyUI-SPEED** ⭐33 (↑11) — Spectral Progressive Diffusion for ComfyUI. Growing.
- **ThetaCursed/Anima-TrainFlow** ⭐47 (↑3) — LoRA trainer Anima 2B, 6GB VRAM. Evaluate.
- **Tencent-Hunyuan/HunyuanWorld-1.0** ⭐2825 — 3D world generation ecosystem. Watch.
- **FranckyB/ComfyUI-DramaBox** ⭐32 — DramaBox narrative generation. Watch.
- **hunhee98/pluck** ⭐34 — MCP-native code retrieval. Watch for Hermes tooling.
- **BasZ4ll/Stable-Diffusion-WebUI** ⭐~633 — Installer GUI viral. Not capability gain. Ignore.

### pydantic-ai v1.101.0 + v1.102.0 — Key Changes for Yggdrasil

- v1.101.0: `ctx.enqueue` / `agent_run.enqueue` pending message queue, MCP background tasks (SEP-1686), XSearch model-agnostic, `top_k` for Google/Anthropic/Cohere, Bedrock Claude Sonnet 4.6/Opus 4.6 thinking fix
- v1.102.0: **SSRF fix** GHSA-cg7w-rg45-pc59 (IPv6 transition forms), Bedrock strict mode fix, VercelAIAdapter fix, `WebFetchTool` domain matching fix
- v2.0.0b3: Pulls in v1.102.0 fixes, no new V2 breaking changes

### Action Items

- [ ] ⚡ **Update pydantic-ai → v1.102.0** — SSRF security fix + `ctx.enqueue` + MCP background tasks. Supersedes v1.98/v1.99/v1.100 audit. Apply all four versions together. (carried over ×7, NOW CRITICAL — 3 versions behind security patches)
- [ ] 🔥 **Read pydantic-ai V2 migration guide** — `capabilities` architecture, V2 beta now at b3 (carried over ×5)
- [ ] **Update langgraph → v1.2.1** — Minor bump from v1.2.0
- [ ] **Update uv → v0.11.16** — Patch bump
- [ ] **Update fastapi → v0.136.3** — Patch bump
- [ ] **Update ComfyUI → v0.22.0** — MoGe 3D, IC-LoRA, LTX 2.3 VRAM fix (carried over ×7)
- [ ] **Test MoGe 3D node** for Lilith 3D asset pipeline (carried over ×7)
- [ ] **Update transformers → v5.9.0** — Cohere2Moe added (carried over ×8)
- [ ] **🔥 Test Pixal3D-ComfyUI ⭐119** — accelerating fast, 3D Lilith pipeline (carried over ×16)
- [ ] **🔥 Test ComfyUI-LiTo ⭐108** — Apple Research 3D Gaussian Splat surging (elevated from watch)
- [ ] Test comfyui-mesh ⭐106 for multi-GPU FLUX.2 inference (carried over ×18)
- [ ] Evaluate Anima-TrainFlow ⭐47 for 6GB VRAM LoRA training (carried over ×18)
- [ ] Evaluate ANIMA_BOOSTER ⭐26 for RTX 3060 Anima optimization (carried over ×4)
- [ ] Test fastmcp v3.3.1 compatibility (carried over ×16)
- [ ] Update textual to v8.2.7 (TUI workspace) (carried over ×15)
- [ ] Watch bytedance/Lance ⭐854 🔺🔺 — explosive multimodal model growth
- [ ] Watch ComfyUI-Angelo ⭐72 🔺 — click-to-refine inpaint for FLUX 2 Klein
- [ ] Watch ComfyUI-SPEED ⭐33 (↑11) — Spectral Progressive Diffusion

## Radar — 2026-05-25 (Manual Scan)

### Key Releases (Δ since May 24 scan)
- **🆕 pydantic-ai v2.0.0b3** (May 23) — Beta update from v2.0.0b2. Read migration guide.
- **🆕 langgraph-sdk sdk==0.3.15** (May 22) — Minor patch update.
- **🆕 fastapi 0.136.3** (May 23) — Patch release.
- **🆕 uv 0.11.16** (May 21) — Patch bump from 0.11.15.

Stable carryovers: ComfyUI v0.22.0, transformers v5.9.0, diffusers 0.38.0, textual v8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, llama_index v0.14.22, fastmcp 3.3.1

### Trending Repos (Δ since May 24 scan)
- **🔥 Merserk/ComfyUI-PiD** ⭐13 (NEW) — NVIDIA PiD pixel diffusion decoding/upscaling for ComfyUI. Potential performance boost.
- **🔥 TileSeaSheave99/Chaos-Enscape-v4-18-Unlocked** ⭐33 (NEW) — Real-time architectural rendering for 3D visualization.
- **🔥 Graphic-Kiliani/QuadLink** ⭐6 (NEW) — Autoregressive quad-dominant mesh generation. Academic but relevant for 3D Lilith pipeline.

### Action Items
- [ ] Watch pydantic-ai v2.0.0b3 — beta updates continue; read migration guide
- [ ] Test ComfyUI-PiD for pixel diffusion upscaling performance
- [ ] Update fastapi → 0.136.3
- [ ] Update uv → 0.11.16
- [ ] Watch langgraph-sdk 0.3.15 — minor graph-based agent framework update
- [ ] Watch QuadLink — quad-dominant mesh generation for 3D pipelines

---

## Radar — 2026-05-26 (Scheduled Scan)

### Key Releases (Δ since May 25 scan)
- **No new releases** since May 25 manual scan. All watched repos unchanged.
- Stable carryovers: pydantic-ai v2.0.0b3, langgraph-sdk 0.3.15, fastapi 0.136.3, uv 0.11.16, ComfyUI v0.22.0, transformers v5.9.0, diffusers 0.38.0, textual v8.2.7, dify 1.14.2, kohya sd-scripts v0.10.5, llama_index v0.14.22, fastmcp 3.3.1

### Trending Repos (Δ since May 25 scan)
- **Merserk/ComfyUI-PiD** ⭐13 — NVIDIA PiD pixel diffusion decoding/upscaling for ComfyUI. Potential performance boost.
- **TileSeaSheave99/Chaos-Enscape-v4-18-Unlocked** ⭐33 — Real-time architectural rendering for 3D visualization.
- **Graphic-Kiliani/QuadLink** ⭐6 — Autoregressive quad-dominant mesh generation. Academic but relevant for 3D Lilith pipeline.

### Action Items (carryovers from May 25 scan)
- [ ] Watch pydantic-ai v2.0.0b3 — beta updates continue; read migration guide
- [ ] Test ComfyUI-PiD for pixel diffusion upscaling performance
- [ ] Update fastapi → 0.136.3
- [ ] Update uv → 0.11.16
- [ ] Watch langgraph-sdk 0.3.15 — minor graph-based agent framework update
- [ ] Watch QuadLink — quad-dominant mesh generation for 3D pipelines

---

*Scan: 2026-05-26 scheduled — Lilith via Yggdrasil Radar*