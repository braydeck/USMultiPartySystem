import { Card } from '@/components/ui/card';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import vData from '../../data/turnoutVerification.json';

type Party = { party: string; verifiedVoted: number; matchedNonvoter: number; unmatched: number };
type VData = { national: Party; parties: Party[] };
const DATA = vData as VData;

// Sorted by unmatched (unknown) descending: the "how findable is this force" claim.
const ORDER = [...DATA.parties].sort((a, b) => b.unmatched - a.unmatched);

const NONVOTER = '#64748b'; // slate-500 — confirmed non-voter (on file, no vote)

function Row({ r }: { r: Party }) {
  const color = PARTY_COLORS[r.party] ?? '#6b7280';
  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 104 }}>
        <div className="text-xs font-semibold text-foreground">{PARTY_NAMES[r.party] ?? r.party}</div>
        <div className="text-[11px] text-muted-foreground">{r.verifiedVoted}% confirmed</div>
      </div>
      <div className="flex-1 flex rounded overflow-hidden" style={{ height: 22 }}>
        {/* verified voters: solid party color */}
        <div className="flex items-center justify-center" title={`Verified voted: ${r.verifiedVoted}%`}
          style={{ width: `${r.verifiedVoted}%`, backgroundColor: color }} />
        {/* matched non-voter: solid slate */}
        <div title={`Confirmed non-voter: ${r.matchedNonvoter}%`}
          style={{ width: `${r.matchedNonvoter}%`, backgroundColor: NONVOTER }} />
        {/* unmatched: striped grey (unknown) */}
        <div title={`Not on voter file (unknown): ${r.unmatched}%`}
          style={{
            width: `${r.unmatched}%`,
            backgroundImage: 'repeating-linear-gradient(45deg, #cbd5e1, #cbd5e1 4px, #e2e8f0 4px, #e2e8f0 8px)',
          }} />
      </div>
      <div className="shrink-0 text-right text-[11px] text-muted-foreground" style={{ width: 78 }}>
        {r.unmatched}% unknown
      </div>
    </div>
  );
}

export function TurnoutVerificationCard() {
  return (
    <Card className="p-5">
      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Turnout, Verified Against the Voter File
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        Self-reported turnout runs ~86% because survey respondents over-claim voting, but the shortfall against the
        voter file is mostly not lying: it is match failure. Solid is a 2024 vote confirmed on the TargetSmart file,
        slate is a confirmed non-voter, striped grey is a respondent the file could not locate at all.
      </p>

      <div className="space-y-1.5">
        {ORDER.map(r => <Row key={r.party} r={r} />)}
      </div>

      {/* Legend + national reference */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-3 pt-2 border-t border-border/50 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-foreground/70" />
          <span>Verified voted</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: NONVOTER }} />
          <span>Confirmed non-voter</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{
            backgroundImage: 'repeating-linear-gradient(45deg, #cbd5e1, #cbd5e1 3px, #e2e8f0 3px, #e2e8f0 6px)',
          }} />
          <span>Not on file (unknown)</span>
        </div>
        <div className="ml-auto">National: {DATA.national.verifiedVoted}% verified, {DATA.national.unmatched}% unmatched</div>
      </div>

      <p className="text-xs text-muted-foreground mt-2">
        Solidarity is the extreme case: 63% of its members cannot be matched to the file at all, so its true turnout is
        genuinely uncertain, bounded below by the 32% we can confirm. The over-report itself, measured only among
        matched respondents, is small everywhere (under 6 points), and low-engagement forces are the hardest to verify,
        not the biggest liars. This is why validated turnout is treated as a floor throughout the simulation.
      </p>
    </Card>
  );
}
