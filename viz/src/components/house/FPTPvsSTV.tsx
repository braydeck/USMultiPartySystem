import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_NAMES, PARTY_COLORS, F5_ORDER } from '../../constants/parties';

// 2024 House composition (approximate)
const FPTP_HOUSE = { GOP: 220, DEM: 215 };
const FPTP_TOTAL = FPTP_HOUSE.GOP + FPTP_HOUSE.DEM;

// Proportional 2-party: 2024 House popular vote shares applied to 435 seats
// GOP ~51.7%, DEM ~46.9% (two-party: GOP 52.4%, DEM 47.6%)
const PR2_HOUSE = { GOP: 228, DEM: 207 };
const PR2_TOTAL = PR2_HOUSE.GOP + PR2_HOUSE.DEM;

interface Props {
  seats: HouseSeat[];
}

export function FPTPvsSTV({ seats }: Props) {
  const stvTotal = seats.reduce((s, r) => s + r.national, 0);

  // Build STV segments in F5 order
  const stvSegments: { party: string; seats: number }[] = [];
  for (const party of F5_ORDER) {
    const clusterId = Object.entries(CLUSTER_TO_PARTY).find(([, p]) => p === party)?.[0];
    if (!clusterId) continue;
    const row = seats.find(s => String(s.party) === clusterId);
    if (row && row.national > 0) stvSegments.push({ party, seats: row.national });
  }

  const fptpBarH = 52;
  const stvBarH = 52;
  const labelColW = 80;

  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
        FPTP vs STV — House of Representatives
      </div>

      {/* FPTP row */}
      <div className="flex items-center gap-3">
        <div className="shrink-0 text-right" style={{ width: labelColW }}>
          <div className="text-xs font-semibold text-slate-700">FPTP Today</div>
          <div className="text-xs text-slate-400">{FPTP_TOTAL} seats</div>
        </div>
        <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: fptpBarH }}>
          <div
            className="flex items-center justify-center"
            style={{
              width: `${(FPTP_HOUSE.DEM / FPTP_TOTAL) * 100}%`,
              backgroundColor: '#1d4ed8',
            }}
          >
            <span className="text-white text-sm font-bold">
              Dem {FPTP_HOUSE.DEM} ({((FPTP_HOUSE.DEM / FPTP_TOTAL) * 100).toFixed(0)}%)
            </span>
          </div>
          <div
            className="flex items-center justify-center"
            style={{
              width: `${(FPTP_HOUSE.GOP / FPTP_TOTAL) * 100}%`,
              backgroundColor: '#dc2626',
            }}
          >
            <span className="text-white text-sm font-bold">
              Rep {FPTP_HOUSE.GOP} ({((FPTP_HOUSE.GOP / FPTP_TOTAL) * 100).toFixed(0)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Proportional 2-party row */}
      <div className="flex items-center gap-3">
        <div className="shrink-0 text-right" style={{ width: labelColW }}>
          <div className="text-xs font-semibold text-slate-700">PR (2-party)</div>
          <div className="text-xs text-slate-400">{PR2_TOTAL} seats</div>
        </div>
        <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: fptpBarH }}>
          <div
            className="flex items-center justify-center"
            style={{ width: `${(PR2_HOUSE.DEM / PR2_TOTAL) * 100}%`, backgroundColor: '#1d4ed8' }}
          >
            <span className="text-white text-sm font-bold">
              Dem {PR2_HOUSE.DEM} ({((PR2_HOUSE.DEM / PR2_TOTAL) * 100).toFixed(0)}%)
            </span>
          </div>
          <div
            className="flex items-center justify-center"
            style={{ width: `${(PR2_HOUSE.GOP / PR2_TOTAL) * 100}%`, backgroundColor: '#dc2626' }}
          >
            <span className="text-white text-sm font-bold">
              Rep {PR2_HOUSE.GOP} ({((PR2_HOUSE.GOP / PR2_TOTAL) * 100).toFixed(0)}%)
            </span>
          </div>
        </div>
      </div>

      {/* STV row */}
      <div className="flex items-center gap-3">
        <div className="shrink-0 text-right" style={{ width: labelColW }}>
          <div className="text-xs font-semibold text-slate-700">STV (sim)</div>
          <div className="text-xs text-slate-400">{stvTotal} seats</div>
        </div>
        <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: stvBarH }}>
          {stvSegments.map(({ party, seats: n }) => {
            const pct = (n / stvTotal) * 100;
            const color = PARTY_COLORS[party] ?? '#6b7280';
            return (
              <div
                key={party}
                title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(1)}%)`}
                className="flex items-center justify-center overflow-hidden"
                style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}
              >
                {pct >= 5 && (
                  <span className="text-white text-xs font-bold leading-tight text-center px-0.5">
                    {party}<br />{pct.toFixed(1)}%
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 pt-2 border-t border-slate-100">
        {stvSegments.map(({ party, seats: n }) => {
          const pct = (n / stvTotal) * 100;
          return (
          <div key={party} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }} />
            <span className="text-xs text-slate-600 font-medium">{party}</span>
            <span className="text-xs text-slate-400">{n} ({pct.toFixed(1)}%)</span>
          </div>
          );
        })}
      </div>

      <p className="text-xs text-slate-400 mt-1">
        FPTP: winner-take-all produces a 2-party monopoly with disproportionate seat shares.
        PR (2-party): same two parties but seats match vote share — still just two parties.
        STV: {stvSegments.length} parties proportionally represented across {stvTotal} seats.
      </p>
    </div>
  );
}
