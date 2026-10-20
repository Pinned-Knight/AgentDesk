export const fmtNum = (n: number): string => Math.round(n).toLocaleString();

/** 0..1 ratio -> "12.5%" (one decimal at most). */
export const fmtPct = (ratio: number): string => `${Math.round(ratio * 1000) / 10}%`;

export const fmtMs = (ms: number): string => `${Math.round(ms).toLocaleString()} ms`;

export function fmtDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export const shortId = (id: string, length = 8): string => id.slice(0, length);

/** Clamp a 0..1 confidence to a whole-number percentage. */
export const toPercent = (value: unknown): number => Math.round(Math.min(Math.max(Number(value) || 0, 0), 1) * 100);
