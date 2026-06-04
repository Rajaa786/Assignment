# 0009. Authentication deferred — IdP-proxy production path

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

The product has exactly one persona — a single, trusted HR manager — and is an internal tool with
no public surface (`requirements.md`). The brief asks for salary management and the ability to
answer questions about pay; it does not ask for users, roles, or permissions. Half-built
authentication is a liability: a login form without rotation, lockout, session hardening, and
audit is worse than no login, because it implies a security guarantee it does not keep.

At the same time, a real deployment cannot sit naked on the internet. The question is *where* the
auth boundary lives, not whether one exists.

## Decision

We will **not build authentication in the application**. Production access control is delegated to
an **identity-aware proxy** in front of the API (Cloudflare Access, Tailscale, or an Okta-fronted
ALB). The application stays auth-agnostic, with a clean seam: a single FastAPI dependency
(`get_current_actor`) is the one place a real identity check would attach, and it currently
resolves to a fixed internal actor. Adding auth later means implementing that one dependency, not
threading identity through every endpoint.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| IdP-proxy, app auth-agnostic (chosen) | No half-built security; production-grade SSO without app code; clean future seam | App is not safe to expose without the proxy; documented as such | — |
| Custom JWT/session auth in-app | Self-contained; runnable public out of the box | Real cost to do safely (rotation, lockout, CSRF, audit); scope creep for one trusted user | Effort + risk with no product value for a single persona |
| No auth at all, no documented path | Least work | Leaves the production story undefined; reviewer can't tell intent from omission | We want the decision visible, not implied by absence |

## Consequences

Easier: zero auth code to write, test, or get wrong; endpoints stay focused on salary logic.
Harder: the API must not be exposed publicly without the proxy in place — this is a documented
deployment precondition, not an oversight. We give up "clone and expose to the internet safely"
in exchange for not shipping fragile security. The `get_current_actor` seam keeps the upgrade path
to real auth a single-file change.

## References

- `CLAUDE.md` §8 (security baseline), §18 (scope — auth out)
- `requirements.md` (deliberately out of scope)
