# Plan: Phase 2 — deploy API (Fly.io) + web (Vercel), end-to-end, ~free

## Outcome (as-built, 2026-06-06) — ✅ DONE & VERIFIED
- **Web (Vercel Hobby, free):** https://acme-salary-web.vercel.app — stable prod alias is
  public; deployment-specific URLs are auth-gated (normal). Project `acme-salary-web`, scope
  `rajaa786`, `VITE_API_BASE` env = the Fly `/api/v1`.
- **API (Fly.io, region `bom`, scale-to-zero):** https://acme-salary-api-rajaa.fly.dev —
  `/healthz` `/readyz` `/docs` 200; seeded **10000** on a 1GB volume `acme_data`. Secrets:
  `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` (from `backend/.env`) + `CORS_ORIGINS=https://acme-salary-web.vercel.app`.
- **Verified:** live `/ask` → 8 rows via `gemini:gemini-2.5-flash`; CORS preflight+GET echo
  the Vercel origin; web bundle bakes the Fly `/api/v1`; machine auto-stops when idle,
  cold-start ~17s → 200. GHCR images `ghcr.io/rajaa786/acme-salary-{api,web}:latest` both PUBLIC.
- **Commits (pushed, `main`=`d8ca284`):** `8bfa17d` fly.toml (app/region/log/autoseed),
  `d8ca284` README live URLs + `GHCR_OWNER=rajaa786`.
- **Deviations from plan below:** (1) Fly flagged the account "high risk" on first
  `apps create` → user unlocked at fly.io/high-risk-unlock, then it worked. (2) Chosen app
  name `acme-salary-api-rajaa` (the bare `acme-salary-api` was taken, as anticipated).
  (3) Vercel gates deployment-specific URLs behind auth — used the public stable alias.
- **Left:** record demo video; fill the one `Demo video:` README placeholder.

---

## Context
The repo is feature-complete and fully pushed (`main` = `6581469` = GitHub HEAD). The
zero-cost reviewer path (GHCR images + `docker-compose.images.yml`) already works. Phase 2
is the **live deployment** so the reviewer has a clickable URL. Deploy artifacts already
exist: [backend/fly.toml](../../backend/fly.toml) (SQLite on volume, scale-to-zero, `/readyz`
check), [web/vercel.json](../../web/vercel.json), and the web client reads `VITE_API_BASE`
([web/src/api/client.ts:5](../../web/src/api/client.ts#L5)).

**Decisions (locked):** Fly.io + SQLite on a persistent volume · real **Gemini** in prod
(encrypted Fly secret) · region **bom** (Mumbai).

**Cost:** Vercel Hobby is free. Fly.io is pay-as-you-go (CC required); with
`min_machines_running=0` it scales to zero ≈ a few cents/mo — effectively free for
assignment traffic, not guaranteed $0. Gemini usage billed to the user's key.

**Split of work — auth is interactive (browser/CC), so the USER does it; tokens are
file-based (`~/.fly/`, `~/.vercel/`), so I drive everything after.**

## Part A — USER prerequisites (one-time, interactive)
1. `brew install flyctl` · `fly auth login` · add a payment method to the Fly org.
2. `brew install vercel-cli` (or `npm i -g vercel`) · `vercel login`.
3. Tell me the Gemini key source is `backend/.env` (gitignored) — I'll read it at deploy
   time and pass to `fly secrets` without printing it.

## Part B — config changes I make first
- `backend/fly.toml`: `primary_region = "iad"` → **`"bom"`**; set a **globally-unique**
  `app` name (Fly app names are global; `acme-salary-api` is likely taken). Use
  `acme-salary-api-<suffix>` and thread that name through the URLs below.
- No code changes — Dockerfile CMD already runs `alembic upgrade head && python -m
  app.seed.bootstrap && uvicorn …`, and `SEED_ON_STARTUP` must be set so the empty volume
  auto-seeds 10k on first boot (add to `[env]` in fly.toml).

## Part C — deploy sequence (I run, after Part A)
1. **API → Fly:** `fly apps create <name>` → `fly volumes create acme_data --region bom
   --size 1 -a <name>` → `fly secrets set LLM_PROVIDER=gemini GEMINI_API_KEY=<from .env>
   -a <name>` → `fly deploy -a <name>` (from `backend/`). Yields `https://<name>.fly.dev`.
2. **Verify API:** `curl …/healthz` 200, `…/readyz` 200, `…/api/v1/employees?limit=1`
   (total ≈ 10000 → seed ran), `POST …/api/v1/ask` → a Gemini answer.
3. **Web → Vercel** (root dir = `web/`): `vercel link` → `vercel env add VITE_API_BASE
   production` = `https://<name>.fly.dev/api/v1` (build-time var, must precede build) →
   `vercel --prod`. Yields `https://<project>.vercel.app`.
4. **Close the CORS loop:** `fly secrets set CORS_ORIGINS=https://<project>.vercel.app
   -a <name>` (triggers machine restart). Browser→API is now allowed.

## Part D — docs + finalize
- Fill README live-URL placeholder ([README.md:162](../../README.md)) with the Vercel URL;
  replace `OWNER/REPO` → `Rajaa786/Assignment` and GHCR `OWNER` → `rajaa786`
  ([README.md](../../README.md)) and the `GHCR_OWNER` default in
  [docker-compose.images.yml](../../docker-compose.images.yml). Demo-video link left as TODO.
- Commit: `chore(deploy): set Fly region bom + autoseed` (fly.toml) and
  `docs: add live demo URLs + GHCR owner`. Push.

## Verification (end-to-end, the proof it "worked properly")
- **API:** `https://<name>.fly.dev/healthz` & `/readyz` → 200; `/docs` loads;
  `/api/v1/employees?limit=1` → `total ≈ 10000`; `/api/v1/ask {"question":"average salary
  by department"}` → rows + `provider: gemini:gemini-2.5-flash` in `fly logs`.
- **Web:** open the Vercel URL → employee list renders (proves `VITE_API_BASE` + CORS),
  analytics charts load, the Q&A box returns an answer from the browser (no CORS error in
  devtools).
- **Free/scale-to-zero:** after ~idle, `fly status -a <name>` shows the machine stopped;
  next request cold-starts it. Confirm no always-on cost.

## Blockers / honesty
- I cannot do `fly auth login` / `vercel login` / add a credit card — those are yours.
- Fly is not strictly $0 (CC required); scale-to-zero makes it ≈free. Flagged, accepted.
- If the chosen app name is taken, Fly errors on `apps create`; I'll pick another and
  re-thread the URL before deploying the web (so `VITE_API_BASE` is never wrong).
