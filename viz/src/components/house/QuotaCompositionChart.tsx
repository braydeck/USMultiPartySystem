import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { CARD_HINT, FOOTNOTE, TABLE_HEADER } from '../../constants/typography';
import quotaComposition from '../../data/quotaComposition.json';

interface PartyRow {
  party: string;
  seats: number;
  belowQuota: number;
  ownShare: number;
  byOrigin: Record<string, number>;
  ownDepth: Record<string, number>;
  marginalByOrigin: Record<string, number>;
  marginalOwnShare: number;
}
interface Bundle {
  config: { apportionment: string; ballotDepth: number; turnoutGap: number };
  parties: PartyRow[];
}

const DATA = quotaComposition as unknown as Bundle;

const name = (p: string) => PARTY_NAMES[p] ?? p;
const pct = (x: number) => Math.round(x * 100);

/** Whose ballots elected each party's seats: own first-preference voters against votes
 *  borrowed from other parties' voters. Origin rather than preference depth, because
 *  ballots are party-contiguous and depth mostly reports slate size. */
export function QuotaCompositionChart({ filterParties }: { filterParties?: string[] }) {
  const rows = filterParties
    ? DATA.parties.filter(r => filterParties.includes(r.party))
    : DATA.parties;
  if (!rows.length) return null;

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        {rows.map(row => {
          const segs = Object.entries(row.byOrigin)
            .sort((a, b) => (a[0] === row.party ? -1 : b[0] === row.party ? 1 : b[1] - a[1]));
          return (
            <div key={row.party} className="grid grid-cols-[7rem_1fr_3.5rem] items-center gap-2">
              <div className="min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: PARTY_COLORS[row.party] }}>
                  {name(row.party)}
                </div>
                <div className={FOOTNOTE}>{row.seats} seats</div>
              </div>

              <div className="relative h-6 rounded overflow-hidden flex">
                {segs.map(([origin, share]) => (
                  <div
                    key={origin}
                    className="h-full flex items-center justify-center overflow-hidden"
                    style={{
                      width: `${share * 100}%`,
                      backgroundColor: PARTY_COLORS[origin] ?? '#94a3b8',
                      opacity: origin === row.party ? 1 : 0.55,
                      boxShadow: origin === row.party ? 'none' : 'inset 1px 0 0 rgba(255,255,255,.65)',
                    }}
                    title={`${pct(share)}% of the weight electing ${name(row.party)} seats came from ${name(origin)} first-preference voters`}
                  >
                    {share >= 0.14 && (
                      <span className="text-2xs font-semibold text-white whitespace-nowrap px-1">
                        {pct(share)}%
                      </span>
                    )}
                  </div>
                ))}
                {/* Marginal seat: where the own-share sits on the last seat the party wins
                    in each district, which is where viability is actually decided. */}
                <div
                  className="absolute inset-y-0 w-0.5 bg-foreground"
                  style={{ left: `${row.marginalOwnShare * 100}%` }}
                  title={`Last seat won per district: ${pct(row.marginalOwnShare)}% own voters`}
                />
              </div>

              <div className="text-xs font-semibold tabular-nums text-right text-foreground">
                {pct(row.ownShare)}%
              </div>
            </div>
          );
        })}
      </div>

      <div className={`flex flex-wrap items-center gap-x-4 gap-y-1 ${TABLE_HEADER}`}>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-slate-500" />own first-preference voters
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-slate-500 opacity-55" />borrowed, coloured by lender
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3.5 w-0.5 bg-foreground" />own share of the last seat won
        </span>
        <span className="ml-auto normal-case tracking-normal">right column = own share</span>
      </div>

      <p className={CARD_HINT}>
        Fixed at the app default: {DATA.config.apportionment} apportionment,
        rank-{DATA.config.ballotDepth} ballots, {Math.round(DATA.config.turnoutGap * 100)}% turnout gap
        closed. It does not follow the depth or turnout controls above.
      </p>
    </div>
  );
}
