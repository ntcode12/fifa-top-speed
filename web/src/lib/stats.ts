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

export function kpis(rows: SpeedRow[], threshold = 35) {
  const fastest = topN(rows, 1)[0];
  const teams = teamsByMean(rows);
  const n35 = rows.filter((r) => r.top_speed_kmh >= threshold).length;
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
