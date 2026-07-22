import { Card } from '@/components/ui/card';
import { factorDistance, policyDivergence } from '../../lib/partyDistance';
import { getBlendColor, PARTY_NAMES, CURRENT_PARTIES } from '../../constants/parties';

export interface DistanceInputs {
  /** z-score vectors keyed z_F1..z_F5, per party code (formulated + current). */
  zByCode: Record<string, Record<string, number>>;
  /** per-(formulated,current) list of shared per-item policy distances (0–100). */
  policyItems: Record<string, Record<string, number[]>>;
  /** η² per factor. */
  eta: Record<string, number>;
  /** selected formulated party codes, in display order. */
  formulated: string[];
}

export function CurrentPartyDistance({ zByCode, policyItems, eta, formulated }: DistanceInputs) {
  if (formulated.length === 0) return null;
  const curs = CURRENT_PARTIES.filter(c => zByCode[c]);
  if (curs.length === 0) return null;

  return (
    <Card className="overflow-hidden">
      <div className="px-4 py-3 border-b border-border/50 bg-muted">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Distance from today's parties</span>
        <span className="text-xs text-muted-foreground ml-3">factor σ (η²-weighted) · policy divergence (avg per-item)</span>
      </div>
      <div className="divide-y divide-border/50">
        {formulated.map(code => {
          const rows = curs.map(cur => ({
            cur,
            fac: factorDistance(zByCode[code], zByCode[cur], eta),
            pol: policyDivergence(policyItems[code]?.[cur] ?? []),
          }));
          const nearest = rows.reduce((a, b) => (b.fac < a.fac ? b : a), rows[0]);
          return (
            <div key={code} className="px-4 py-2.5 flex items-center gap-3 flex-wrap">
              <span className="text-xs font-bold w-24 shrink-0" style={{ color: getBlendColor(code) }}>
                {PARTY_NAMES[code] ?? code}
              </span>
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {rows.map(r => (
                  <span key={r.cur}
                    className={`text-[11px] tabular-nums ${r.cur === nearest.cur ? 'font-semibold' : 'text-muted-foreground'}`}>
                    <span style={{ color: getBlendColor(r.cur) }}>{PARTY_NAMES[r.cur] ?? r.cur}</span>{' '}
                    {r.fac.toFixed(1)}σ / {Math.round(r.pol)}
                    {r.cur === nearest.cur && <span className="ml-1 text-amber-500">◀ nearest</span>}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
