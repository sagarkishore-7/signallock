# SignalLock — Deployment Guide

This document walks you through hosting the **backend on Railway** and the **dashboard on Vercel**, then wiring them together with CORS so the live dashboard can talk to the live API.

The backend deployment path is now **Dockerfile-first**. Railway will use the root `Dockerfile` automatically, which avoids builder drift and ensures the `signallock` package and repo-root `configs/` directory are present in the runtime image.

---

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  signallock-dashboard       │         │  signallock-api              │
│  Next.js 15 on Vercel       │ ──HTTP──▶│  FastAPI on Railway          │
│  https://...vercel.app      │         │  https://...railway.app      │
└─────────────────────────────┘         └──────────────────────────────┘
        ▲                                         ▲
        │ NEXT_PUBLIC_API_BASE                    │ MODEL_FILE, CORS_ORIGINS
        │                                         │
   set in Vercel project                     set in Railway service
```

The backend is **stateless** by design — no database, no per-user storage, no password logging. Everything is computed per request.

---

## Part 1 — Deploy the backend on Railway

### 1.1. Push the repo to GitHub

```bash
cd "/path/to/SignalLock"
git add .
git commit -m "feat: deployment configuration for Railway and Vercel"
git push origin main
```

The repository already includes the necessary deployment files at the project root:

| File | Purpose |
|---|---|
| `Dockerfile` | Deterministic backend image build for Railway |
| `.dockerignore` | Keeps the Railway build context lean while still allowing optional committed model artifacts |
| `pyproject.toml` | Declares dependencies and the optional `ml` and `api` extras |
| `railway.json` | Health-check and restart-policy configuration |
| `.python-version` | Local Python pin; not used by the Docker deployment path |
| `Procfile` | Optional fallback start command for non-Docker platforms |

### 1.2. Create the Railway service

1. Sign in to [railway.com](https://railway.com).
2. **New Project → Deploy from GitHub repo** → select your `signallock` repository.
3. Railway will detect the root `Dockerfile` and build the backend image from it. No custom build command is required.
4. Once the build finishes, Railway exposes a public URL like `https://signallock-production.up.railway.app`.

### 1.2.a. What the Docker image does

The image:

- starts from `python:3.13-slim`,
- copies `src/` and `configs/`,
- installs `signallock[ml,api]`,
- creates an empty `artifacts/` directory for runtime outputs,
- sets `SIGNALLOCK_PROJECT_ROOT=/app` so the installed package can still resolve repo-root configs and artifacts,
- starts the API with `python -m signallock serve --host 0.0.0.0`.

This matters because SignalLock resolves several runtime config files from the repo root, including:

- `configs/policy_profiles.json`
- `configs/experiment_presets.json`
- `configs/threshold_sweep_presets.json`

The Dockerfile preserves that layout explicitly.

### 1.3. Configure environment variables in Railway

Open your Railway service → **Variables** tab and add:

| Variable | Required | Value |
|---|---|---|
| `PORT` | auto-set by Railway | leave blank |
| `HOST` | optional | `0.0.0.0` (the Docker image already starts the API on `0.0.0.0`) |
| `CORS_ORIGINS` | **required for the dashboard to work** | `https://your-dashboard.vercel.app` (you'll set this after Vercel deploy — fill it back in then) |
| `MODEL_FILE` | optional | path to a `.pkl` file inside the deployed image if you ship one yourself (see § 1.5) |

**Save** — Railway will redeploy automatically.

### 1.4. Verify the API is live

```bash
curl https://your-app.up.railway.app/healthz
# → {"status":"ok","version":"0.1.0","model_loaded":false}

curl https://your-app.up.railway.app/policies
# → [{"profile":"balanced",...}, {"profile":"strict",...}, ...]

curl https://your-app.up.railway.app/demo/profiles?count=3
# → {"count":3,"profiles":[...]}
```

If `/healthz` returns 200, the backend is live.

### 1.5. (Optional) Ship an ML model in the image

The default Railway image runs in heuristic mode and does **not** copy your local `artifacts/` directory into the container. That is intentional: `artifacts/` is treated as local output, is gitignored by default, and often does not exist in the repository at all.

If you want to enable `?ml=true` or `/compare-scoring` in production, you need to intentionally ship a tracked model artifact inside the image and point `MODEL_FILE` at it.

A simple pattern is:

1. Train a model locally:

   ```bash
   .venv/bin/python -m signallock train-model \
     --count 100 --seed 1 --model-type gradient_boosting \
     --save-model --output-dir artifacts/models
   ```

2. Move or copy the selected `.pkl` into a tracked location in the repo, update the Dockerfile to copy that location into the image, and commit the change.

3. Set the Railway env var to the in-image path:

   ```
   MODEL_FILE = /app/<your-tracked-model-path>/model_gradient_boosting.pkl
   ```

4. Redeploy. Verify with:

   ```bash
   curl https://your-app.up.railway.app/healthz
   # → {"status":"ok","version":"0.1.0","model_loaded":true}
   ```

If you do not need ML-backed scoring in the deployed demo, leave `MODEL_FILE` unset. The backend, dashboard, and heuristic scoring flows still work normally.

---

## Part 2 — Deploy the dashboard on Vercel

### 2.1. Create the Vercel project

1. Sign in to [vercel.com](https://vercel.com).
2. **Add New → Project** → import the same GitHub repository.
3. **Root Directory:** click `Edit` and set it to `dashboard`. This is critical — Vercel must build from `dashboard/`, not from the project root.
4. Vercel auto-detects Next.js. Defaults are correct (`npm install`, `npm run build`).

### 2.2. Configure the API endpoint

In the Vercel project settings, add:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE` | `https://your-app.up.railway.app` (no trailing slash) |

This is read at build time and bakes the API URL into the static bundle. The `NEXT_PUBLIC_` prefix is required for Next.js to expose it client-side.

Click **Deploy**. After ~1 minute you'll have a URL like `https://signallock-dashboard.vercel.app`.

### 2.3. Wire CORS back to Railway

The dashboard is now live but the API will reject its requests until you allow its origin.

1. Copy your Vercel URL: `https://signallock-dashboard.vercel.app`.
2. Open the Railway service → **Variables** → set:

   ```
   CORS_ORIGINS = https://signallock-dashboard.vercel.app
   ```

3. Save — Railway redeploys.

If you have multiple Vercel deployments (preview branches, custom domains), space-separate them:

```
CORS_ORIGINS = https://signallock-dashboard.vercel.app https://your-custom-domain.com
```

### 2.4. Verify the live integration

Open `https://signallock-dashboard.vercel.app` in a browser:

- The header should show **API connected · heuristic** (or **ML** if you shipped a model).
- The roster should populate with synthetic profiles.
- Drill into any user and try the password tester.

If you see **API offline**, open the browser console — it's almost always a CORS misconfiguration. Double-check the exact origin (including `https://` and no trailing slash) matches what you set in `CORS_ORIGINS`.

---

## Part 3 — Local development against the live backend

You can also run the dashboard locally and point it at the deployed Railway API:

```bash
cd dashboard
NEXT_PUBLIC_API_BASE=https://your-app.up.railway.app npm run dev
```

Just make sure `http://localhost:3000` is in `CORS_ORIGINS` on Railway.

---

## Part 4 — Updating

| Change | Action |
|---|---|
| Edit Python code | `git push` — Railway rebuilds the Docker image and redeploys automatically |
| Edit dashboard code | `git push` — Vercel redeploys automatically |
| Add CORS origin | Update `CORS_ORIGINS` env var on Railway |
| Swap the trained model | Replace the `.pkl` file in the repo, update `MODEL_FILE`, redeploy |
| Bump dependencies | Update `pyproject.toml` (backend) or `dashboard/package.json` (frontend) and push |

---

## Part 5 — Costs

**Railway** has a free trial then $5/mo for hobby projects. The SignalLock API uses very little CPU and ~150 MB RAM (mostly scikit-learn + uvicorn).

**Vercel** has a generous Hobby tier that covers this dashboard for free indefinitely (well under bandwidth and build-minute caps for a research demo).

---

## Troubleshooting

**"API offline" in the dashboard header**
- The browser cannot reach the Railway URL. Open `https://...railway.app/healthz` directly and check the response.
- If healthz responds but the dashboard still fails: it's CORS. Look for `Access-Control-Allow-Origin` mismatch in the browser network tab.

**Railway starts the container but crashes with `No module named signallock`**
- This usually means Railway is still deploying through an older non-Docker builder path or a stale service configuration.
- Confirm the repository root contains a file named exactly `Dockerfile` with a capital `D`.
- In Railway build logs, verify it says the Dockerfile is being used.
- Remove any old custom build/start overrides in the Railway service settings if they conflict with the repo config, then redeploy.

**Railway build fails on `pip install`**
- Confirm the service is building from the root `Dockerfile`, not an older Nixpacks/Nix-based configuration.
- Check the build log around `pip install ".[ml,api]"` for the failing dependency.
- If you changed the model extras or Python version recently, redeploy from a clean commit so Railway rebuilds the image from scratch.

**`/compare-scoring` returns 503**
- The server was started without `MODEL_FILE`. Set it in Railway and redeploy.

**Dashboard build fails on Vercel with "Cannot find module"**
- Make sure the **Root Directory** is set to `dashboard`. Without that, Vercel builds from the repo root and fails to find `package.json`.

**Slow first request after idle**
- Railway's hobby tier puts services to sleep after inactivity. The first request after wake-up takes ~3–5 seconds. This is fine for a demo.
