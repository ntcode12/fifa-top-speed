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
