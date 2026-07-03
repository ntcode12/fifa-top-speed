"use client";

import { useEffect, useState } from "react";
import Tooltip, { TooltipState } from "../Tooltip";
import useMeasure from "../useMeasure";
import { linearScale, ticks } from "@/lib/scale";
import { deltas } from "@/lib/stats";
import type { SpeedRow } from "@/lib/types";

const ROW_H = 44;

export default function Dumbbell({ rows, n }: { rows: SpeedRow[]; n: number }) {
  const [ref, width] = useMeasure<HTMLDivElement>();
  const [tip, setTip] = useState<TooltipState | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  useEffect(() => setHidden(new Set()), [rows, n]);

  const items = deltas(rows, n);
  if (!items.length) {
    return (
      <div className="glass px-6 py-6 text-sm text-[var(--dim)]">
        Not enough players with multiple appearances in this filter.
      </div>
    );
  }

  const xmin = Math.min(...items.map((d) => d.slow)) - 1.5;
  const xmax = Math.max(...items.map((d) => d.fast)) + 1.5;
  const height = items.length * ROW_H + 40;
  const x = linearScale(xmin, xmax, 8, Math.max(width, 320) - 48);

  return (
    <div ref={ref} className="relative">
      {hidden.size > 0 && (
        <button
          onClick={() => setHidden(new Set())}
          className="glass absolute -top-12 right-0 px-4 py-1.5 text-[12px] text-[var(--ink)]"
        >
          ↺ Show all
        </button>
      )}
      <svg width="100%" height={height}>
        {ticks(xmin, xmax, 6).map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={0} y2={height - 30} stroke="rgba(255,255,255,0.09)" />
            <text x={x(t)} y={height - 12} textAnchor="middle" fontSize={10.5} fill="var(--dim)">
              {t} km/h
            </text>
          </g>
        ))}
        {items.map((d, i) => {
          const cy = i * ROW_H + 30;
          const off = hidden.has(d.player);
          return (
            <g
              key={d.player}
              className="cursor-pointer"
              onClick={() =>
                setHidden((h) => {
                  const nh = new Set(h);
                  if (nh.has(d.player)) nh.delete(d.player);
                  else nh.add(d.player);
                  return nh;
                })
              }
              onMouseMove={(e) => {
                if (off) return;
                const b = (
                  e.currentTarget.ownerSVGElement!.parentElement as HTMLElement
                ).getBoundingClientRect();
                setTip({
                  x: e.clientX - b.left,
                  y: e.clientY - b.top,
                  lines: [
                    `${d.player} · ${d.team}`,
                    `Slower ${d.slow.toFixed(1)} · Faster ${d.fast.toFixed(1)}`,
                    `Δ ${d.delta.toFixed(1)} km/h`,
                  ],
                });
              }}
              onMouseLeave={() => setTip(null)}
            >
              <text
                x={x(xmin)}
                y={cy - 8}
                fontSize={11.5}
                fill={off ? "var(--faint)" : "var(--ink)"}
                fontWeight={600}
              >
                {d.player}
                <tspan fill={off ? "var(--faint)" : "var(--dim)"} fontWeight={400}>
                  {"  "}
                  {d.team} · Δ{d.delta.toFixed(1)}
                </tspan>
              </text>
              <line
                x1={x(d.slow)}
                x2={x(d.fast)}
                y1={cy}
                y2={cy}
                stroke={off ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.14)"}
                strokeWidth={2.5}
              />
              {!off && (
                <>
                  <circle
                    cx={x(d.slow)}
                    cy={cy}
                    r={5}
                    fill="#141a2e"
                    stroke="var(--indigo)"
                    strokeWidth={1.8}
                  />
                  <circle cx={x(d.fast)} cy={cy} r={5} fill="var(--indigo)" />
                  <text
                    x={x(d.slow) - 9}
                    y={cy + 3}
                    textAnchor="end"
                    fontSize={9}
                    fill="var(--dim)"
                  >
                    {d.slow.toFixed(1)}
                  </text>
                  <text x={x(d.fast) + 9} y={cy + 3} fontSize={9} fill="var(--indigo)" fontWeight={700}>
                    {d.fast.toFixed(1)}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}
