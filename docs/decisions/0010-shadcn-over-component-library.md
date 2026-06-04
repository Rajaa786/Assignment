# 0010. shadcn/ui over Material UI / Chakra

- **Status**: Accepted
- **Date**: 2026-06-04
- **Deciders**: Raj Singh

## Context

The UI needs a small set of primitives — buttons, cards, inputs, selects, tables, badges — with a
clean, professional look and full control over styling. The choice of component layer affects bundle
size, how much we fight the library's opinions, and how easy it is for a reviewer to read the
component code.

## Decision

We will use **shadcn/ui**: Tailwind-styled components **copied into the repo** (under
`components/ui/`) rather than imported from a package. We own the source, so components are plain,
readable React + Tailwind with no runtime theming layer. We add only the primitives we actually use,
plus the small helpers shadcn relies on (`clsx`, `tailwind-merge`, `class-variance-authority`) and
`lucide-react` for icons. Recharts handles charts.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| shadcn/ui (chosen) | Own the code; tiny, readable; Tailwind = full control; no theme runtime | Must copy/maintain components yourself | — |
| Material UI | Comprehensive; DataGrid included | Heavy; strong visual opinions; theming API to fight; larger bundle | More than a single-user internal tool needs |
| Chakra UI | Good DX; accessible | Runtime styling system; another API to learn; heavier than Tailwind | Tailwind + shadcn is leaner and more transparent |

## Consequences

Easier: components are in the repo and trivially customizable; the bundle carries only what we use;
styling is consistent with Tailwind tokens. Harder: we maintain the primitives ourselves and add
new ones by hand as needed (a small, well-understood cost). We deliberately keep the set minimal
(native `<select>` instead of a Radix combobox, etc.) rather than pulling in every primitive.

## References

- `CLAUDE.md` §2, §12
- Code: `web/src/components/ui/`
