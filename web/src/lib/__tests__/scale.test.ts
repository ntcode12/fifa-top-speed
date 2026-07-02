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
    expect(t.length).toBeGreaterThan(2);
    expect(t.length).toBeLessThanOrEqual(7);
  });
});
