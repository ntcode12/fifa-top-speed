"use client";

import MultiSelect from "./MultiSelect";

export interface FilterState {
  teams: string[];
  matches: string[];
  topN: number;
  deltaN: number;
  ridgeN: number;
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="glass flex items-center gap-3 px-4 py-2.5 text-[12px] text-[var(--dim)]">
      <span className="whitespace-nowrap">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#8b9cf9]"
      />
      <span className="w-6 text-right font-bold text-[var(--ink)]">{value}</span>
    </label>
  );
}

export default function FilterBar({
  allTeams,
  allMatches,
  state,
  onChange,
}: {
  allTeams: string[];
  allMatches: string[];
  state: FilterState;
  onChange: (next: FilterState) => void;
}) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-3 max-sm:grid-cols-1 lg:grid-cols-5">
      <MultiSelect
        label="Teams"
        options={allTeams}
        selected={state.teams}
        onChange={(teams) => onChange({ ...state, teams })}
      />
      <MultiSelect
        label="Matches"
        options={allMatches}
        selected={state.matches}
        onChange={(matches) => onChange({ ...state, matches })}
      />
      <SliderField label="Top N" value={state.topN} min={10} max={40} step={5}
        onChange={(topN) => onChange({ ...state, topN })} />
      <SliderField label="Delta N" value={state.deltaN} min={10} max={30} step={5}
        onChange={(deltaN) => onChange({ ...state, deltaN })} />
      <SliderField label="Teams shown" value={state.ridgeN} min={10} max={48} step={2}
        onChange={(ridgeN) => onChange({ ...state, ridgeN })} />
    </div>
  );
}
