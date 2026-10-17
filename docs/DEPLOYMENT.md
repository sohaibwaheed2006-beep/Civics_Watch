# Deployment Guide — Frontend on Vercel, Backend on Render

This walks you through deploying the whole app for the first time:

- **Frontend** (Vite + React) → **Vercel**
- **Backend** (FastAPI) → **Render**
- **Database + photo storage** → **Supabase** (Postgres + Storage bucket)

```
  Browser ──> Vercel (React SPA) ──API calls──> Render (FastAPI) ──> Supabase Postgres
                                                     │
  Browser <────────── photo <img> ─────────────────-┴─> Supabase Storage (public bucket)
```

You need four free accounts: **GitHub**, **Supabase**, **Render**, **Vercel**.

> Deploy from the branch that actually has this code. If your work is on the
> `backend` branch, either merge it into `main` first or pick that branch in the
> Render/Vercel UI when prompted.

---

## Step 0 — Push to GitHub

```powershell
git add -A
git commit -m "Add deployment config (Vercel + Render) and Supabase photo storage"
git push
```

The repo already contains the deploy config this guide relies on: `vercel.json`,
`.vercelignore`, and `render.yaml`.

---

## Step 1 — Supabase (database + photo bucket)

1. Create a project at **supabase.com** → set a database password (save it).
2. **Database URL** — Project Settings → **Database** → *Connection string* →
   **Transaction** pooler (port **6543**). Copy it and change the prefix to the
   SQLAlchemy driver form:
   ```
   postgresql+psycopg2://postgres.<ref>:<your-password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```
   (Use the *Transaction* pooler, not the direct 5432 connection — it's the one
   built for short-lived app connections.)
3. **API credentials** — Project Settings → **API**:
   - `Project URL` → `https://<project-id>.supabase.co`
   - `service_role` secret key (under Project API keys). **Server-side only.**
4. **Storage bucket for photos** — Storage → **New bucket**:
   - Name: `report-photos`
   - **Public bucket: ON** (so uploaded photos are viewable via a CDN URL)

Keep these three values handy: the `postgresql+psycopg2://…` URL, the project
URL, and the service-role key.

---

## Step 2 — Backend on Render

1. **render.com** → **New** → **Blueprint** → connect your GitHub repo.
2. Render reads `render.yaml` and creates a web service `nir-backend`. It will
   **prompt you for the secret env vars** (`sync: false`). Fill them in:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | the `postgresql+psycopg2://…` pooler URL from Step 1 |
   | `SUPABASE_URL` | `https://<project-id>.supabase.co` |
   | `SUPABASE_SECRET_KEY` | the service-role secret key |
   | `CORS_ORIGINS` | *leave blank for now — set in Step 4* (e.g. `https://your-app.vercel.app`) |
   | `FRONTEND_BASE_URL` | *same as above, set in Step 4* |

   These are set for you automatically by `render.yaml`: `SECRET_KEY` (generated),
   `APP_ENV=production`, `DEBUG=false`, `PHOTO_STORAGE_BACKEND=supabase`,
   `SUPABASE_STORAGE_BUCKET=report-photos`, `PYTHON_VERSION`.

3. Click **Apply**. Render will:
   - `pip install -r requirements.txt`
   - run `alembic upgrade head` (creates all tables **and seeds the three
     departments + nine field-worker accounts**)
   - start `uvicorn app.main:app`
4. When it's live, copy the service URL, e.g. `https://nir-backend.onrender.com`.
   Verify it:
   - open `https://nir-backend.onrender.com/health` → should return a healthy JSON
   - open `https://nir-backend.onrender.com/docs` → interactive API docs

> **Free-tier note:** the service sleeps after ~15 min idle; the first request
> after that cold-starts in a few seconds. Normal for the free plan.

---

## Step 3 — Frontend on Vercel

1. **vercel.com** → **Add New** → **Project** → import the same GitHub repo.
2. Vercel auto-detects **Vite** (build `npm run build`, output `dist` — already
   pinned in `vercel.json`). Leave the build settings as-is.
3. Add **Environment Variables**:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://nir-backend.onrender.com/api/v1` |
   | `VITE_ENABLE_MOCK_FALLBACK` | `false` |
   | `VITE_APP_NAME` | `Neighborhood Issue Reporter` |

   > Important: include the `/api/v1` suffix on `VITE_API_BASE_URL`, and set
   > `VITE_ENABLE_MOCK_FALLBACK=false` so the app talks to the real backend
   > instead of silently using demo data.

4. **Deploy.** You'll get `https://your-app.vercel.app`.

---

## Step 4 — Connect the two origins (CORS)

The backend must allow the browser origin that Vercel gave you.

1. In **Render** → `nir-backend` → **Environment**, set:
   - `CORS_ORIGINS` = `https://your-app.vercel.app`
   - `FRONTEND_BASE_URL` = `https://your-app.vercel.app`  *(no trailing slash)*
2. Save → Render redeploys automatically.

(If you later add a custom domain, put both origins comma-separated:
`CORS_ORIGINS=https://your-app.vercel.app,https://www.yourdomain.com`.)

---

## Step 5 — First login & creating an admin

After `alembic upgrade head`, these **worker** accounts exist immediately
(password `Password123!` for all): `worker@example.com`, `elena.worker@example.com`,
`amara.worker@example.com`, … (nine total).

There is **no admin or citizen seeded**. To create them:

- **Citizen:** just use **Register** in the app.
- **Admin:** register normally, then promote the account in **Supabase → SQL
  Editor**:
  ```sql
  update users
  set role = 'admin', is_verified = true
  where email = 'you@example.com';
  ```
  Log out and back in — you now have the admin portal.

Test the full loop: sign in, file a report **with a photo**, and confirm the
photo displays (it's served from the Supabase public bucket, so its URL looks
like `https://<project>.supabase.co/storage/v1/object/public/report-photos/…`).

---

## Everyday workflow after setup

- **Push to the deployed branch** → Vercel and Render both auto-rebuild.
- **Backend logs / errors:** Render dashboard → Logs.
- **Frontend build logs:** Vercel dashboard → Deployments.
- **Change a secret:** update it in the Render/Vercel dashboard (not in git).

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Frontend loads but every API call fails / CORS error in console | `CORS_ORIGINS` on Render doesn't match the Vercel URL exactly (scheme + host, no trailing slash). Fix and redeploy. |
| App shows data but it's obviously fake / never changes | `VITE_ENABLE_MOCK_FALLBACK` is `true`, or `VITE_API_BASE_URL` is unset/misspelled. It must point at `https://<render>/api/v1`. |
| 404s on refresh of a deep link (e.g. `/admin/reports`) | `vercel.json` rewrite missing — it's included here; make sure it was committed. |
| Backend deploy fails on `alembic upgrade head` | `DATABASE_URL` wrong. It must start with `postgresql+psycopg2://` and use the **pooler** host on port 6543. |
| Uploaded photos don't appear | Bucket not **public**, or its name ≠ `SUPABASE_STORAGE_BUCKET` (`report-photos`), or `SUPABASE_SECRET_KEY`/`SUPABASE_URL` not set on Render. |
| First request after idle is slow | Render free-tier cold start — expected. Upgrade the plan to keep it warm. |
| Can't log in as admin | No admin is seeded; register, then run the promote-to-admin SQL above. |

---

## What's configured in the repo (reference)

- `vercel.json` — Vite build + SPA rewrite for client-side routes.
- `.vercelignore` — keeps the Python backend out of the frontend deploy.
- `render.yaml` — the FastAPI web service: build/start commands, health check,
  and the env-var contract (secrets prompted, non-secrets preset).
- `PHOTO_STORAGE_BACKEND=supabase` (set on Render) switches photo storage from
  local disk to the Supabase bucket, so uploads survive restarts and their URLs
  work from any origin. Locally it defaults to `local`, so nothing changes for
  development.
