---
name: yggdrasil-health-check
description: Run comprehensive health checks on the Yggdrasil ecosystem — GPU, services, disk, and model inventory.
version: 1.0.0
triggers:
  - health check
  - ecosystem status
  - check services
  - yggdrasil health
---

# Yggdrasil Ecosystem Health Check

Run comprehensive health checks on the Yggdrasil ecosystem using the script at `~/.hermes/scripts/health_check.sh`.

## Modes

### Quick Mode (`--quick` or `-q`)

Checks **only services + GPU**. Fast, suitable for frequent ad-hoc checks.

```bash
bash ~/.hermes/scripts/health_check.sh --quick
```

### Full Mode (default or `--full`)

Checks **services + GPU + disk space + ComfyUI model inventory**. Slower but comprehensive.

```bash
bash ~/.hermes/scripts/health_check.sh --full
# or simply:
bash ~/.hermes/scripts/health_check.sh
```

## What Each Check Covers

### 1. GPU (`nvidia-smi`)

- **What it checks**: GPU name, VRAM total, VRAM used/free, GPU utilization %.
- **PASS**: `nvidia-smi` responds and reports sane values.
- **FAIL**: `nvidia-smi` not found or returns error.

### 2. ComfyUI (`http://localhost:8188/system_stats`)

- **What it checks**: ComfyUI API responds at port 8188.
- **PASS**: HTTP 200 from `/system_stats`.
- **FAIL**: Connection refused, timeout, or non-200 response.

### 3. YggdrasilStudio Backend (`http://localhost:8080/health`)

- **What it checks**: YS backend health endpoint.
- **PASS**: HTTP 200 from `/health`.
- **FAIL**: Connection refused, timeout, or non-200 response.

### 4. YggdrasilStudio Frontend

- **What it checks**: Frontend dev server (Vite on `:5173`) or built frontend (`:8080`).
- **PASS**: Either `localhost:5173` (Vite dev) or `localhost:8080` (built/prod) responds with HTTP 200.
- **FAIL**: Neither port responds.

### 5. LM Studio (`http://localhost:1234/v1/models`)

- **What it checks**: LM Studio OpenAI-compatible endpoint and loaded model name.
- **PASS**: HTTP 200, response contains at least one model ID.
- **FAIL**: Connection refused, timeout, empty model list, or non-200 response.

### 6. Ollama (`http://localhost:11434/api/tags`)

- **What it checks**: Ollama API and available models.
- **PASS**: HTTP 200, response contains at least one model entry.
- **FAIL**: Connection refused, timeout, empty model list, or non-200 response.

### 7. Disk Space (Full mode only)

- **What it checks**: Available space on `/mnt/c`, `/mnt/d`, `/mnt/e`, and WSL root (`/`).
- **Thresholds**:
  - **CRITICAL**: Less than 5 GB free — immediate action required.
  - **WARNING**: Less than 15 GB free — plan cleanup soon.
  - **OK**: 15 GB or more free.
- **FAIL**: Any mount point is CRITICAL (<5 GB) or unreachable.
- **WARN**: Any mount point is in WARNING range (5–15 GB).

### 8. ComfyUI Model Inventory (Full mode only)

- **What it checks**: Scans ComfyUI model directories and counts files for each category:
  - `checkpoints` — main model files
  - `loras` — LoRA adapters
  - `ipadapter` — IP-Adapter models
  - `clip_vision` — CLIP vision encoders
  - `vae` — VAE models
- **PASS**: ComfyUI models directory exists and is readable; reports file counts per category.
- **FAIL**: Models directory missing or unreadable.

## Exit Codes

The script exits with a code equal to the **number of FAIL results**. This enables programmatic alerting:

| Exit Code | Meaning                         |
|-----------|---------------------------------|
| 0         | All checks PASS                 |
| 1         | 1 check FAILED                  |
| 2         | 2 checks FAILED                 |
| N         | N checks FAILED                 |

Use in shell scripts:

```bash
bash ~/.hermes/scripts/health_check.sh
if [ $? -gt 0 ]; then
  echo "ALERT: $failures check(s) failed!"
fi
```

## How to Read Results

The script prints a status table like:

```
[PASS] GPU        — NVIDIA RTX 4090 (24 GB VRAM, 12.3 GB used, 67% util)
[PASS] ComfyUI    — http://localhost:8188 (responding)
[FAIL] YS Backend — http://localhost:8080 (connection refused)
[PASS] YS Frontend— http://localhost:5173 (Vite dev server)
[PASS] LM Studio  — http://localhost:1234 (model: meta-llama-3.1-8b)
[PASS] Ollama     — http://localhost:11434 (3 models loaded)
[WARN] Disk /mnt/d— 8.2 GB free (WARNING: < 15 GB)
[PASS] Models     — 12 checkpoints, 45 loras, 3 ipadapter, 2 clip_vision, 4 vae
```

## What to Do on Failure

- **GPU FAIL**: Verify `nvidia-smi` works. Check if NVIDIA drivers are installed/updated. On WSL2, ensure the GPU driver on the Windows host is current.
- **Service FAIL (ComfyUI, YS Backend/Frontend, LM Studio, Ollama)**: Check if the service process is running (`ps aux | grep <name>`). Restart the service if needed. Check logs for errors.
- **Disk CRITICAL**: Delete or move files immediately. Targets: Windows temp files, old Docker images (`docker system prune`), large model caches.
- **Disk WARNING**: Plan cleanup within the next few days. Identify large directories with `du -sh /mnt/c/Users/*/Downloads` or similar.
- **Models FAIL**: Verify the ComfyUI models directory path is correct and readable. Check file permissions.

## Quick Reference

```bash
# Quick check (services + GPU only)
bash ~/.hermes/scripts/health_check.sh -q

# Full check (services + GPU + disk + models)
bash ~/.hermes/scripts/health_check.sh

# Capture exit code for alerting
bash ~/.hermes/scripts/health_check.sh --quick
echo "Failures: $?"
```