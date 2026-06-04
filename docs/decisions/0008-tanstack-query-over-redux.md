# 0008. TanStack Query over Redux for server state

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

Almost all state in this UI is **server state**: employees, analytics, import results, Q&A
answers. Server state is asynchronous, shared, cached, and can go stale — concerns a general state
container does not solve on its own. The little remaining state is local UI (form inputs, which
filter is open), which `useState` handles.

The forces: avoid boilerplate, get caching/refetch/loading/error semantics for free, and keep the
data-fetching layer out of components.

## Decision

We will use **TanStack Query** for all server state and `useState` for local UI state — no Redux.
Each resource gets a typed hook (`useEmployees`, `useEmployee`, `useSummary`, `useAsk`, …) that
owns its query key and fetcher; components never call the query client directly. Lists use an
infinite query keyed on the cursor; mutations invalidate the employee and analytics keys so the UI
stays consistent after a write. Defaults: 30s stale time, retry once, no refetch-on-focus.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| TanStack Query (chosen) | Caching, dedupe, loading/error, pagination built in; tiny per-resource hooks | Another concept to learn; cache invalidation needs thought | — |
| Redux Toolkit (+ RTK Query) | Powerful; RTK Query is similar to TanStack | Redux store/boilerplate for state that is 95% server cache; overkill here | Weight without payoff for a single-user tool |
| `useEffect` + `useState` fetching | No dependency | Re-implements caching, dedupe, race handling, and loading state by hand, badly | Exactly what the charter forbids |

## Consequences

Easier: components read `data/isLoading/error` from a hook and render; refetching and cache
coherence are handled centrally. Harder: we must pick query keys deliberately and invalidate the
right ones on mutation (done in the mutation hooks). We give up a single global store inspector
(Redux DevTools); TanStack's own devtools cover the cache if needed.

## References

- `CLAUDE.md` §2, §12 (server vs UI state)
- Code: `web/src/api/hooks.ts`, `web/src/main.tsx`
