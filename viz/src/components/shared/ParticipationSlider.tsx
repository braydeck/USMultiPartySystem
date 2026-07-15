export const GAP_STOPS = [0, 25, 50, 75, 100] as const;
// Plausible range: realistically only a small share of non-voters would be newly mobilized.
const PLAUSIBLE_MAX = 30; // % of non-voters

interface Props {
  /** Share of current non-voters who turn out (one of GAP_STOPS). */
  value: number;
  onChange: (v: number) => void;
}

/** Non-voter turnout slider: 0% = 2024 actual, 100% = everyone votes. The value is
 *  the share of each force's current non-voters who show up; datasets are precomputed
 *  per stop, so it snaps to the 5 GAP_STOPS. */
export function ParticipationSlider({ value, onChange }: Props) {
  const idx = Math.max(0, GAP_STOPS.indexOf(value as typeof GAP_STOPS[number]));
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground uppercase tracking-widest">Non-voter turnout</span>
      <div className="flex flex-col gap-0.5 w-[168px]"
        title="Share of today's non-voters who show up: 0% = 2024 actual, 100% = everyone votes. Shaded = plausible range (~0–30%).">
        <input
          type="range" min={0} max={GAP_STOPS.length - 1} step={1} value={idx}
          onChange={e => onChange(GAP_STOPS[Number(e.target.value)])}
          className="w-full accent-indigo-600 cursor-pointer"
          aria-label="Share of non-voters who show up"
        />
        {/* plausible-mobilization band (value maps 1:1 to track fraction) */}
        <div className="relative h-1 rounded bg-slate-200">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70"
            style={{ width: `${PLAUSIBLE_MAX}%` }} />
        </div>
        <div className="flex justify-between text-[9px] text-muted-foreground leading-none">
          <span>2024 actual</span>
          <span className="font-semibold text-foreground">{value}% of non-voters</span>
          <span>Everyone</span>
        </div>
      </div>
    </div>
  );
}
