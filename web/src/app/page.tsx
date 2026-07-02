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
