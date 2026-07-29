import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_NAMES, PARTY_COLORS, F5_ORDER_WFP as F5_ORDER, getContrastText } from '../../constants/parties';

// 2024 House composition (approximate)
const FPTP_HOUSE = { GOP: 220, DEM: 215 };
const FPTP_TOTAL = FPTP_HOUSE.GOP + FPTP_HOUSE.DEM;

// Proportional 2-party: 2024 House popular vote shares applied to 435 seats
// GOP ~51.7%, DEM ~46.9% (two-party: GOP 52.4%, DEM 47.6%)
const PR2_HOUSE = { GOP: 228, DEM: 207 };
const PR2_TOTAL = PR2_HOUSE.GOP + PR2_HOUSE.DEM;

// Shared with SenateCompositionCard so every seat-share bar in the app reads at the same scale.
export const BAR_HEIGHT = 52;
export const LABEL_COL_WIDTH = 90;

interface Props {
  seats: HouseSeat[];
  systemLabel: 'STV' | 'Party List';
  /** The other proportional system's seats at the current Wyoming rule — a 4th row in double-Wyoming view. */
  otherSystemSeats?: HouseSeat[];
  otherSystemLabel?: 'STV' | 'Party List';
  /** This system's seats under double-Wyoming — the comparison row in triple-Wyoming view. */
  doubleSeats?: HouseSeat[];
  wyoming?: 'double' | 'triple';
}

function buildSegments(seats: HouseSeat[]): { party: string; seats: number }[] {
  const segments: { party: string; seats: number }[] = [];
  for (const party of F5_ORDER) {
    const clusterId = Object.entries(CLUSTER_TO_PARTY).find(([, p]) => p === party)?.[0];
    if (!clusterId) continue;
    const row = seats.find(s => String(s.party) === clusterId);
    if (row && row.national > 0) segments.push({ party, seats: row.national });
  }
  return segments;
}

function SeatBar({ label, total, segments, faded = false }: {
  label: string; total: number; segments: { party: string; seats: number }[]; faded?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: LABEL_COL_WIDTH }}>
        <div className={`text-xs font-semibold ${faded ? 'text-muted-foreground' : 'text-foreground'}`}>{label}</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className={`flex-1 flex rounded-lg overflow-hidden ${faded ? 'opacity-60' : ''}`} style={{ height: BAR_HEIGHT }}>
        {segments.map(({ party, seats: n }) => {
          const pct = (n / total) * 100;
          const color = PARTY_COLORS[party] ?? '#6b7280';
          return (
            <div
              key={party}
              title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(1)}%)`}
              className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}
            >
              <span className="seat-segment-label text-xs font-bold leading-tight text-center px-0.5 chip-text" style={{ color: getContrastText(color) }}>
                {party}<br />{pct.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FixedPartyBar({ label, total, dem, gop }: { label: string; total: number; dem: number; gop: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: LABEL_COL_WIDTH }}>
        <div className="text-xs font-semibold text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: BAR_HEIGHT }}>
        <div className="flex items-center justify-center" style={{ width: `${(dem / total) * 100}%`, backgroundColor: '#1d4ed8' }}>
          <span className="text-white text-sm font-bold">Dem {dem} ({((dem / total) * 100).toFixed(0)}%)</span>
        </div>
        <div className="flex items-center justify-center" style={{ width: `${(gop / total) * 100}%`, backgroundColor: '#dc2626' }}>
          <span className="text-white text-sm font-bold">Rep {gop} ({((gop / total) * 100).toFixed(0)}%)</span>
        </div>
      </div>
    </div>
  );
}

function Legend({ label, segments }: { label: string; segments: { party: string; seats: number }[] }) {
  const total = segments.reduce((s, r) => s + r.seats, 0);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="shrink-0 text-xs font-semibold text-foreground" style={{ width: 68 }}>{label}</span>
      {segments.map(({ party, seats: n }) => (
        <span key={party} className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }} />
          <span className="text-xs text-muted-foreground font-medium">{party}</span>
          <span className="text-xs text-muted-foreground">{total ? (n / total * 100).toFixed(1) : '0.0'}%</span>
        </span>
      ))}
    </div>
  );
}

// Percentage-only, one entry per party comparing two systems side by side (e.g. "9.0% / 9.5%")
// rather than a seat count — seat counts across two different chamber sizes read as noise.
function CombinedLegend({ primaryLabel, secondaryLabel, primary, secondary }: {
  primaryLabel: string; secondaryLabel: string;
  primary: { party: string; seats: number }[]; secondary: { party: string; seats: number }[];
}) {
  const primaryTotal = primary.reduce((s, r) => s + r.seats, 0);
  const secondaryTotal = secondary.reduce((s, r) => s + r.seats, 0);
  const primaryByParty = Object.fromEntries(primary.map(s => [s.party, s.seats]));
  const secondaryByParty = Object.fromEntries(secondary.map(s => [s.party, s.seats]));
  const parties = [...primary.map(s => s.party)];
  for (const s of secondary) if (!parties.includes(s.party)) parties.push(s.party);

  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold text-foreground">{primaryLabel} / {secondaryLabel}</div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {parties.map(party => {
          const pPct = primaryTotal ? (primaryByParty[party] ?? 0) / primaryTotal * 100 : 0;
          const sPct = secondaryTotal ? (secondaryByParty[party] ?? 0) / secondaryTotal * 100 : 0;
          return (
            <span key={party} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }} />
              <span className="text-xs text-muted-foreground font-medium">{party}</span>
              <span className="text-xs text-muted-foreground">{pPct.toFixed(1)}% / {sPct.toFixed(1)}%</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export function FPTPvsSTV({ seats, systemLabel, otherSystemSeats, otherSystemLabel, doubleSeats, wyoming = 'double' }: Props) {
  const total = seats.reduce((s, r) => s + r.national, 0);
  const segments = buildSegments(seats);

  const otherTotal = otherSystemSeats?.reduce((s, r) => s + r.national, 0) ?? 0;
  const otherSegments = otherSystemSeats && otherTotal > 0 ? buildSegments(otherSystemSeats) : null;

  const dblTotal = doubleSeats?.reduce((s, r) => s + r.national, 0) ?? 0;
  const dblSegments = doubleSeats && dblTotal > 0 ? buildSegments(doubleSeats) : null;

  const isTriple = wyoming === 'triple';
  const title = isTriple
    ? `${systemLabel} — Double vs Triple Wyoming`
    : `FPTP vs ${systemLabel}${otherSegments ? ` vs ${otherSystemLabel}` : ''}`;

  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
        {title} — House of Representatives
      </div>

      <FixedPartyBar label="FPTP Today" total={FPTP_TOTAL} dem={FPTP_HOUSE.DEM} gop={FPTP_HOUSE.GOP} />
      <FixedPartyBar label="PR (2-party)" total={PR2_TOTAL} dem={PR2_HOUSE.DEM} gop={PR2_HOUSE.GOP} />
      <SeatBar label={isTriple ? `${systemLabel} (triple)` : `${systemLabel} (sim)`} total={total} segments={segments} />
      {isTriple
        ? dblSegments && <SeatBar label={`${systemLabel} (double)`} total={dblTotal} segments={dblSegments} faded />
        : otherSegments && <SeatBar label={`${otherSystemLabel} (sim)`} total={otherTotal} segments={otherSegments} />}

      {/* Legend — a combined row per party when two systems are shown, so seat counts across two
          different chamber sizes don't have to be mentally converted to compare. */}
      <div className="mt-3 pt-2 border-t border-border/50">
        {isTriple
          ? (dblSegments
              ? <CombinedLegend primaryLabel={`${systemLabel} (triple)`} secondaryLabel={`${systemLabel} (double)`} primary={segments} secondary={dblSegments} />
              : <Legend label={systemLabel} segments={segments} />)
          : (otherSegments
              ? <CombinedLegend primaryLabel={systemLabel} secondaryLabel={otherSystemLabel ?? ''} primary={segments} secondary={otherSegments} />
              : <Legend label={systemLabel} segments={segments} />)}
      </div>
    </div>
  );
}
