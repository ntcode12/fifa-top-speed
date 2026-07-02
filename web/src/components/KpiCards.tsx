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
    {
      label: "Fastest team avg",
      value: k.bestTeam.team,
      sub: `${k.bestTeam.mean.toFixed(1)} km/h mean`,
      accent: false,
    },
    {
      label: "Tournament mean",
      value: `${k.meanSpeed.toFixed(1)} km/h`,
      sub: `across ${k.total.toLocaleString()} appearances`,
      accent: false,
    },
    {
      label: "Players ≥ 35 km/h",
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
            {c.value}
          </div>
          <div className="mt-2 text-[11.5px] leading-snug text-[var(--dim)]">{c.sub}</div>
        </GlassCard>
      ))}
    </div>
  );
}
