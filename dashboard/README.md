# SignalLock Dashboard

A Next.js 15 + TypeScript + Tailwind dashboard for the SignalLock Audit and Interactive modes. Talks to the FastAPI backend over HTTP.

## Pages

| Route | Purpose |
|---|---|
| `/` | Org-level exposure heatmap with band filters and sort |
| `/users/[id]` | Per-user drill-down: exposure factors, component scores, profile snapshot, interactive password tester |
| `/test` | Standalone password tester — pick any profile, score a candidate password, see heuristic vs ML side-by-side and the full explanation paragraph |

## Local development

The dashboard requires the FastAPI server to be running with CORS enabled.

**1. Start the API** (in one terminal, from the project root):

```bash
.venv/bin/python -m signallock serve \
  --port 8000 \
  --cors-origins http://localhost:3000
```

To enable the ML-assisted toggle and `compare-scoring` panel, add `--model-file <path-to-pkl>`.

**2. Install dashboard deps** (one-time):

```bash
cd dashboard
npm install
```

**3. Start the dev server**:

```bash
npm run dev
```

Visit `http://localhost:3000`.

## Configuration

Override the API base URL:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:9000 npm run dev
```

## Production build

```bash
npm run build
npm run start
```

## Validation

```bash
npm run type-check
```

The current `npm run type-check` command uses a non-interactive Next.js build-backed validation path. This is intentional: the dashboard relies on Next-generated route/type artifacts, so a plain `tsc --noEmit` pass is not the most reliable standalone check for this app.

The current `npm run lint` script is also intentionally non-interactive and aliases the same validation path until an explicit ESLint config is added to the dashboard.

Equivalent direct build check:

```bash
npm run build
```

## Stack

- Next.js 15 (App Router)
- React 19
- TypeScript 5
- Tailwind CSS 3
