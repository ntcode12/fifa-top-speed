"use client";

import { useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { kde, mean, median, teamsByMean } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const STEP = 26;
const AMP = STEP * 1.45;

function mix(t: number) {
  // indigo #8b9cf9 -> slate #3d4457
  const c = (a: number, b: number) => Math.round(a + t * (b - a));
  return `rgb(${c(139, 61)},${c(156, 68)},${c(249, 87)})`;
}

export default function Ridgeline({
  rows,
  teamsShown,
}: {
  rows: SpeedRow[];
  teamsShown: number;
}) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const teams = teamsByMean(rows).slice(0, teamsShown);
  if (!teams.length) return null;

  const all = rows.map((r) => r.top_speed_kmh);
  const xmin = Math.min(...all) - 1.5;
  const xmax = Math.max(...all) + 1.5;
  const tMedian = median(all);
  const n = teams.length;
  const height = n * STEP + Math.round(AMP) + 70;
  const x = linearScale(xmin, xmax, 110, Math.max(width, 360) - 20);
  const grid = Array.from({ length: 240 }, (_, i) => xmin + ((xmax - xmin) * i) / 239);

  return (
    <div ref={ref} className="relative">
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <text
            key={t}
            x={x(t)}
            y={height - 12}
            textAnchor="middle"
            fontSize={10.5}
            fill="var(--dim)"
          >
            {t} km/h
          </text>
        ))}
        <line
          x1={x(tMedian)}
          x2={x(tMedian)}
          y1={8}
          y2={height - 30}
          stroke="var(--faint)"
          strokeDasharray="4 4"
        />
        <text x={x(tMedian) + 4} y={14} fontSize={9.5} fill="var(--faint)">
          median {tMedian.toFixed(1)}
        </text>
        {[...teams].reverse().map((t, revIdx) => {
          const rank = n - 1 - revIdx; // 0 = fastest
          const base = rank * STEP + Math.round(AMP) + 6;
          const dens = kde(t.speeds, grid);
          const color = mix(rank / Math.max(n - 1, 1));
          const label = (
            <text
              key={`l-${t.team}`}
              x={100}
              y={base + 3}
              textAnchor="end"
              fontSize={10}
              fill="var(--ink)"
            >
              {t.team}
            </text>
          );
          if (!dens) return label;
          const peak = Math.max(...dens);
          const ys = dens.map((d) => (d / peak) * AMP);
          const path =
            `M ${x(grid[0])} ${base}` +
            ys.map((y, i) => ` L ${x(grid[i])} ${base - y}`).join("") +
            ` L ${x(grid[grid.length - 1])} ${base} Z`;
          const m = mean(t.speeds);
          const mIdx = Math.min(
            grid.length - 1,
            Math.max(0, Math.round(((m - xmin) / (xmax - xmin)) * (grid.length - 1))),
          );
          return (
            <g key={t.team}>
              {label}
              <path d={path} fill={color} fillOpacity={0.16} stroke={color} strokeWidth={1.3} />
              <line
                x1={x(m)}
                x2={x(m)}
                y1={base}
                y2={base - ys[mIdx]}
                stroke="var(--rose)"
                strokeWidth={1.4}
              />
              <circle
                cx={x(m)}
                cy={base - ys[mIdx]}
                r={4}
                fill="var(--rose)"
                onMouseMove={(e) => {
                  const b = (
                    e.currentTarget.ownerSVGElement!.parentElement as HTMLElement
                  ).getBoundingClientRect();
                  setTip({
                    x: e.clientX - b.left,
                    y: e.clientY - b.top,
                    lines: [
                      t.team,
                      `Mean ${m.toFixed(1)} km/h`,
                      `Range ${Math.min(...t.speeds).toFixed(1)}–${Math.max(...t.speeds).toFixed(1)}`,
                      `n=${t.speeds.length}`,
                    ],
                  });
                }}
                onMouseLeave={() => setTip(null)}
              />
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
