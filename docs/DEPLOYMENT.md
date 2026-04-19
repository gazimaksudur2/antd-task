# Deployment guide — Smart Drone Traffic Analyzer

This document walks through **using your NVIDIA GPU locally** and **deploying** the stack (backend + frontend) for production-style hosting.

---

## Part 1 — Does the app use your GPU today?

### How it works in code

- Inference runs through **Ultralytics YOLO** with `device` set from your config (default **`YOLO_DEVICE=auto`**).
- **`auto`** means: use **`cuda`** if `torch.cuda.is_available()` is true, otherwise **CPU**.

So the RTX 4060 Ti **is used only if**:

1. **NVIDIA drivers** are installed (GeForce / Studio driver is fine).
2. **PyTorch with CUDA** is installed in the same virtualenv as the backend.

The usual problem on Windows: `pip install -r requirements.txt` pulls a **CPU-only** PyTorch wheel. Then `torch.cuda.is_available()` is **false** and everything runs on CPU even though you have a GPU.

### Verify from a terminal

```powershell
cd D:\Tasks\Antd-task\backend
.\.venv\Scripts\Activate.ps1
python -c "import torch; print('cuda_available:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'n/a')"
```

- If you see `cuda_available: True` and your GPU name → the app **will** use the GPU with `YOLO_DEVICE=auto`.
- If `cuda_available: False` → install CUDA-enabled PyTorch (next section).

### Install PyTorch with CUDA (Windows, RTX 4060 Ti)

1. Open [PyTorch — Get Started](https://pytorch.org/get-started/locally/).
2. Choose **Stable**, **Windows**, **Pip**, **Python**, **CUDA 12.4** (or the newest CUDA build offered for your Python version).
3. Run the **exact** command the site shows **inside your backend venv**, for example:

```powershell
.\.venv\Scripts\Activate.ps1
pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

4. Re-run the one-liner check above until `cuda_available: True`.

5. (Optional) Faster inference on RTX — in `backend/.env`:

```env
YOLO_DEVICE=auto
YOLO_HALF=true
```

`YOLO_HALF=true` enables **FP16** on CUDA (good fit for Ada Lovelace / RTX 40-series).

6. Start the API and watch logs on first job: you should see a line like  
   `CUDA device 0: NVIDIA GeForce RTX 4060 Ti ...` and `YOLO inference device: cuda:0 (half_precision=True)`.

### Force CPU (debugging)

```env
YOLO_DEVICE=cpu
```

### Force a specific GPU

```env
YOLO_DEVICE=cuda:0
```

---

## Part 2 — Step-by-step deployment overview

Pick **one** path. Most teams use **Docker on a Linux VPS** for production; **Windows + Docker Desktop** is fine for demos.

### A) Prerequisites (all paths)

| Item | Notes |
|------|--------|
| Machine | Linux x86_64 VPS (e.g. Ubuntu 22.04/24.04) or Windows Server with Docker |
| RAM | 8 GB minimum; 16 GB+ if processing long 4K clips |
| Disk | Enough space for uploads + reports + Docker images |
| Domain (optional) | For HTTPS and clean URLs |
| GPU (optional) | For faster inference: NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on Linux |

---

### B) Deploy with Docker Compose (recommended baseline)

This repo ships [`docker-compose.yml`](../docker-compose.yml) with **frontend** (nginx + static React build) and **backend** (FastAPI + CPU PyTorch image by default).

1. **Clone** the repository on the server.

2. **Set production environment** for the backend (create `backend/.env` or use compose `environment:`):

   - `CORS_ORIGINS=https://your-domain.com` (comma-separated if multiple origins).
   - `HOST=0.0.0.0`, `PORT=8000` (internal; nginx proxies to this).
   - Optional: `YOLO_MODEL=yolov8s.pt` for better accuracy at the cost of speed.

3. **Build frontend with the public API URL** (so the browser calls your domain, not localhost):

   ```bash
   # Linux / macOS example — set to your real API origin
   export VITE_API_URL=https://api.your-domain.com
   docker compose build --build-arg VITE_API_URL=$VITE_API_URL
   ```

   On Windows PowerShell:

   ```powershell
   $env:VITE_API_URL="https://api.your-domain.com"
   docker compose build --build-arg VITE_API_URL=$env:VITE_API_URL
   ```

   If frontend and API are **same origin** (one domain, nginx proxies `/api` to backend), you can leave `VITE_API_URL` empty and rely on relative URLs (matches default `nginx.conf` in `frontend/`).

4. **Start**:

   ```bash
   docker compose up -d --build
   ```

5. **Smoke test**:

   - Open `http://SERVER_IP:3000` (or map host 80 in compose).
   - Upload a short MP4; confirm progress and download links.

6. **TLS (HTTPS)** — put **Caddy** or **nginx** on the host in front of ports 80/443, terminate TLS, and `proxy_pass` to `localhost:3000` (or serve only frontend and proxy `/api` + `/api/ws` to port 8000). WebSockets need:

   ```nginx
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```

---

### C) GPU in Docker (Linux + NVIDIA)

The default `backend/Dockerfile` uses **CPU** PyTorch from pip. For **GPU inside the container**:

1. Install **NVIDIA Container Toolkit** on the host.
2. Use an official **PyTorch CUDA** base image or install `torch` with CUDA in the Dockerfile.
3. Extend `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
```

Exact keys depend on Docker Compose v2 vs Swarm; see [NVIDIA GPU in Compose](https://docs.docker.com/compose/gpu-support/).

---

### D) Deploy without Docker (“bare metal”)

**Backend**

1. Install Python 3.11+, create venv, `pip install -r requirements.txt`.
2. Install **CUDA PyTorch** if you want GPU (same as Part 1).
3. Run under a process manager:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
   ```

   Use **1 worker** for in-memory job state unless you refactor to Redis + workers.

4. Put **nginx** or **Caddy** in front for TLS, body size (e.g. `client_max_body_size 525M`), and WebSocket headers.

**Frontend**

1. `cd frontend && npm ci && npm run build`
2. Set `VITE_API_URL` at build time if the API is on another host.
3. Serve `frontend/dist` with nginx (`try_files` SPA fallback).

---

### E) Checklist before going live

- [ ] `CORS_ORIGINS` matches the real browser origin(s).
- [ ] Upload size limits aligned (`MAX_UPLOAD_BYTES`, reverse proxy `client_max_body_size`).
- [ ] WebSocket path `/api/ws/` proxied with upgrade headers.
- [ ] Disk retention / backups for `data/uploads` and `data/reports` (or move to S3 later).
- [ ] Secrets not committed (`.env` in `.gitignore`).
- [ ] Firewall: only 80/443 (and SSH) open publicly.

---

### F) Optional cloud patterns

- **Single VM**: Docker Compose as above.
- **Split**: Static site on **S3 + CloudFront**; API on **ECS / Cloud Run / VM** (WebSockets need sticky routing or dedicated URL).
- **GPU cloud**: AWS **g4dn** / Azure **NC** series + same Docker GPU steps.

---

## Quick reference — environment variables

| Variable | Typical production value |
|----------|---------------------------|
| `CORS_ORIGINS` | `https://app.example.com` |
| `YOLO_DEVICE` | `auto` or `cuda:0` on GPU hosts |
| `YOLO_HALF` | `true` on RTX for speed |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) or your policy |
| `FILE_RETENTION_HOURS` | `24` or higher per compliance |

Frontend build-time:

| Variable | When to set |
|----------|-------------|
| `VITE_API_URL` | API on a different origin than the static site (e.g. `https://api.example.com`) |

If the UI and API share one domain and nginx proxies `/api`, leave `VITE_API_URL` empty.
