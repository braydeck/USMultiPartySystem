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
  perDistrict: {
    districtsWon: number; median: number; max: number;
    hist: Record<string, number>; multiSeatShare: number;
  };
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
            <div key={row.party} className="grid grid-cols-[7rem_1fr_3rem_4.5rem] items-start gap-2 pt-0.5">
              <div className="min-w-0">
                <div className="text-xs font-medium truncate" style={{ color: PARTY_COLORS[row.party] }}>
                  {name(row.party)}
                </div>
                <div className={FOOTNOTE}>{row.seats} seats</div>
              </div>

              <div className="h-6 rounded overflow-hidden flex">
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
              </div>

              <div
                className="text-xs font-semibold tabular-nums text-right text-foreground"
                title={`${pct(row.ownShare)}% own voters across all seats; ${pct(row.marginalOwnShare)}% on the last seat won in each district`}
              >
                {pct(row.ownShare)}%
              </div>

              {/* Seats per district won: the variable behind everything else here. Only
                  Conservative regularly takes more than one seat in the same district. */}
              <div
                className="text-right"
                title={`Wins seats in ${row.perDistrict.districtsWon} districts; takes more than one seat in ${pct(row.perDistrict.multiSeatShare)}% of them`}
              >
                <div className="text-xs tabular-nums text-foreground">
                  {(row.seats / row.perDistrict.districtsWon).toFixed(2)}
                </div>
                <div className={FOOTNOTE}>in {row.perDistrict.districtsWon}</div>
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
        <span className="ml-auto normal-case tracking-normal">
          columns: own share · seats per district won
        </span>
      </div>

      <p className={`${CARD_HINT} mb-1`}>
        This describes how a party assembles a quota, not how well it converts votes into
        seats. The two are independent here: Conservative and Progressive both elect close to
        90% of their weight from their own voters, and Conservative finishes 34 seats above a
        proportional list while Progressive finishes 7 below. Compare the Party List view for
        conversion. Own share also slips on a party&apos;s last seat in a district, by 8.3
        points for Conservative and 2.7 for Labour, but that mostly follows from having won an
        earlier seat with the same voters rather than from any weakness.
      </p>
      <p className={CARD_HINT}>
        Fixed at the app default: {DATA.config.apportionment} apportionment,
        rank-{DATA.config.ballotDepth} ballots, {Math.round(DATA.config.turnoutGap * 100)}% turnout gap
        closed. It does not follow the depth or turnout controls above.
      </p>
    </div>
  );
}
