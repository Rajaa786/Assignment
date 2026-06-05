# 0011. Publish images to GHCR + auto-seed for zero-effort reviewer onboarding

- **Status**: Accepted
- **Date**: 2026-06-05
- **Deciders**: Raj Singh

## Context

This is a hiring assessment: the reviewer's time-to-running-app is itself part of the experience.
Building from source needs Docker plus a successful multi-stage build; even `docker compose up`
requires cloning the repo and (previously) a manual seed step before there was any data to look at.
We want the reviewer to go from nothing to a populated, running app in one command, without
installing a toolchain or reading setup instructions.

Two frictions to remove: **building** (slow, can fail on the reviewer's machine) and **empty
database** (a running app with no data looks broken).

## Decision

We will **publish prebuilt images to GHCR** and **auto-seed on first start**:

- A GitHub Actions workflow builds the API and web images for `linux/amd64,linux/arm64` and pushes
  them to `ghcr.io/<owner>/acme-salary-{api,web}` using the built-in `GITHUB_TOKEN` — no extra
  account or secret. Packages are made public so pulls are anonymous.
- The API container bootstrap runs migrations, then (when `SEED_ON_STARTUP=true`) seeds 10k
  employees **only if the database is empty** — idempotent, so restarts never wipe data. The flag is
  off by default, so local dev and tests never auto-seed.
- A tiny `docker-compose.images.yml` references the published images, so the reviewer downloads one
  file and runs `docker compose up` — no clone, no build, data already loaded.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| GHCR images + auto-seed (chosen) | One command; no build/toolchain; multi-arch; uses the repo's own CI token | Images can lag source; packages must be set public once | — |
| Docker Hub | Familiar `docker pull user/img` | Needs a separate account + `DOCKERHUB_TOKEN` secret | Extra account/secret for no benefit over GHCR |
| Build-from-source only | Nothing to publish | Reviewer must build (slow, can fail on their machine) | More friction, the thing we're removing |
| Manual seed step | Explicit; no startup logic | A bare running app looks empty/broken; one more command | Auto-seed-if-empty is safer and frictionless |

## Consequences

Easier: a reviewer runs one command and sees a populated app; the same images deploy to Fly
unchanged (set `SEED_ON_STARTUP=true` there too). Harder: published images can drift from `main`
until CI re-runs (mitigated by building on every push), and the GHCR packages must be flipped to
Public once. We accept a small amount of "magic" at container start (the seed bootstrap) in exchange
for the onboarding win; it is gated by an env flag and logs exactly what it did.

## References

- `CLAUDE.md` §2 (Docker, CI), §9 (seed performance)
- Code: `.github/workflows/release-images.yml`, `docker-compose.images.yml`,
  `app/seed/bootstrap.py`, `app/seed/seed.py` (`seed_if_empty`)
