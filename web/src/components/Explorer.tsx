"use client";

import { useMemo, useState } from "react";
import FilterBar, { FilterState } from "./FilterBar";
import KpiCards from "./KpiCards";
import Section from "./Section";
import Leaderboard from "./charts/Leaderboard";
import Ridgeline from "./charts/Ridgeline";
import type { SpeedRow } from "@/lib/types";

export default function Explorer({ rows }: { rows: SpeedRow[] }) {
  const allTeams = useMemo(() => [...new Set(rows.map((r) => r.team))].sort(), [rows]);
  const allMatches = useMemo(() => [...new Set(rows.map((r) => r.match))].sort(), [rows]);
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
      <Section
        eyebrow="Leaderboard"
        title={`Top ${state.topN} fastest player appearances`}
        sub="One dot per player-match · top three highlighted · hover for full context"
      >
        <Leaderboard rows={filtered} n={state.topN} />
      </Section>
      <Section
        eyebrow="Distribution"
        title="How speed distributes within each team"
        sub="Fastest teams at the top, fading to slowest · rose tick marks the team mean · dashed line is the tournament median"
      >
        <Ridgeline rows={filtered} teamsShown={state.ridgeN} />
      </Section>
    </>
  );
}
