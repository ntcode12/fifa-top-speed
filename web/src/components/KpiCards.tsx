import GlassCard from "./GlassCard";
import { flagUrl } from "@/lib/flags";
import { kpis } from "@/lib/stats";
import { Unit, eliteThreshold, unitLabel } from "@/lib/units";
import type { SpeedRow } from "@/lib/types";

export default function KpiCards({ rows, unit = "kmh" }: { rows: SpeedRow[]; unit?: Unit }) {
  const label = unitLabel(unit);
  const threshold = eliteThreshold(unit);
  const k = kpis(rows, threshold);
  const cards = [
    {
      label: "Fastest recorded",
      value: `${k.fastest.top_speed_kmh.toFixed(1)} ${label}`,
      sub: `${k.fastest.player} · ${k.fastest.team}`,
      accent: true,
    },
    {
      label: "Fastest team avg",
      value: k.bestTeam.team,
      flag: flagUrl(k.bestTeam.team),
      sub: `${k.bestTeam.mean.toFixed(1)} ${label} mean`,
      accent: false,
    },
    {
      label: "Tournament mean",
      value: `${k.meanSpeed.toFixed(1)} ${label}`,
      sub: `across ${k.total.toLocaleString()} appearances`,
      accent: false,
    },
    {
      label: `Players ≥ ${unit === "kmh" ? "35" : threshold.toFixed(1)} ${label}`,
      value: String(k.n35),
      sub: `${((k.n35 / k.total) * 100).toFixed(1)}% of all appearances`,
      accent: false,
    },
  ];
  return (
    <div className="mt-9 grid grid-cols-4 gap-4 max-lg:grid-cols-2 max-sm:grid-cols-1">
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
            {"flag" in c && c.flag && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={c.flag}
                alt=""
                className="mr-2 inline h-[18px] w-6 rounded-[3px] object-cover align-[-2px]"
              />
            )}
            {c.value}
          </div>
          <div className="mt-2 text-[11.5px] leading-snug text-[var(--dim)]">{c.sub}</div>
        </GlassCard>
      ))}
    </div>
  );
}
