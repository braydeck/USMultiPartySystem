import { getBlendColor, getContrastText } from '../../constants/parties';
import { Card } from '@/components/ui/card';

/**
 * What first-past-the-post does with this field, counted nationally: one stacked bar of
 * first preferences and the plurality that would win on them.
 *
 * This file used to be `PresidentialMap` and carried two more panels — a per-state vote
 * share grid and a per-state winner map with its own electoral college tally. Both are now
 * views of the cartogram in `ECCartogram`, which sizes states by population or by
 * electoral weight instead of drawing every state the same size.
 *
 * Shares come from round one of the instant runoff via `nationalFirstChoice`, not from
 * re-weighting the per-state shares. The two agree to within 0.05 points, and having one
 * source means the bar cannot drift from the FPTP card above it.
 */
export function NationalFPTPProjection({ shares, label }: {
  shares: { code: string; pct: number }[];
  label: (code: string) => string;
}) {
  if (shares.length === 0) return null;
  const leader = shares[0];

  return (
    <Card className="p-4">
      <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        National FPTP Projection
      </h4>
      <p className="text-xs text-muted-foreground mb-3">
        Who would win under current first-past-the-post rules.
      </p>

      <div className="text-sm mb-2">
        <span className="font-bold" style={{ color: getBlendColor(leader.code) }}>
          {label(leader.code)}
        </span>
        <span className="text-foreground"> wins with </span>
        <span className="font-bold">{(leader.pct * 100).toFixed(1)}%</span>
        <span className="text-muted-foreground"> of the first-choice vote</span>
      </div>

      <div className="flex rounded overflow-hidden h-8">
        {shares.map(({ code, pct }) => {
          const w = pct * 100;
          const color = getBlendColor(code);
          return (
            <div
              key={code}
              className="flex items-center justify-center overflow-hidden"
              style={{ width: `${w}%`, backgroundColor: color, minWidth: w < 2 ? 2 : 0 }}
              title={`${label(code)}: ${w.toFixed(1)}%`}
            >
              {w > 6 && (
                <span className="text-xs font-bold px-0.5 truncate chip-text"
                  style={{ color: getContrastText(color), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                  {label(code)} {w.toFixed(1)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
