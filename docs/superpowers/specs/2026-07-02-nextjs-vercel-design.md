# FIFA Top Speed — Next.js Rebuild on Vercel

**Date:** 2026-07-02
**Status:** Approved

## Goal

Replace the Streamlit frontend with a Next.js app deployed on Vercel
(Streamlit cannot run there), keeping the liquid-glass design and all
existing functionality. Move the repo to GitHub. Retire the HF Space
after the Vercel site is verified.

## Decisions

- **Data:** static at build. The Dagster `top_speeds` asset writes
  `web/src/data/top_speeds.json` alongside its existing outputs; the
  page imports it. Data refresh = run pipeline + git push (Vercel
  rebuilds on push).
- **Layout:** monorepo — `web/` next to `pipeline/` and `infra/`.
  Vercel project root directory: `web/`.
- **Charts:** hand-rolled responsive SVG React components (no chart
  library).
- **HF Space:** stays live until the Vercel site is verified, then the
  Streamlit app is retired (Space deletion confirmed with user
  separately).

## Architecture

`web/`: Next.js App Router, TypeScript, Tailwind CSS. One statically
generated page; all interactivity client-side over the ~2,300-row JSON.

### Modules

- `src/lib/types.ts` — `SpeedRow { match, team, jersey, player, top_speed_kmh }`.
- `src/lib/stats.ts` — pure functions: gaussian KDE (ported from
  scipy usage, bw_method 0.35 equivalent), team means, top-N
  leaderboard rows, per-player delta rows (players with 2+
  appearances), KPI aggregates.
- `src/lib/scale.ts` — linear scale + tick helpers shared by charts.
- `src/components/GlassCard.tsx` — frosted card primitive.
- `src/components/Hero.tsx`, `KpiCards.tsx`.
- `src/components/FilterBar.tsx` — team/match multiselects (searchable
  chip comboboxes) + three sliders (leaderboard N, delta N, ridgeline
  teams). Sticky below hero. Drives all charts via React state.
- `src/components/charts/Leaderboard.tsx` — horizontal dot plot,
  medals for top 3, hover tooltip.
- `src/components/charts/Ridgeline.tsx` — per-team KDE curves,
  fastest at top, rose mean tick, dashed tournament median.
- `src/components/charts/Dumbbell.tsx` — min→max per player, hollow/
  filled dots, click row to hide, "show all" reset; hidden set resets
  when filters change.
- `src/components/Tooltip.tsx` — shared hover tooltip.
- `src/app/page.tsx` — composition; `layout.tsx` — fonts/meta;
  `globals.css` — gradient backdrop + glass styles.

### Design language

Same as the Streamlit redesign: `#0b1020` base with indigo/rose/cyan
radial gradients, glass cards (`backdrop-blur`, 1px
`rgba(255,255,255,0.12)` border, inner highlight), ink `#e7ecf5`,
accents `#8b9cf9` / `#fb7185`, Inter. Mobile-first; charts scale to
container width via viewBox + measured width.

## Error handling

- Empty filter result → friendly "no data matches" panel (no crash).
- KDE degenerate input (n<2 or zero variance) → skip that team.
- Delta section with no multi-appearance players → info message.
- Data JSON validated at build by a vitest test (shape + row count > 0).

## Testing

- Vitest: stats functions (KDE sanity, top-N, deltas, KPI numbers
  cross-checked against known values from the current CSV), scale/tick
  helpers, data shape.
- `next build` must pass (type checks, static generation).
- Browser verification: desktop + 390px, hover/click interactions.

## Deployment

1. `gh repo create` (user authenticates `gh` first) → push monorepo.
2. Vercel project: root `web/`, framework Next.js, connected to the
   GitHub repo for push-to-deploy (or `vercel` CLI deploy as fallback).
3. Verify production URL, then retire Streamlit (`app.py`, Dockerfile,
   HF frontmatter in README) in a follow-up commit. HF Space deletion
   only with explicit user confirmation.

## Pipeline change

`pipeline/assets.py::top_speeds` additionally writes
`web/src/data/top_speeds.json` (records orient). Tests updated
accordingly.

## Out of scope

- Runtime S3 reads / ISR.
- New analytics beyond the existing three charts + KPIs.
- Auth, multi-tournament support.
