"use client";

import { useMemo, useState } from "react";
import FilterBar, { FilterState } from "./FilterBar";
import KpiCards from "./KpiCards";
import Section from "./Section";
import Leaderboard from "./charts/Leaderboard";
import Ridgeline from "./charts/Ridgeline";
import Dumbbell from "./charts/Dumbbell";
import { MPH_PER_KMH, Unit, unitLabel } from "@/lib/units";
import type { SpeedRow } from "@/lib/types";

function UnitToggle({ unit, onChange }: { unit: Unit; onChange: (u: Unit) => void }) {
  return (
    <div className="glass flex rounded-full p-1 text-[12px]">
      {(["kmh", "mph"] as const).map((u) => (
        <button
          key={u}
          onClick={() => onChange(u)}
          className={`rounded-full px-4 py-1.5 font-semibold transition ${
            unit === u
              ? "bg-[#8b9cf9]/25 text-[var(--ink)]"
              : "text-[var(--dim)] hover:text-[var(--ink)]"
          }`}
        >
          {unitLabel(u)}
        </button>
      ))}
    </div>
  );
}

export default function Explorer({ rows }: { rows: SpeedRow[] }) {
  const allTeams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const allMatches = useMemo(() => [...new Set(rows.map((r) => r.match))].sort(), [rows]);
  const [unit, setUnit] = useState<Unit>("kmh");
  const [state, setState] = useState<FilterState>({
    teams: [],
    matches: [],
    topN: 25,
    deltaN: 20,
    ridgeN: 30,
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

  const display = useMemo(
    () =>
      unit === "kmh"
        ? filtered
        : filtered.map((r) => ({ ...r, top_speed_kmh: r.top_speed_kmh * MPH_PER_KMH })),
    [filtered, unit],
  );

  const label = unitLabel(unit);
  const controls = (
    <>
      <div className="mt-10 flex justify-end">
        <UnitToggle unit={unit} onChange={setUnit} />
      </div>
      <FilterBar allTeams={allTeams} allMatches={allMatches} state={state} onChange={setState} />
    </>
  );

  if (!display.length) {
    return (
      <>
        {controls}
        <div className="glass mt-10 px-6 py-8 text-center text-sm text-[var(--dim)]">
          No data matches the current filters.
        </div>
      </>
    );
  }

  return (
    <>
      {controls}
      <KpiCards rows={display} unit={unit} />
      <Section
        eyebrow="Leaderboard"
        title={`Top ${state.topN} fastest player appearances`}
        sub="One dot per player-match · top three highlighted · hover for full context"
      >
        <Leaderboard rows={display} n={state.topN} unit={label} />
      </Section>
      <Section
        eyebrow="Distribution"
        title="How speed distributes within each team"
        sub="Fastest teams at the top, fading to slowest · rose tick marks the team mean · dashed line is the tournament median"
      >
        <Ridgeline rows={display} teamsShown={state.ridgeN} unit={label} />
      </Section>
      <Section
        eyebrow="Speed delta"
        title="Who performed most differently between matches?"
        sub="Players with 2+ appearances, sorted by swing size · hollow dot = slower match · filled dot = faster match · click any row to hide it"
      >
        <Dumbbell rows={display} n={state.deltaN} unit={label} />
      </Section>
    </>
  );
}
