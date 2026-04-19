# Deploy the backend on Render (Web Service) — step by step

This guide deploys **only the FastAPI backend** from [`backend/`](../backend/) as a **Render Web Service**. Your frontend (Vite/React) stays separate (e.g. Render Static Site, Vercel, Netlify, or same-origin behind a CDN).

**Important facts about Render**

| Topic | What to expect |
|--------|------------------|
| **GPU** | Standard Web Services are **CPU-only**. Your RTX 4060 Ti is **not** used. Set `YOLO_DEVICE=cpu` (or `auto`, which resolves to CPU). |
| **RAM** | **Free (512 MB)** usually **runs out of memory** loading Ultralytics + PyTorch. Use **Starter (512 MB–2 GB)** or higher; **Standard 2 GB+** is safer for video jobs. |
| **Disk** | Ephemeral by default — **uploads and reports are lost on redeploy**. For persistence, attach a **Render Disk** and point `DATA_DIR` / `UPLOAD_DIR` / `REPORT_DIR` at the mount path. |
| **WebSockets** | Supported on Web Services. Keep your client on `wss://` when the site uses HTTPS. |
| **Build time** | First build can take **15–25 minutes** (PyTorch + OpenCV + Ultralytics). |

---

## Prerequisites

1. **GitHub (or GitLab) repository** containing this project (Render connects to Git).
2. **Render account** — [https://dashboard.render.com](https://dashboard.render.com).
3. **Frontend URL(s)** you will use in production (for `CORS_ORIGINS`), e.g. `https://my-app.onrender.com` or `https://app.example.com`.

---

## Path A — One-click Blueprint (`render.yaml`)

Best if you want the service defined in Git and reproducible.

### Step 1 — Confirm repo files

At the **repository root** you should have:

- [`render.yaml`](../render.yaml) — defines the Web Service.
- [`backend/scripts/render_build.sh`](../backend/scripts/render_build.sh) — installs **CPU** PyTorch first, then `requirements.txt` (avoids pulling a multi‑GB CUDA wheel onto Render).

### Step 2 — Push to GitHub

```bash
git add render.yaml backend/scripts/render_build.sh docs/DEPLOY-RENDER.md
git commit -m "Add Render blueprint and build script"
git push
```

### Step 3 — Create Blueprint on Render

1. Open [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect your Git provider and select the repository.
3. Render detects `render.yaml` → review the **smart-drone-analyzer-api** service.
4. Click **Apply** (or **Create Blueprint**).

### Step 4 — Set required environment variables (dashboard)

After the service is created, open **Environment** for that Web Service and set:

| Key | Example value | Required |
|-----|----------------|----------|
| `CORS_ORIGINS` | `https://your-frontend.onrender.com` | **Yes** — comma-separated if multiple origins |
| `PYTHON_VERSION` | `3.11.8` | Recommended (matches `render.yaml`) |

Optional tuning:

| Key | Suggested on Render |
|-----|---------------------|
| `YOLO_DEVICE` | `cpu` |
| `YOLO_HALF` | `false` (no FP16 benefit without GPU in most cases) |
| `FRAME_SKIP` | `2` or `3` to reduce CPU load |
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) — align with Render / proxy limits |

### Step 5 — Wait for deploy

1. **Logs** tab — watch `bash scripts/render_build.sh` then `uvicorn` start.
2. When status is **Live**, open **Events** / **URL**: `https://<service-name>.onrender.com`.

### Step 6 — Smoke test

```bash
curl https://<service-name>.onrender.com/api/health
# expect: {"status":"ok"}
```

Open **API docs**: `https://<service-name>.onrender.com/docs`

---

## Path B — Manual Web Service (dashboard only)

Use this if you prefer not to use `render.yaml`.

### Step 1 — New Web Service

1. **New** → **Web Service**.
2. Connect the repository.
3. Configure:

| Field | Value |
|--------|--------|
| **Name** | e.g. `smart-drone-analyzer-api` |
| **Region** | Closest to your users |
| **Branch** | `main` (or your default) |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `bash scripts/render_build.sh` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance type** | **Starter** or higher (avoid Free for this stack) |

### Step 2 — Environment variables

Add the same variables as in Path A, especially **`CORS_ORIGINS`**.

### Step 3 — Health check

Under **Health Check Path** (or in service settings):

```
/api/health
```

### Step 4 — Deploy

Save → Render builds and starts. Test as in Path A, Step 6.

---

## Wire up the frontend

1. **Production API base URL** — `https://<service-name>.onrender.com` (no trailing slash).

2. **Rebuild the frontend** with that URL:

   ```bash
   cd frontend
   echo "VITE_API_URL=https://<service-name>.onrender.com" > .env.production
   npm run build
   ```

   Deploy the `frontend/dist` folder to your static host, **or** set `VITE_API_URL` in that host’s build environment.

3. **CORS** — `CORS_ORIGINS` on Render must **exactly** match the browser origin serving the UI (scheme + host + port), e.g. `https://my-app.netlify.app`.

4. **WebSockets** — the client should connect to:

   `wss://<service-name>.onrender.com/api/ws/<job_id>`

   If you use `VITE_API_URL`, your [`frontend/src/services/api.ts`](../frontend/src/services/api.ts) `wsUrl()` should derive `wss://` from `https://`.

---

## Optional — Persistent disk (uploads survive redeploys)

1. In the Web Service → **Disks** → **Add Disk**.
2. Mount path e.g. `/var/data`.
3. Add environment variables:

   ```text
   DATA_DIR=/var/data
   UPLOAD_DIR=/var/data/uploads
   REPORT_DIR=/var/data/reports
   ```

4. Redeploy. Ensure the app creates directories (your `Settings.ensure_dirs()` already does).

---

## Optional — Custom domain + HTTPS

1. Web Service → **Settings** → **Custom Domain** → add `api.example.com`.
2. Follow Render’s DNS instructions (CNAME).
3. Update frontend `VITE_API_URL` and backend `CORS_ORIGINS` to use `https://api.example.com`.

---

## Troubleshooting

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| Build fails / killed | OOM during `pip install` | Use a **larger plan** or a slimmer dependency set. |
| **Ran out of memory** at runtime | Free / small instance | Upgrade to **Standard 2 GB+**. |
| **502** on upload | Request / body timeout | Increase timeout in Render settings if available; trim video size. |
| **CORS error** in browser | Wrong `CORS_ORIGINS` | Match origin exactly (including `https`). |
| **WebSocket failed** | Mixed content | Use **HTTPS** on the page and **wss://** for the API. |
| Very slow inference | CPU-only | Expected on Render; increase `FRAME_SKIP`, use `yolov8n.pt`. |

---

## Quick reference — commands Render runs

```text
Build:  bash scripts/render_build.sh
Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health: GET /api/health
```

`$PORT` is **injected by Render** — do not hardcode `8000` in the start command.

---

## Related docs

- General deployment options: [DEPLOYMENT.md](DEPLOYMENT.md)
- Local GPU setup: same file, **Part 1 — GPU**.
