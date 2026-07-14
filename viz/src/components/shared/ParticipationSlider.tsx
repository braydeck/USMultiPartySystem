export const GAP_STOPS = [0, 25, 50, 75, 100] as const;
// Plausible post-reform mobilization: PR closes the 'no representation' slice of the
// turnout gap but not the SES slice (income/education), so realistic closure is small.
const PLAUSIBLE_MAX = 30; // % of the gap

interface Props {
  /** % of the inter-force turnout gap that has closed (one of GAP_STOPS). */
  value: number;
  onChange: (v: number) => void;
}

/** Gap-compression slider: as-cast 2024 turnout (0%) → full parity (100%).
 *  Sweeps how much each force's turnout gap closes; datasets are precomputed per
 *  stop, so it snaps to the 5 GAP_STOPS. The shaded band marks the plausible
 *  realistic mobilization range; it is a sensitivity control, not a forecast. */
export function ParticipationSlider({ value, onChange }: Props) {
  const idx = Math.max(0, GAP_STOPS.indexOf(value as typeof GAP_STOPS[number]));
  const label = value === 0 ? 'As cast' : value === 100 ? 'Parity' : `${value}% closed`;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground uppercase tracking-widest">Participation</span>
      <div className="flex flex-col gap-0.5 w-[168px]"
        title="Turnout gap closed: as-cast 2024 (0%) → full parity (100%). Shaded = plausible post-reform range (~0–30%).">
        <input
          type="range" min={0} max={GAP_STOPS.length - 1} step={1} value={idx}
          onChange={e => onChange(GAP_STOPS[Number(e.target.value)])}
          className="w-full accent-indigo-600 cursor-pointer"
          aria-label="Turnout gap closed"
        />
        {/* plausible-mobilization band (gap% maps 1:1 to track fraction) */}
        <div className="relative h-1 rounded bg-slate-200">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70"
            style={{ width: `${PLAUSIBLE_MAX}%` }} />
        </div>
        <div className="flex justify-between text-[9px] text-muted-foreground leading-none">
          <span>As cast&nbsp;’24</span>
          <span className="font-semibold text-foreground">{label}</span>
          <span>Parity</span>
        </div>
      </div>
    </div>
  );
}
