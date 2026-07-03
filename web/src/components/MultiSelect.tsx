"use client";

import { useEffect, useRef, useState } from "react";
import { flagUrl } from "@/lib/flags";

export default function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const toggle = (o: string) =>
    onChange(selected.includes(o) ? selected.filter((s) => s !== o) : [...selected, o]);
  const shown = options.filter((o) => o.toLowerCase().includes(q.toLowerCase()));

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="glass w-full px-4 py-2.5 text-left text-[13px] text-[var(--ink)]"
      >
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--dim)]">
          {label}
        </span>
        <div className="mt-0.5 truncate">
          {selected.length ? selected.join(", ") : `All ${options.length}`}
        </div>
      </button>
      {open && (
        <div className="absolute z-20 mt-2 max-h-72 w-full overflow-auto rounded-2xl border border-white/15 bg-[#12182c] p-2 shadow-2xl">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search…"
            className="mb-2 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-[13px] outline-none placeholder:text-[var(--faint)]"
          />
          {selected.length > 0 && (
            <button
              onClick={() => onChange([])}
              className="mb-1 w-full rounded-lg px-3 py-1.5 text-left text-[12px] text-[var(--rose)] hover:bg-white/5"
            >
              Clear selection
            </button>
          )}
          {shown.map((o) => (
            <button
              key={o}
              onClick={() => toggle(o)}
              className={`block w-full rounded-lg px-3 py-1.5 text-left text-[13px] hover:bg-white/5 ${
                selected.includes(o) ? "text-[var(--indigo)]" : "text-[var(--ink)]"
              }`}
            >
              {selected.includes(o) ? "✓ " : ""}
              {flagUrl(o) && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={flagUrl(o)!}
                  alt=""
                  className="mr-2 inline h-3 w-4 rounded-[2px] object-cover align-[-1px]"
                />
              )}
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
