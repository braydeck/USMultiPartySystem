import { useMemo } from 'react';
import type { VoteModelRow, PresidentialElection, CandidateVoteRow } from '../../types';
import { getBlendColor } from '../../constants/parties';
import type { VoteMode, HouseSystem } from '../../constants/labels';
import { SHOW_CROSSOVER } from '../../constants/features';
import { blocOutcome, houseProbField, presSigns, type SeatMap } from './voteBloc';
import { getBayesianLabel, getDirection, VerdictBadge, SignBadge, WhippedBadge, type VerdictLabel } from './UnifiedBillTable';
import { Card } from '@/components/ui/card';
import { FIELD_LABEL } from '../../constants/typography';

// Crossover only; the party-line side resolves by the party of the president in `election`,
// which is the one this panel displays.
const FD_SIGN: Record<string, keyof VoteModelRow> = {
  'factorDev+condorcet': 'presFDCondSigns',
  'factorDev+irv':       'presFDIRVSigns',
};

const FD_PCT: Record<string, keyof VoteModelRow> = {
  'factorDev+condorcet': 'presFDCondPct',
  'factorDev+irv':       'presFDIRVPct',
};

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  election: PresidentialElection;
  pipeline: 'rawMulti' | 'factorDev';
  wyoming?: 'double' | 'triple';
  /** Which House counting rule seats the chamber: STV transfers or a Hare-quota party list. */
  system?: HouseSystem;
  // Whipped mode: deterministic party-bloc verdicts. Senate composition differs by method,
  // so the two methods can pass/fail a bill differently even under whipping.
  voteModel?: VoteMode;
  candidateVotes?: CandidateVoteRow[];
  houseSeats?: SeatMap;
  senateSeatsCond?: SeatMap;
  senateSeatsIRV?: SeatMap;
}

type Row = {
  row: VoteModelRow;
  houseLabel: VerdictLabel | '';
  senateCondLabel: VerdictLabel | '';
  senateIRVLabel: VerdictLabel | '';
  condPresPct: number | undefined;
  irvPresPct: number | undefined;
  housePass: boolean; senateCondPass: boolean; senateIRVPass: boolean;
  condSign: boolean; irvSign: boolean;
  methodSplit: boolean;
  score: number;
};

export function LegislationDivergences({ houseVotes, senateVotes, election, pipeline, wyoming = 'double',
                                         system = 'stv', voteModel = 'free', candidateVotes = [], houseSeats = {},
                                         senateSeatsCond = {}, senateSeatsIRV = {} }: Props) {
  const whipped = voteModel === 'whipped';
  const condWinner = election.condorcetWinner;
  const irvWinner  = election.irvWinner;

  const condCombo = `${pipeline}+condorcet`;
  const irvCombo  = `${pipeline}+irv`;
  const isFD = pipeline === 'factorDev';
  const condPresParty = election.condorcetWinner.split('_')[0];
  const irvPresParty  = election.irvWinner.split('_')[0];

  const SENATE_PROB: Record<string, keyof VoteModelRow> = {
    'rawMulti+condorcet':  'condRawMultiProbPass',
    'rawMulti+irv':        'irvRawMultiProbPass',
    'factorDev+condorcet': 'condFDProbPass',
    'factorDev+irv':       'irvFDProbPass',
  };


  const HOUSE_PROB = houseProbField(system, pipeline, wyoming);

  const houseByVar = useMemo(
    () => Object.fromEntries(houseVotes.map(r => [r.variable, r])),
    [houseVotes],
  );
  const candByVar = useMemo(
    () => Object.fromEntries(candidateVotes.map(r => [r.variable, r])),
    [candidateVotes],
  );

  const divergentBills = useMemo(() => {
    return senateVotes
      .map(row => {
        const hr = houseByVar[row.variable];

        if (whipped) {
          const cb = candByVar[row.variable];
          if (!cb) return null;
          const housePass = blocOutcome(cb, houseSeats).pass;
          const senateCondPass = blocOutcome(cb, senateSeatsCond).pass;
          const senateIRVPass  = blocOutcome(cb, senateSeatsIRV).pass;
          const condSign = presSigns(cb, condWinner);
          const irvSign  = presSigns(cb, irvWinner);

          const methodSplit = senateCondPass !== senateIRVPass;
          const houseSenateSplit = housePass !== senateCondPass || housePass !== senateIRVPass;
          const presSplit = condSign !== irvSign;
          if (!methodSplit && !houseSenateSplit && !presSplit) return null;

          const score = (methodSplit ? 3 : 0) + (houseSenateSplit ? 2 : 0) + (presSplit ? 1 : 0);
          return {
            row, houseLabel: '', senateCondLabel: '', senateIRVLabel: '',
            condPresPct: undefined, irvPresPct: undefined,
            housePass, senateCondPass, senateIRVPass, condSign, irvSign, methodSplit, score,
          } as Row;
        }

        const houseLabel     = getBayesianLabel([hr?.[HOUSE_PROB] as number | undefined]);
        const senateCondLabel = getBayesianLabel([row[SENATE_PROB[condCombo]] as number | undefined]);
        const senateIRVLabel  = getBayesianLabel([row[SENATE_PROB[irvCombo]] as number | undefined]);
        // See VoteModelRow.presSignsByParty: the party-line side must key on the president this
        // panel displays, not on the fixed columns, which carry the full-depth tree's winners.
        const condPresSign    = isFD ? (row[FD_SIGN[condCombo]] as string | undefined) : row.presSignsByParty?.[condPresParty];
        const irvPresSign     = isFD ? (row[FD_SIGN[irvCombo]]  as string | undefined) : row.presSignsByParty?.[irvPresParty];
        const condPresPct     = isFD ? (row[FD_PCT[condCombo]]  as number | undefined) : row.presPctByParty?.[condPresParty];
        const irvPresPct      = isFD ? (row[FD_PCT[irvCombo]]   as number | undefined) : row.presPctByParty?.[irvPresParty];

        const hDir     = getDirection(houseLabel);
        const sCondDir = getDirection(senateCondLabel);
        const sIRVDir  = getDirection(senateIRVLabel);

        const methodSplit = sCondDir !== 'uncertain' && sIRVDir !== 'uncertain' && sCondDir !== sIRVDir;
        const houseSenateSplit =
          (hDir !== 'uncertain' && sCondDir !== 'uncertain' && hDir !== sCondDir) ||
          (hDir !== 'uncertain' && sIRVDir !== 'uncertain' && hDir !== sIRVDir);
        const presSplit = !!(condPresSign && irvPresSign && condPresSign !== irvPresSign);

        if (!methodSplit && !houseSenateSplit && !presSplit) return null;

        const score = (methodSplit ? 3 : 0) + (houseSenateSplit ? 2 : 0) + (presSplit ? 1 : 0);
        return {
          row, houseLabel, senateCondLabel, senateIRVLabel, condPresPct, irvPresPct,
          housePass: false, senateCondPass: false, senateIRVPass: false, condSign: false, irvSign: false,
          methodSplit, score,
        } as Row;
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score) as Row[];
  }, [senateVotes, houseByVar, candByVar, condCombo, irvCombo, HOUSE_PROB, whipped, houseSeats, senateSeatsCond, senateSeatsIRV, condWinner, irvWinner, isFD, condPresParty, irvPresParty]);

  if (divergentBills.length === 0) {
    return (
      <Card className="border-green-200 px-4 py-3">
        <span className="text-sm text-green-700">No method divergences found. Condorcet and IRV produce the same legislative outcomes.</span>
      </Card>
    );
  }

  // The candidate field only needs naming when there are two of them to tell apart.
  const label = SHOW_CROSSOVER ? ` (${pipeline === 'rawMulti' ? 'Party-Line' : 'Crossover'})` : '';
  const condColor = getBlendColor(condWinner);
  const irvColor = getBlendColor(irvWinner);
  const condParty = condWinner.split('_')[0];
  const irvParty = irvWinner.split('_')[0];
  // Grouped columns: House, then each method's (Senate + President) pair side by side.
  const COLS = 'md:grid-cols-[minmax(150px,1fr)_110px_110px_110px_110px_110px]';

  return (
    <Card className="border-amber-300 overflow-hidden">
      <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
        {/* CARD_HEADING's size, weight and case; amber instead of muted, since the colour is
            what marks this card as the warning. Not composed, so the colour can't lose a
            specificity race with text-muted-foreground. */}
        <h4 className="text-sm font-semibold text-amber-900 uppercase tracking-widest">
          Method Divergences{label} — {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} where IRV ≠ Condorcet
        </h4>
        <p className="text-xs text-amber-700 mt-0.5">
          Bills where the election method (Condorcet vs IRV) changes the Senate outcome, the president&apos;s veto decision, or creates a House–Senate split.
        </p>
      </div>

      {/* Two-tier header: House, then a Condorcet group (Senate + President) and an IRV group */}
      <div className={`hidden md:grid ${COLS} gap-x-1 px-4 pt-2 text-3xs font-bold uppercase tracking-widest`}>
        <div /><div />
        <div className="col-span-2 text-center border-l border-border/40" style={{ color: condColor }}>Condorcet</div>
        <div className="col-span-2 text-center border-l border-border/40" style={{ color: irvColor }}>IRV</div>
      </div>
      <div className={`hidden md:grid ${COLS} gap-x-1 px-4 pb-2 border-b border-border/50 ${FIELD_LABEL}`}>
        <div>Bill</div>
        <div className="text-center">House</div>
        <div className="text-center border-l border-border/40">Senate</div>
        <div className="text-center" style={{ color: condColor }}>{condParty} Pres</div>
        <div className="text-center border-l border-border/40">Senate</div>
        <div className="text-center" style={{ color: irvColor }}>{irvParty} Pres</div>
      </div>

      <div className="divide-y divide-slate-100">
        {divergentBills.map((d) => (
          <div
            key={d.row.variable}
            className={`flex flex-col md:grid ${COLS} gap-x-1 items-start md:items-center px-4 py-2.5 ${
              d.methodSplit ? 'bg-amber-50/40' : 'bg-white'
            }`}
          >
            <div className="min-w-0 mb-1 md:mb-0">
              <span className="text-sm text-foreground">{d.row.question}</span>
              <span className="text-xs text-muted-foreground ml-2">{d.row.domain}</span>
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">House</span>
              {whipped ? <WhippedBadge pass={d.housePass} kind="pass" /> : <VerdictBadge label={d.houseLabel} />}
            </div>
            {/* Condorcet group */}
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:border-l md:border-border/40">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">Senate (Condorcet)</span>
              {whipped ? <WhippedBadge pass={d.senateCondPass} kind="pass" /> : <VerdictBadge label={d.senateCondLabel} />}
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold uppercase tracking-wide" style={{ color: condColor }}>{condParty} Pres (Condorcet)</span>
              {whipped ? <WhippedBadge pass={d.condSign} kind="sign" /> : <SignBadge prob={d.condPresPct !== undefined ? d.condPresPct / 100 : undefined} />}
            </div>
            {/* IRV group */}
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:border-l md:border-border/40">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">Senate (IRV)</span>
              {whipped ? <WhippedBadge pass={d.senateIRVPass} kind="pass" /> : <VerdictBadge label={d.senateIRVLabel} />}
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold uppercase tracking-wide" style={{ color: irvColor }}>{irvParty} Pres (IRV)</span>
              {whipped ? <WhippedBadge pass={d.irvSign} kind="sign" /> : <SignBadge prob={d.irvPresPct !== undefined ? d.irvPresPct / 100 : undefined} />}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
