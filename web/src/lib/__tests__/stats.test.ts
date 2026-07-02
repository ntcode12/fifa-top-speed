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
