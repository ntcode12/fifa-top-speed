"use client";

import { useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { topN } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const MEDALS = ["🥇", "🥈", "🥉"];
const ROW_H = 44;

export default function Leaderboard({ rows, n }: { rows: SpeedRow[]; n: number }) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const top = topN(rows, n);
  if (!top.length) return null;

  const speeds = top.map((r) => r.top_speed_kmh);
  const xmin = Math.min(...speeds) - 2;
  const xmax = Math.max(...speeds) + 1;
  const height = top.length * ROW_H + 40;
  const x = linearScale(xmin, xmax, 8, Math.max(width, 320) - 48);

  return (
    <div ref={ref} className="relative">
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={height - 30} stroke="rgba(255,255,255,0.09)" />
            <text x={x(t)} y={height - 12} textAnchor="middle" fontSize={10.5} fill="var(--dim)">
              {t} km/h
            </text>
          </g>
        ))}
        {top.map((r, i) => {
          const cy = i * ROW_H + 30;
          const col = i < 3 ? "var(--rose)" : "var(--indigo)";
          return (
            <g
              key={`${r.player}-${r.match}`}
              onMouseMove={(e) => {
                const b = (
                  e.currentTarget.ownerSVGElement!.parentElement as HTMLElement
                ).getBoundingClientRect();
                setTip({
                  x: e.clientX - b.left,
                  y: e.clientY - b.top,
                  lines: [r.player, `${r.team} · ${r.match}`, `${r.top_speed_kmh.toFixed(1)} km/h`],
                });
              }}
              onMouseLeave={() => setTip(null)}
            >
              <text x={x(xmin)} y={cy - 8} fontSize={11.5} fill="var(--ink)" fontWeight={600}>
                {MEDALS[i] ?? `${i + 1}.`} {r.player}
                <tspan fill="var(--dim)" fontWeight={400}>
                  {"  "}
                  {r.team}
                </tspan>
              </text>
              <line
                x1={x(xmin)}
                x2={x(r.top_speed_kmh)}
                y1={cy}
                y2={cy}
                stroke="rgba(255,255,255,0.09)"
                strokeWidth={1.5}
              />
              <circle
                cx={x(r.top_speed_kmh)}
                cy={cy}
                r={5.5}
                fill={col}
                stroke="#141a2e"
                strokeWidth={1.5}
              />
              <text
                x={x(r.top_speed_kmh) + 10}
                y={cy + 3.5}
                fontSize={10}
                fill={col}
                fontWeight={700}
              >
                {r.top_speed_kmh.toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
