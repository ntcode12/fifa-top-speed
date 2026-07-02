# Next.js Liquid-Glass Explorer on Vercel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the FIFA top-speed explorer as a Next.js app in `web/`, deploy on Vercel via a new GitHub repo, then retire the Streamlit frontend.

**Architecture:** Statically generated single page; all interactivity client-side over a build-time JSON snapshot (`web/src/data/top_speeds.json`, written by the Dagster pipeline). Hand-rolled responsive SVG charts. Liquid-glass design identical to the current Streamlit theme.

**Tech Stack:** Next.js (App Router) + TypeScript + Tailwind CSS v4, Vitest for unit tests, gh CLI + Vercel CLI for deployment.

## Global Constraints

- App lives in `web/` (monorepo root also holds `pipeline/`, `infra/`).
- Palette: backdrop `#0b1020` with radial gradients `rgba(99,102,241,0.28)` / `rgba(225,29,72,0.16)` / `rgba(56,189,248,0.12)`; ink `#e7ecf5`; dim `#8b93a7`; accents indigo `#8b9cf9`, rose `#fb7185`; glass = `backdrop-blur` + 1px `rgba(255,255,255,0.12)` border; font Inter.
- Data flows one way: pipeline → JSON → static import. No runtime fetches, no AWS in Vercel.
- KDE must match scipy semantics used before: bandwidth = 0.35 × sample std (ddof=1).
- HF Space and Streamlit files stay untouched until the Vercel production URL is verified (Task 8).
- All commits end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Scaffold `web/`, export data JSON, wire pipeline

**Files:**
- Create: `web/` (via create-next-app), `web/src/data/top_speeds.json`, `web/vitest.config.ts`
- Modify: `pipeline/assets.py` (add JSON output), `tests/test_parsing.py` untouched; extend `tests/test_definitions.py` is NOT needed — pipeline JSON write covered by py test below
- Test: `tests/test_assets_json.py` (python), `web/src/lib/__tests__/data.test.ts`

**Interfaces:**
- Produces: `web/src/data/top_speeds.json` — array of `{match: string, team: string, jersey: number, player: string, top_speed_kmh: number}`; `WEB_JSON` path constant in `pipeline/assets.py`.

- [ ] **Step 1: Scaffold the app**

```bash
cd /Users/nichollastidow/projects/fifa_top_speed
npx -y create-next-app@latest web --ts --tailwind --app --no-eslint --src-dir --import-alias "@/*" --use-npm --turbopack --yes
cd web && npm install -D vitest
```

- [ ] **Step 2: Generate the JSON snapshot from the current dataset**

```bash
cd /Users/nichollastidow/projects/fifa_top_speed
uv run python -c "
import polars as pl
df = pl.read_csv('data/top_speeds.csv').drop_nulls('top_speed_kmh')
df.write_json('web/src/data/top_speeds.json')
print(len(df), 'rows')
"
```
Expected: `2271 rows` (or current count).

- [ ] **Step 3: Wire the pipeline to keep it fresh**

In `pipeline/assets.py`, next to `LOCAL_CSV` add:

```python
WEB_JSON = Path("web/src/data/top_speeds.json")
```

and in `top_speeds`, after `df.write_csv(LOCAL_CSV)`:

```python
    WEB_JSON.parent.mkdir(parents=True, exist_ok=True)
    df.drop_nulls("top_speed_kmh").write_json(WEB_JSON)
```

- [ ] **Step 4: Python test for the JSON output**

`tests/test_assets_json.py`:

```python
import json
from pathlib import Path


def test_web_json_shape():
    rows = json.loads(Path("web/src/data/top_speeds.json").read_text())
    assert len(rows) > 2000
    r = rows[0]
    assert set(r) == {"match", "team", "jersey", "player", "top_speed_kmh"}
    assert isinstance(r["top_speed_kmh"], (int, float))
```

Run: `uv run pytest tests/test_assets_json.py -v` → PASS.

- [ ] **Step 5: Vitest config + TS data test**

`web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: { environment: "node" },
});
```

Add to `web/package.json` scripts: `"test": "vitest run"`.

`web/src/lib/__tests__/data.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import rows from "@/data/top_speeds.json";

describe("data snapshot", () => {
  it("has valid rows", () => {
    expect(rows.length).toBeGreaterThan(2000);
    for (const r of rows.slice(0, 50)) {
      expect(typeof r.player).toBe("string");
      expect(r.top_speed_kmh).toBeGreaterThan(10);
      expect(r.top_speed_kmh).toBeLessThan(45);
    }
  });
});
```

Run: `cd web && npm test` → PASS.

- [ ] **Step 6: Commit**

```bash
git add web/ pipeline/assets.py tests/test_assets_json.py
git commit -m "Scaffold Next.js app; pipeline exports web JSON snapshot"
```

---

### Task 2: Types, stats, and scale libraries (TDD)

**Files:**
- Create: `web/src/lib/types.ts`, `web/src/lib/stats.ts`, `web/src/lib/scale.ts`
- Test: `web/src/lib/__tests__/stats.test.ts`, `web/src/lib/__tests__/scale.test.ts`

**Interfaces:**
- Produces:
  - `SpeedRow { match; team; jersey; player; top_speed_kmh }`
  - `mean(xs: number[]): number`, `std(xs: number[]): number` (ddof=1), `median(xs: number[]): number`
  - `kde(sample: number[], grid: number[], bwFactor?: number): number[] | null` — null when n<2 or zero variance
  - `kpis(rows: SpeedRow[]): { fastest: SpeedRow; bestTeam: { team: string; mean: number }; meanSpeed: number; n35: number; total: number }`
  - `teamsByMean(rows: SpeedRow[]): { team: string; mean: number; speeds: number[] }[]` (descending mean)
  - `topN(rows: SpeedRow[], n: number): SpeedRow[]` (descending speed)
  - `deltas(rows: SpeedRow[], n: number): DeltaRow[]` where `DeltaRow { player; team; slow; fast; delta }`
  - `linearScale(d0,d1,r0,r1): (x:number)=>number`, `ticks(min,max,count): number[]`

- [ ] **Step 1: Write failing tests**

`web/src/lib/__tests__/stats.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { deltas, kde, kpis, mean, median, std, teamsByMean, topN } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const row = (p: string, t: string, m: string, s: number): SpeedRow => ({
  match: m, team: t, jersey: 1, player: p, top_speed_kmh: s,
});

const rows: SpeedRow[] = [
  row("A", "X", "M1", 36.0), row("A", "X", "M2", 30.0),
  row("B", "X", "M1", 34.0), row("C", "Y", "M3", 35.5),
  row("D", "Y", "M3", 20.0),
];

describe("basics", () => {
  it("mean/std/median", () => {
    expect(mean([1, 2, 3])).toBeCloseTo(2);
    expect(std([2, 4, 4, 4, 5, 5, 7, 9])).toBeCloseTo(2.138, 3); // ddof=1
    expect(median([1, 3, 2])).toBe(2);
    expect(median([1, 2, 3, 4])).toBeCloseTo(2.5);
  });
});

describe("kde", () => {
  it("is symmetric for symmetric samples and integrates to ~1", () => {
    const sample = [28, 30, 32];
    const grid = Array.from({ length: 401 }, (_, i) => 20 + i * 0.05);
    const d = kde(sample, grid)!;
    const mid = Math.round((30 - 20) / 0.05);
    expect(d[mid - 40]).toBeCloseTo(d[mid + 40], 6);
    const integral = d.reduce((a, b) => a + b, 0) * 0.05;
    expect(integral).toBeGreaterThan(0.95);
    expect(integral).toBeLessThan(1.05);
  });
  it("returns null for degenerate input", () => {
    expect(kde([30], [29, 30, 31])).toBeNull();
    expect(kde([30, 30, 30], [29, 30, 31])).toBeNull();
  });
});

describe("aggregations", () => {
  it("kpis", () => {
    const k = kpis(rows);
    expect(k.fastest.player).toBe("A");
    expect(k.n35).toBe(2); // 36.0 and 35.5
    expect(k.total).toBe(5);
    expect(k.bestTeam.team).toBe("X"); // mean 33.33 vs Y 27.75
  });
  it("teamsByMean sorts descending", () => {
    const t = teamsByMean(rows);
    expect(t[0].team).toBe("X");
    expect(t[0].speeds.length).toBe(3);
  });
  it("topN", () => {
    expect(topN(rows, 2).map((r) => r.player)).toEqual(["A", "C"]);
  });
  it("deltas requires 2+ appearances", () => {
    const d = deltas(rows, 10);
    expect(d.length).toBe(1);
    expect(d[0]).toMatchObject({ player: "A", slow: 30.0, fast: 36.0 });
    expect(d[0].delta).toBeCloseTo(6.0);
  });
});
```

`web/src/lib/__tests__/scale.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { linearScale, ticks } from "@/lib/scale";

describe("scale", () => {
  it("maps domain to range", () => {
    const s = linearScale(0, 10, 0, 100);
    expect(s(5)).toBe(50);
    expect(s(0)).toBe(0);
  });
  it("ticks produce round steps within bounds", () => {
    const t = ticks(17.3, 37.6, 6);
    expect(t[0]).toBeGreaterThanOrEqual(17.3);
    expect(t[t.length - 1]).toBeLessThanOrEqual(37.6);
    const step = t[1] - t[0];
    expect([1, 2, 2.5, 5, 10].some((k) => Math.abs(step / k % 1) < 1e-9 || Math.abs(step - k) < 1e-9)).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && npm test`
Expected: FAIL — cannot resolve `@/lib/stats`, `@/lib/scale`.

- [ ] **Step 3: Implement**

`web/src/lib/types.ts`:

```ts
export interface SpeedRow {
  match: string;
  team: string;
  jersey: number;
  player: string;
  top_speed_kmh: number;
}

export interface DeltaRow {
  player: string;
  team: string;
  slow: number;
  fast: number;
  delta: number;
}
```

`web/src/lib/stats.ts`:

```ts
import type { DeltaRow, SpeedRow } from "./types";

export const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;

export function std(xs: number[]): number {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  return Math.sqrt(xs.reduce((a, x) => a + (x - m) ** 2, 0) / (xs.length - 1));
}

export function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/** Gaussian KDE matching scipy gaussian_kde(sample, bw_method=bwFactor). */
export function kde(sample: number[], grid: number[], bwFactor = 0.35): number[] | null {
  const h = bwFactor * std(sample);
  if (sample.length < 2 || h === 0) return null;
  const norm = 1 / (sample.length * h * Math.sqrt(2 * Math.PI));
  return grid.map((x) =>
    norm * sample.reduce((a, xi) => a + Math.exp(-0.5 * ((x - xi) / h) ** 2), 0),
  );
}

export function teamsByMean(rows: SpeedRow[]) {
  const by = new Map<string, number[]>();
  for (const r of rows) {
    if (!by.has(r.team)) by.set(r.team, []);
    by.get(r.team)!.push(r.top_speed_kmh);
  }
  return [...by.entries()]
    .map(([team, speeds]) => ({ team, mean: mean(speeds), speeds }))
    .sort((a, b) => b.mean - a.mean);
}

export function topN(rows: SpeedRow[], n: number): SpeedRow[] {
  return [...rows].sort((a, b) => b.top_speed_kmh - a.top_speed_kmh).slice(0, n);
}

export function kpis(rows: SpeedRow[]) {
  const fastest = topN(rows, 1)[0];
  const teams = teamsByMean(rows);
  const n35 = rows.filter((r) => r.top_speed_kmh >= 35).length;
  return {
    fastest,
    bestTeam: { team: teams[0].team, mean: teams[0].mean },
    meanSpeed: mean(rows.map((r) => r.top_speed_kmh)),
    n35,
    total: rows.length,
  };
}

export function deltas(rows: SpeedRow[], n: number): DeltaRow[] {
  const by = new Map<string, SpeedRow[]>();
  for (const r of rows) {
    if (!by.has(r.player)) by.set(r.player, []);
    by.get(r.player)!.push(r);
  }
  const out: DeltaRow[] = [];
  for (const [player, rs] of by) {
    if (rs.length < 2) continue;
    const speeds = rs.map((r) => r.top_speed_kmh);
    const slow = Math.min(...speeds);
    const fast = Math.max(...speeds);
    out.push({ player, team: rs[0].team, slow, fast, delta: fast - slow });
  }
  return out.sort((a, b) => b.delta - a.delta).slice(0, n);
}
```

`web/src/lib/scale.ts`:

```ts
export function linearScale(d0: number, d1: number, r0: number, r1: number) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  return (x: number) => r0 + (x - d0) * k;
}

export function ticks(min: number, max: number, count: number): number[] {
  const span = max - min;
  const raw = span / Math.max(count, 1);
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * pow).find((s) => span / s <= count) ?? pow * 10;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(10)));
  return out;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npm test` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/
git commit -m "Add typed stats (KDE, aggregations) and scale helpers with tests"
```

---

### Task 3: Page shell — layout, globals, glass primitives, hero, KPI cards

**Files:**
- Create: `web/src/components/GlassCard.tsx`, `web/src/components/Hero.tsx`, `web/src/components/KpiCards.tsx`, `web/src/components/Section.tsx`
- Modify: `web/src/app/layout.tsx`, `web/src/app/globals.css`, `web/src/app/page.tsx`

**Interfaces:**
- Consumes: `kpis` from `@/lib/stats`, `SpeedRow` from `@/lib/types`.
- Produces: `<GlassCard className children>`, `<Section eyebrow title sub children>`, `<Hero matches teams total>`, `<KpiCards rows>` — used by Task 4's `Explorer`.

- [ ] **Step 1: globals.css**

Replace `web/src/app/globals.css` with:

```css
@import "tailwindcss";

:root {
  --ink: #e7ecf5;
  --dim: #8b93a7;
  --faint: #5c6478;
  --indigo: #8b9cf9;
  --rose: #fb7185;
}

body {
  color: var(--ink);
  background:
    radial-gradient(ellipse 80% 50% at 20% -10%, rgba(99, 102, 241, 0.28), transparent),
    radial-gradient(ellipse 60% 40% at 90% 10%, rgba(225, 29, 72, 0.16), transparent),
    radial-gradient(ellipse 50% 60% at 60% 110%, rgba(56, 189, 248, 0.12), transparent),
    #0b1020;
  background-attachment: fixed;
  font-family: var(--font-inter), -apple-system, sans-serif;
}

.glass {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.03));
  backdrop-filter: blur(22px) saturate(140%);
  -webkit-backdrop-filter: blur(22px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}
```

- [ ] **Step 2: layout.tsx**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "FIFA WC 2026 · Top Speeds",
  description: "Every sprint from the FIFA World Cup 2026, measured.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} antialiased`}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Primitives**

`web/src/components/GlassCard.tsx`:

```tsx
export default function GlassCard({
  className = "",
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <div className={`glass ${className}`}>{children}</div>;
}
```

`web/src/components/Section.tsx`:

```tsx
export default function Section({
  eyebrow,
  title,
  sub,
  children,
}: {
  eyebrow: string;
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-14">
      <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--indigo)]">
        {eyebrow}
      </div>
      <h2 className="mt-2 text-[23px] font-extrabold tracking-tight text-[#f2f5fb] max-sm:text-[19px]">
        {title}
      </h2>
      <p className="mt-1 mb-5 max-w-[720px] text-[12.5px] leading-relaxed text-[var(--dim)]">
        {sub}
      </p>
      {children}
    </section>
  );
}
```

`web/src/components/Hero.tsx`:

```tsx
export default function Hero({
  matches,
  teams,
  total,
}: {
  matches: number;
  teams: number;
  total: number;
}) {
  return (
    <header>
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--indigo)]">
        FIFA World Cup 2026
      </div>
      <h1
        className="mt-3 text-5xl font-black tracking-tight text-[#f2f5fb] max-sm:text-[32px]"
        style={{ textShadow: "0 0 40px rgba(139,156,249,0.35)" }}
      >
        Top Speed Report
      </h1>
      <p className="mt-4 max-w-[640px] text-sm leading-relaxed text-[var(--dim)]">
        Every sprint measured by FIFA&apos;s physical performance system. {matches} matches ·{" "}
        {teams} teams · {total.toLocaleString()} player appearances — refreshed as new match
        reports publish.
      </p>
    </header>
  );
}
```

`web/src/components/KpiCards.tsx`:

```tsx
import GlassCard from "./GlassCard";
import { kpis } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

export default function KpiCards({ rows }: { rows: SpeedRow[] }) {
  const k = kpis(rows);
  const cards = [
    {
      label: "Fastest recorded",
      value: `${k.fastest.top_speed_kmh.toFixed(1)} km/h`,
      sub: `${k.fastest.player} · ${k.fastest.team}`,
      accent: true,
    },
    { label: "Fastest team avg", value: k.bestTeam.team, sub: `${k.bestTeam.mean.toFixed(1)} km/h mean`, accent: false },
    { label: "Tournament mean", value: `${k.meanSpeed.toFixed(1)} km/h`, sub: `across ${k.total.toLocaleString()} appearances`, accent: false },
    { label: "Players ≥ 35 km/h", value: String(k.n35), sub: `${((k.n35 / k.total) * 100).toFixed(1)}% of all appearances`, accent: false },
  ];
  return (
    <div className="mt-9 grid grid-cols-4 gap-4 max-sm:grid-cols-1 max-lg:grid-cols-2">
      {cards.map((c) => (
        <GlassCard key={c.label} className="px-5 py-4">
          <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--dim)]">
            {c.label}
          </div>
          <div
            className={`mt-2 text-[28px] font-extrabold tracking-tight max-sm:text-[23px] ${
              c.accent ? "text-[#a5b4fc]" : "text-[#f2f5fb]"
            }`}
            style={c.accent ? { textShadow: "0 0 24px rgba(139,156,249,0.5)" } : undefined}
          >
            {c.value}
          </div>
          <div className="mt-2 text-[11.5px] leading-snug text-[var(--dim)]">{c.sub}</div>
        </GlassCard>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Temporary page to verify shell**

`web/src/app/page.tsx`:

```tsx
import rows from "@/data/top_speeds.json";
import Hero from "@/components/Hero";
import KpiCards from "@/components/KpiCards";
import type { SpeedRow } from "@/lib/types";

export default function Page() {
  const data = rows as SpeedRow[];
  const matches = new Set(data.map((r) => r.match)).size;
  const teams = new Set(data.map((r) => r.team)).size;
  return (
    <main className="mx-auto max-w-[1180px] px-10 pb-20 pt-14 max-sm:px-4 max-sm:pt-8">
      <Hero matches={matches} teams={teams} total={data.length} />
      <KpiCards rows={data} />
    </main>
  );
}
```

- [ ] **Step 5: Verify**

Run: `cd web && npm run build`
Expected: build succeeds, `/` statically generated.

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "Page shell: liquid-glass globals, hero, KPI cards"
```

---

### Task 4: FilterBar + Explorer client state

**Files:**
- Create: `web/src/components/MultiSelect.tsx`, `web/src/components/FilterBar.tsx`, `web/src/components/Explorer.tsx`
- Modify: `web/src/app/page.tsx`

**Interfaces:**
- Consumes: `SpeedRow`, primitives from Task 3.
- Produces: `Explorer` (client component, owns state `{teams: string[], matches: string[], topN: number, deltaN: number, ridgeN: number}` and `filtered: SpeedRow[]`); renders chart placeholders replaced in Tasks 5–7. `FilterBar` props: `{allTeams, allMatches, state, onChange}` where `state = {teams, matches, topN, deltaN, ridgeN}`.

- [ ] **Step 1: MultiSelect**

`web/src/components/MultiSelect.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

export default function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const toggle = (o: string) =>
    onChange(selected.includes(o) ? selected.filter((s) => s !== o) : [...selected, o]);
  const shown = options.filter((o) => o.toLowerCase().includes(q.toLowerCase()));

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="glass w-full px-4 py-2.5 text-left text-[13px] text-[var(--ink)]"
      >
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--dim)]">
          {label}
        </span>
        <div className="mt-0.5 truncate">
          {selected.length ? selected.join(", ") : `All ${options.length}`}
        </div>
      </button>
      {open && (
        <div className="glass absolute z-20 mt-2 max-h-72 w-full overflow-auto p-2">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search…"
            className="mb-2 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[13px] outline-none placeholder:text-[var(--faint)]"
          />
          {selected.length > 0 && (
            <button
              onClick={() => onChange([])}
              className="mb-1 w-full rounded-lg px-3 py-1.5 text-left text-[12px] text-[var(--rose)] hover:bg-white/5"
            >
              Clear selection
            </button>
          )}
          {shown.map((o) => (
            <button
              key={o}
              onClick={() => toggle(o)}
              className={`block w-full rounded-lg px-3 py-1.5 text-left text-[13px] hover:bg-white/5 ${
                selected.includes(o) ? "text-[var(--indigo)]" : "text-[var(--ink)]"
              }`}
            >
              {selected.includes(o) ? "✓ " : ""}
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: FilterBar**

`web/src/components/FilterBar.tsx`:

```tsx
"use client";

import MultiSelect from "./MultiSelect";

export interface FilterState {
  teams: string[];
  matches: string[];
  topN: number;
  deltaN: number;
  ridgeN: number;
}

function SliderField({
  label, value, min, max, step, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="glass flex items-center gap-3 px-4 py-2.5 text-[12px] text-[var(--dim)]">
      <span className="whitespace-nowrap">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#8b9cf9]"
      />
      <span className="w-6 text-right font-bold text-[var(--ink)]">{value}</span>
    </label>
  );
}

export default function FilterBar({
  allTeams,
  allMatches,
  state,
  onChange,
}: {
  allTeams: string[];
  allMatches: string[];
  state: FilterState;
  onChange: (next: FilterState) => void;
}) {
  return (
    <div className="mt-10 grid grid-cols-2 gap-3 max-sm:grid-cols-1 lg:grid-cols-5">
      <MultiSelect label="Teams" options={allTeams} selected={state.teams}
        onChange={(teams) => onChange({ ...state, teams })} />
      <MultiSelect label="Matches" options={allMatches} selected={state.matches}
        onChange={(matches) => onChange({ ...state, matches })} />
      <SliderField label="Top N" value={state.topN} min={10} max={40} step={5}
        onChange={(topN) => onChange({ ...state, topN })} />
      <SliderField label="Delta N" value={state.deltaN} min={10} max={30} step={5}
        onChange={(deltaN) => onChange({ ...state, deltaN })} />
      <SliderField label="Teams shown" value={state.ridgeN} min={10} max={48} step={2}
        onChange={(ridgeN) => onChange({ ...state, ridgeN })} />
    </div>
  );
}
```

- [ ] **Step 3: Explorer**

`web/src/components/Explorer.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import FilterBar, { FilterState } from "./FilterBar";
import KpiCards from "./KpiCards";
import type { SpeedRow } from "@/lib/types";

export default function Explorer({ rows }: { rows: SpeedRow[] }) {
  const allTeams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const allMatches = useMemo(() => [...new Set(rows.map((r) => r.match))].sort(), [rows]);
  const [state, setState] = useState<FilterState>({
    teams: [], matches: [], topN: 25, deltaN: 20, ridgeN: 30,
  });

  const filtered = useMemo(
    () =>
      rows.filter(
        (r) =>
          (!state.teams.length || state.teams.includes(r.team)) &&
          (!state.matches.length || state.matches.includes(r.match)),
      ),
    [rows, state.teams, state.matches],
  );

  if (!filtered.length) {
    return (
      <>
        <FilterBar allTeams={allTeams} allMatches={allMatches} state={state} onChange={setState} />
        <div className="glass mt-10 px-6 py-8 text-center text-sm text-[var(--dim)]">
          No data matches the current filters.
        </div>
      </>
    );
  }

  return (
    <>
      <FilterBar allTeams={allTeams} allMatches={allMatches} state={state} onChange={setState} />
      <KpiCards rows={filtered} />
      {/* charts appended in Tasks 5–7 */}
    </>
  );
}
```

Update `web/src/app/page.tsx` to render `Explorer`:

```tsx
import rows from "@/data/top_speeds.json";
import Explorer from "@/components/Explorer";
import Hero from "@/components/Hero";
import type { SpeedRow } from "@/lib/types";

export default function Page() {
  const data = rows as SpeedRow[];
  const matches = new Set(data.map((r) => r.match)).size;
  const teams = new Set(data.map((r) => r.team)).size;
  return (
    <main className="mx-auto max-w-[1180px] px-10 pb-20 pt-14 max-sm:px-4 max-sm:pt-8">
      <Hero matches={matches} teams={teams} total={data.length} />
      <Explorer rows={data} />
      <footer className="mt-16 text-center text-[11px] tracking-wide text-[var(--faint)]">
        FIFA World Cup 2026 · Top Speed Report · Data scraped from fifatrainingcentre.com
      </footer>
    </main>
  );
}
```

- [ ] **Step 4: Verify build + commit**

Run: `cd web && npm run build` → succeeds.

```bash
git add web/src/
git commit -m "Client-side filters: multiselects, sliders, Explorer state"
```

---

### Task 5: Leaderboard chart (+ shared chart infrastructure)

**Files:**
- Create: `web/src/components/useMeasure.ts`, `web/src/components/Tooltip.tsx`, `web/src/components/charts/Leaderboard.tsx`
- Modify: `web/src/components/Explorer.tsx` (add section)

**Interfaces:**
- Consumes: `topN`, `linearScale`, `ticks`, `Section`, `FilterState.topN`.
- Produces:
  - `useMeasure(): [ref, width]` — ResizeObserver hook.
  - `TooltipState { x: number; y: number; lines: string[] } | null`; `<Tooltip tip={TooltipState} />` renders inside a `relative` container.
  - `<Leaderboard rows={SpeedRow[]} n={number} />`.

- [ ] **Step 1: useMeasure**

`web/src/components/useMeasure.ts`:

```ts
"use client";

import { useEffect, useRef, useState } from "react";

export default function useMeasure<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((es) => setWidth(es[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}
```

- [ ] **Step 2: Tooltip**

`web/src/components/Tooltip.tsx`:

```tsx
"use client";

export interface TooltipState {
  x: number;
  y: number;
  lines: string[];
}

export default function Tooltip({ tip }: { tip: TooltipState | null }) {
  if (!tip) return null;
  return (
    <div
      className="pointer-events-none absolute z-30 rounded-xl border border-white/15 bg-[#141a2ef2] px-3 py-2 text-[12px] leading-relaxed shadow-xl"
      style={{ left: tip.x + 12, top: tip.y + 12 }}
    >
      {tip.lines.map((l, i) => (
        <div key={i} className={i === 0 ? "font-bold text-[var(--ink)]" : "text-[var(--dim)]"}>
          {l}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Leaderboard**

`web/src/components/charts/Leaderboard.tsx`:

```tsx
"use client";

import { useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { topN } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const MEDALS = ["🥇", "🥈", "🥉"];
const ROW_H = 44;

export default function Leaderboard({ rows, n }: { rows: SpeedRow[]; n: number }) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const top = topN(rows, n);
  if (!top.length) return null;

  const speeds = top.map((r) => r.top_speed_kmh);
  const xmin = Math.min(...speeds) - 2;
  const xmax = Math.max(...speeds) + 1;
  const height = top.length * ROW_H + 40;
  const x = linearScale(xmin, xmax, 8, Math.max(width, 320) - 48);

  return (
    <div ref={ref} className="relative">
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={height - 30} stroke="rgba(255,255,255,0.09)" />
            <text x={x(t)} y={height - 12} textAnchor="middle" fontSize={10.5} fill="var(--dim)">
              {t} km/h
            </text>
          </g>
        ))}
        {top.map((r, i) => {
          const cy = i * ROW_H + 30;
          const col = i < 3 ? "var(--rose)" : "var(--indigo)";
          return (
            <g
              key={`${r.player}-${r.match}`}
              onMouseMove={(e) => {
                const b = (e.currentTarget.ownerSVGElement!.parentElement as HTMLElement).getBoundingClientRect();
                setTip({
                  x: e.clientX - b.left, y: e.clientY - b.top,
                  lines: [r.player, `${r.team} · ${r.match}`, `${r.top_speed_kmh.toFixed(1)} km/h`],
                });
              }}
              onMouseLeave={() => setTip(null)}
            >
              <text x={x(xmin)} y={cy - 8} fontSize={11.5} fill="var(--ink)" fontWeight={600}>
                {MEDALS[i] ?? `${i + 1}.`} {r.player}
                <tspan fill="var(--dim)" fontWeight={400}>  {r.team}</tspan>
              </text>
              <line x1={x(xmin)} x2={x(r.top_speed_kmh)} y1={cy} y2={cy}
                stroke="rgba(255,255,255,0.09)" strokeWidth={1.5} />
              <circle cx={x(r.top_speed_kmh)} cy={cy} r={5.5} fill={col}
                stroke="#141a2e" strokeWidth={1.5} />
              <text x={x(r.top_speed_kmh) + 10} y={cy + 3.5} fontSize={10} fill={col} fontWeight={700}>
                {r.top_speed_kmh.toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
```

- [ ] **Step 4: Wire into Explorer**

In `Explorer.tsx`, import `Section` and `Leaderboard`, and after `<KpiCards …/>` add:

```tsx
      <Section
        eyebrow="Leaderboard"
        title={`Top ${state.topN} fastest player appearances`}
        sub="One dot per player-match · top three highlighted · hover for full context"
      >
        <Leaderboard rows={filtered} n={state.topN} />
      </Section>
```

- [ ] **Step 5: Verify + commit**

Run: `cd web && npm run build && npm test` → both pass.

```bash
git add web/src/
git commit -m "Leaderboard dot plot with shared tooltip and measure hook"
```

---

### Task 6: Ridgeline chart

**Files:**
- Create: `web/src/components/charts/Ridgeline.tsx`
- Modify: `web/src/components/Explorer.tsx`

**Interfaces:**
- Consumes: `kde`, `teamsByMean`, `median`, `mean`, `linearScale`, `ticks`, `useMeasure`, `Tooltip`.
- Produces: `<Ridgeline rows={SpeedRow[]} teamsShown={number} />`.

- [ ] **Step 1: Implement**

`web/src/components/charts/Ridgeline.tsx`:

```tsx
"use client";

import { useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { kde, mean, median, teamsByMean } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const STEP = 26;
const AMP = STEP * 1.45;

function mix(t: number) {
  // indigo #8b9cf9 -> slate #3d4457
  const c = (a: number, b: number) => Math.round(a + t * (b - a));
  return `rgb(${c(139, 61)},${c(156, 68)},${c(249, 87)})`;
}

export default function Ridgeline({ rows, teamsShown }: { rows: SpeedRow[]; teamsShown: number }) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const teams = teamsByMean(rows).slice(0, teamsShown);
  if (!teams.length) return null;

  const all = rows.map((r) => r.top_speed_kmh);
  const xmin = Math.min(...all) - 1.5;
  const xmax = Math.max(...all) + 1.5;
  const tMedian = median(all);
  const n = teams.length;
  const height = n * STEP + Math.round(AMP) + 70;
  const x = linearScale(xmin, xmax, 110, Math.max(width, 360) - 20);
  const grid = Array.from({ length: 240 }, (_, i) => xmin + ((xmax - xmin) * i) / 239);

  return (
    <div ref={ref} className="relative">
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <text key={t} x={x(t)} y={height - 12} textAnchor="middle" fontSize={10.5} fill="var(--dim)">
            {t} km/h
          </text>
        ))}
        <line x1={x(tMedian)} x2={x(tMedian)} y1={8} y2={height - 30}
          stroke="var(--faint)" strokeDasharray="4 4" />
        <text x={x(tMedian) + 4} y={14} fontSize={9.5} fill="var(--faint)">
          median {tMedian.toFixed(1)}
        </text>
        {[...teams].reverse().map((t, revIdx) => {
          const rank = n - 1 - revIdx; // 0 = fastest
          const base = rank * STEP + Math.round(AMP) + 6;
          const dens = kde(t.speeds, grid);
          const color = mix(rank / Math.max(n - 1, 1));
          const label = (
            <text key={`l-${t.team}`} x={100} y={base + 3} textAnchor="end" fontSize={10} fill="var(--ink)">
              {t.team}
            </text>
          );
          if (!dens) return label;
          const peak = Math.max(...dens);
          const ys = dens.map((d) => (d / peak) * AMP);
          const path =
            `M ${x(grid[0])} ${base}` +
            ys.map((y, i) => ` L ${x(grid[i])} ${base - y}`).join("") +
            ` L ${x(grid[grid.length - 1])} ${base} Z`;
          const m = mean(t.speeds);
          const mIdx = Math.min(
            grid.length - 1,
            Math.max(0, Math.round(((m - xmin) / (xmax - xmin)) * (grid.length - 1))),
          );
          return (
            <g key={t.team}>
              {label}
              <path d={path} fill={color} fillOpacity={0.16} stroke={color} strokeWidth={1.3} />
              <line x1={x(m)} x2={x(m)} y1={base} y2={base - ys[mIdx]} stroke="var(--rose)" strokeWidth={1.4} />
              <circle
                cx={x(m)} cy={base - ys[mIdx]} r={4} fill="var(--rose)"
                onMouseMove={(e) => {
                  const b = (e.currentTarget.ownerSVGElement!.parentElement as HTMLElement).getBoundingClientRect();
                  setTip({
                    x: e.clientX - b.left, y: e.clientY - b.top,
                    lines: [
                      t.team,
                      `Mean ${m.toFixed(1)} km/h`,
                      `Range ${Math.min(...t.speeds).toFixed(1)}–${Math.max(...t.speeds).toFixed(1)}`,
                      `n=${t.speeds.length}`,
                    ],
                  });
                }}
                onMouseLeave={() => setTip(null)}
              />
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
```

- [ ] **Step 2: Wire into Explorer**

After the Leaderboard section in `Explorer.tsx`:

```tsx
      <Section
        eyebrow="Distribution"
        title="How speed distributes within each team"
        sub="Fastest teams at the top, fading to slowest · rose tick marks the team mean · dashed line is the tournament median"
      >
        <Ridgeline rows={filtered} teamsShown={state.ridgeN} />
      </Section>
```

- [ ] **Step 3: Verify + commit**

Run: `cd web && npm run build && npm test` → pass.

```bash
git add web/src/
git commit -m "Ridgeline chart: per-team KDE with mean ticks and median guide"
```

---

### Task 7: Dumbbell chart (click-to-hide)

**Files:**
- Create: `web/src/components/charts/Dumbbell.tsx`
- Modify: `web/src/components/Explorer.tsx`

**Interfaces:**
- Consumes: `deltas`, `linearScale`, `ticks`, `useMeasure`, `Tooltip`, `Section`.
- Produces: `<Dumbbell rows={SpeedRow[]} n={number} />` — internal hidden-set state, resets when `rows` or `n` changes.

- [ ] **Step 1: Implement**

`web/src/components/charts/Dumbbell.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { deltas } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const ROW_H = 44;

export default function Dumbbell({ rows, n }: { rows: SpeedRow[]; n: number }) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  useEffect(() => setHidden(new Set()), [rows, n]);

  const items = deltas(rows, n);
  if (!items.length) {
    return (
      <div className="glass px-6 py-6 text-sm text-[var(--dim)]">
        Not enough players with multiple appearances in this filter.
      </div>
    );
  }

  const xmin = Math.min(...items.map((d) => d.slow)) - 1.5;
  const xmax = Math.max(...items.map((d) => d.fast)) + 1.5;
  const height = items.length * ROW_H + 40;
  const x = linearScale(xmin, xmax, 8, Math.max(width, 320) - 48);

  return (
    <div ref={ref} className="relative">
      {hidden.size > 0 && (
        <button
          onClick={() => setHidden(new Set())}
          className="glass absolute right-0 -top-12 px-4 py-1.5 text-[12px] text-[var(--ink)]"
        >
          ↺ Show all
        </button>
      )}
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={height - 30} stroke="rgba(255,255,255,0.09)" />
            <text x={x(t)} y={height - 12} textAnchor="middle" fontSize={10.5} fill="var(--dim)">
              {t} km/h
            </text>
          </g>
        ))}
        {items.map((d, i) => {
          const cy = i * ROW_H + 30;
          const off = hidden.has(d.player);
          return (
            <g
              key={d.player}
              className="cursor-pointer"
              onClick={() =>
                setHidden((h) => {
                  const nh = new Set(h);
                  if (nh.has(d.player)) nh.delete(d.player); else nh.add(d.player);
                  return nh;
                })
              }
              onMouseMove={(e) => {
                if (off) return;
                const b = (e.currentTarget.ownerSVGElement!.parentElement as HTMLElement).getBoundingClientRect();
                setTip({
                  x: e.clientX - b.left, y: e.clientY - b.top,
                  lines: [
                    `${d.player} · ${d.team}`,
                    `Slower ${d.slow.toFixed(1)} · Faster ${d.fast.toFixed(1)}`,
                    `Δ ${d.delta.toFixed(1)} km/h`,
                  ],
                });
              }}
              onMouseLeave={() => setTip(null)}
            >
              <text x={x(xmin)} y={cy - 8} fontSize={11.5}
                fill={off ? "var(--faint)" : "var(--ink)"} fontWeight={600}>
                {d.player}
                <tspan fill={off ? "var(--faint)" : "var(--dim)"} fontWeight={400}>
                  {"  "}{d.team} · Δ{d.delta.toFixed(1)}
                </tspan>
              </text>
              <line x1={x(d.slow)} x2={x(d.fast)} y1={cy} y2={cy}
                stroke={off ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.14)"} strokeWidth={2.5} />
              {!off && (
                <>
                  <circle cx={x(d.slow)} cy={cy} r={5} fill="#141a2e"
                    stroke="var(--indigo)" strokeWidth={1.8} />
                  <circle cx={x(d.fast)} cy={cy} r={5} fill="var(--indigo)" />
                  <text x={x(d.slow) - 9} y={cy + 3} textAnchor="end" fontSize={9} fill="var(--dim)">
                    {d.slow.toFixed(1)}
                  </text>
                  <text x={x(d.fast) + 9} y={cy + 3} fontSize={9} fill="var(--indigo)" fontWeight={700}>
                    {d.fast.toFixed(1)}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
```

- [ ] **Step 2: Wire into Explorer**

After the Ridgeline section:

```tsx
      <Section
        eyebrow="Speed delta"
        title="Who performed most differently between matches?"
        sub="Players with 2+ appearances, sorted by swing size · hollow dot = slower match · filled dot = faster match · click any row to hide it"
      >
        <Dumbbell rows={filtered} n={state.deltaN} />
      </Section>
```

- [ ] **Step 3: Verify + commit**

Run: `cd web && npm run build && npm test` → pass.

```bash
git add web/src/
git commit -m "Dumbbell delta chart with click-to-hide"
```

---

### Task 8: Browser verification + fixes

**Files:**
- Modify: any component with issues found

- [ ] **Step 1: Run dev server and inspect**

Run: `cd web && npm run dev` (port 3000). Screenshot desktop (1440px) and mobile (390px): hero, KPI glass cards, all three charts, filters open/closed, tooltip hover, dumbbell click-to-hide + reset, empty-filter state (pick disjoint team+match). Fix contrast/overlap issues found; iterate until clean.

- [ ] **Step 2: Commit any fixes**

```bash
git add web/src/
git commit -m "Visual polish from browser verification"
```

---

### Task 9: GitHub migration

**Files:** none (git operations)

**Prerequisite:** user has run `gh auth login`.

- [ ] **Step 1: Create repo and push**

```bash
gh repo create fifa-top-speed --public --source . --remote origin --push
```
Expected: repo created, `main` pushed, `origin` remote added (HF `space` remote untouched).

- [ ] **Step 2: Verify**

Run: `gh repo view --web=false | head -5` → shows repo. `git remote -v` shows both `origin` (GitHub) and `space` (HF).

---

### Task 10: Vercel deploy

**Files:**
- Create: none (Vercel project config lives on Vercel)

**Prerequisite:** Vercel auth (CLI `vercel login` or the Vercel plugin's authenticate flow).

- [ ] **Step 1: Link and deploy**

```bash
cd web
npx -y vercel link --yes            # creates .vercel/ (gitignored by CLI)
npx -y vercel --prod --yes
```
Expected: production URL printed.

Prefer connecting the GitHub repo to the Vercel project (dashboard or `npx vercel git connect`) so pushes auto-deploy; root directory = `web/`.

- [ ] **Step 2: Verify production**

`curl -s -o /dev/null -w "%{http_code}" <prod-url>` → 200; browser screenshot of prod URL shows the app with current data.

---

### Task 11: Retire Streamlit

**Only after Task 10 verification.**

**Files:**
- Delete: `app.py`, `Dockerfile`, `requirements.txt`
- Modify: `README.md` (drop HF frontmatter + Streamlit references; point to Vercel URL and `web/`)

- [ ] **Step 1: Remove Streamlit app**

```bash
git rm app.py Dockerfile requirements.txt
```
Update README: remove the `---title:…---` HF frontmatter block, replace "Live app: interactive Streamlit explorer" with the Vercel production URL, replace the `app.py` row in the Files table with `web/` (Next.js explorer).

- [ ] **Step 2: Test + commit + push**

```bash
uv run pytest tests/ && git add -A && git commit -m "Retire Streamlit frontend; Vercel is the live app" && git push origin main
```

- [ ] **Step 3: HF Space deletion**

Ask the user for explicit confirmation before deleting the Space (destructive, external). If confirmed, they can delete at huggingface.co/spaces/ntcode12/fifa-top-speed/settings; do not push further to `space`.

---

## Self-review notes

- Spec coverage: JSON export + pipeline wiring (T1), stats/scale libs (T2), shell + glass + hero + KPIs (T3), filters (T4), three charts (T5–7), error states (empty filter T4, KDE null T2/T6, empty deltas T7), testing (T1/T2 vitest + pytest, T8 browser), GitHub (T9), Vercel (T10), Streamlit retirement + Space confirmation (T11). ✔
- No placeholders; all components fully coded. ✔
- Types consistent: `SpeedRow`/`DeltaRow`/`FilterState`/`TooltipState` defined before use; `kde` null contract honored in Ridgeline. ✔
