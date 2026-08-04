import { FIELD_LABEL } from '../../constants/typography';
export const GAP_STOPS = [0, 5, 10, 15, 20, 25, 30] as const;
// Zone by stop: 0 = observed data, 5–15 = plausible (15 = ceiling), 20–30 = stress (beyond one-cycle evidence).
const ZONE: Record<number, string> = { 0: 'observed', 5: 'plausible', 10: 'plausible', 15: 'plausible', 20: 'stress', 25: 'stress', 30: 'stress' };

interface Props {
  /** % of the inter-force turnout gap closed (one of GAP_STOPS). */
  value: number;
  onChange: (v: number) => void;
}

/** Gap-compression slider (the contraction effect): 0% = observed 2024 turnout,
 *  higher = the suppressed forces close X% of their turnout gap toward the mobilized.
 *  Snaps to GAP_STOPS; 0–10% is literature-plausible, 20–30% is stress. */
export function ParticipationSlider({ value, onChange }: Props) {
  const idx = Math.max(0, GAP_STOPS.indexOf(value as typeof GAP_STOPS[number]));
  return (
    <div className="flex items-center gap-2">
      <span className={FIELD_LABEL}>Turnout gap closed</span>
      <div className="flex flex-col gap-0.5 w-[168px]"
        title="Share of the inter-force turnout gap closed (contraction effect). 0% = observed 2024; ≤15% plausible for one cycle; 20–30% = stress test.">
        <input
          type="range" min={0} max={GAP_STOPS.length - 1} step={1} value={idx}
          onChange={e => onChange(GAP_STOPS[Number(e.target.value)])}
          className="w-full accent-indigo-600 cursor-pointer"
          aria-label="Turnout gap closed"
        />
        {/* plausible (≤15%) vs stress (20–30%) — stops at 0/.17/.33/.5/.67/.83/1; boundary drawn between the 15 and 20 stops */}
        <div className="relative h-1 rounded bg-amber-200/70">
          <div className="absolute inset-y-0 left-0 rounded bg-emerald-400/70" style={{ width: '58.33%' }} />
        </div>
        <div className="flex justify-between text-4xs text-muted-foreground leading-none">
          <span>Observed</span>
          <span className="font-semibold text-foreground">{value}% · {ZONE[value]}</span>
          <span>Stress</span>
        </div>
      </div>
    </div>
  );
}
