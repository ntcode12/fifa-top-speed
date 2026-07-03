"use client";

export interface TooltipState {
  x: number;
  y: number;
  lines: string[];
}

export default function Tooltip({ tip }: { tip: TooltipState | null }) {
  if (!tip) return null;
  return (
    <div
      className="pointer-events-none absolute z-30 rounded-xl border border-white/15 bg-[#141a2ef2] px-3 py-2 text-[12px] leading-relaxed shadow-xl"
      style={{ left: tip.x + 12, top: tip.y + 12 }}
    >
      {tip.lines.map((l, i) => (
        <div key={i} className={i === 0 ? "font-bold text-[var(--ink)]" : "text-[var(--dim)]"}>
          {l}
        </div>
      ))}
    </div>
  );
}
