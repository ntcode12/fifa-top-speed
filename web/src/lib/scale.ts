export function linearScale(d0: number, d1: number, r0: number, r1: number) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  return (x: number) => r0 + (x - d0) * k;
}

export function ticks(min: number, max: number, count: number): number[] {
  const span = max - min;
  const raw = span / Math.max(count, 1);
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * pow).find((s) => span / s <= count) ?? pow * 10;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(10)));
  return out;
}
