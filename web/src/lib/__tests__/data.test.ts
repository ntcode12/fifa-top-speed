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
