import { useMemo } from 'react';
import type { VoteModelRow, PresidentialElection } from '../../types';
import { getBlendColor } from '../../constants/parties';
import { getBayesianLabel, getDirection, VerdictBadge, SignBadge, type VerdictLabel } from './UnifiedBillTable';
import { Card } from '@/components/ui/card';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  election: PresidentialElection;
  pipeline: 'rawMulti' | 'factorDev';
  wyoming?: 'double' | 'triple';
}

export function LegislationDivergences({ houseVotes, senateVotes, election, pipeline, wyoming = 'double' }: Props) {
  const condWinner = election.condorcetWinner;
  const irvWinner  = election.irvWinner;

  const condCombo = `${pipeline}+condorcet`;
  const irvCombo  = `${pipeline}+irv`;

  const SENATE_PROB: Record<string, keyof VoteModelRow> = {
    'rawMulti+condorcet':  'condRawMultiProbPass',
    'rawMulti+irv':        'irvRawMultiProbPass',
    'factorDev+condorcet': 'condFDProbPass',
    'factorDev+irv':       'irvFDProbPass',
  };

  const PRES_SIGN: Record<string, keyof VoteModelRow> = {
    'rawMulti+condorcet':  'presRawMultiCondSigns',
    'rawMulti+irv':        'presRawMultiIRVSigns',
    'factorDev+condorcet': 'presFDCondSigns',
    'factorDev+irv':       'presFDIRVSigns',
  };

  const PRES_PCT: Record<string, keyof VoteModelRow> = {
    'rawMulti+condorcet':  'presRawMultiCondPct',
    'rawMulti+irv':        'presRawMultiIRVPct',
    'factorDev+condorcet': 'presFDCondPct',
    'factorDev+irv':       'presFDIRVPct',
  };

  const HOUSE_PROB: keyof VoteModelRow = wyoming === 'triple'
    ? (pipeline === 'rawMulti' ? 'houseRawMultiTripleProbPass' : 'houseFDTripleProbPass')
    : (pipeline === 'rawMulti' ? 'houseRawMultiProbPass' : 'houseFDProbPass');

  const houseByVar = useMemo(
    () => Object.fromEntries(houseVotes.map(r => [r.variable, r])),
    [houseVotes],
  );

  const divergentBills = useMemo(() => {
    return senateVotes
      .map(row => {
        const hr = houseByVar[row.variable];

        const houseLabel     = getBayesianLabel([hr?.[HOUSE_PROB] as number | undefined]);
        const senateCondLabel = getBayesianLabel([row[SENATE_PROB[condCombo]] as number | undefined]);
        const senateIRVLabel  = getBayesianLabel([row[SENATE_PROB[irvCombo]] as number | undefined]);
        const condPresSign    = row[PRES_SIGN[condCombo]] as string | undefined;
        const irvPresSign     = row[PRES_SIGN[irvCombo]] as string | undefined;
        const condPresPct     = row[PRES_PCT[condCombo]] as number | undefined;
        const irvPresPct      = row[PRES_PCT[irvCombo]] as number | undefined;

        const hDir     = getDirection(houseLabel);
        const sCondDir = getDirection(senateCondLabel);
        const sIRVDir  = getDirection(senateIRVLabel);

        // IRV vs Condorcet divergence in senate
        const methodSplit = sCondDir !== 'uncertain' && sIRVDir !== 'uncertain' && sCondDir !== sIRVDir;
        // House vs either senate method
        const houseSenateSplit =
          (hDir !== 'uncertain' && sCondDir !== 'uncertain' && hDir !== sCondDir) ||
          (hDir !== 'uncertain' && sIRVDir !== 'uncertain' && hDir !== sIRVDir);
        // Presidential sign disagreement between methods
        const presSplit = !!(condPresSign && irvPresSign && condPresSign !== irvPresSign);

        if (!methodSplit && !houseSenateSplit && !presSplit) return null;

        const score = (methodSplit ? 3 : 0) + (houseSenateSplit ? 2 : 0) + (presSplit ? 1 : 0);
        return { row, houseLabel, senateCondLabel, senateIRVLabel, condPresSign, irvPresSign, condPresPct, irvPresPct, methodSplit, houseSenateSplit, presSplit, score };
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score) as {
        row: VoteModelRow;
        houseLabel: VerdictLabel | '';
        senateCondLabel: VerdictLabel | '';
        senateIRVLabel: VerdictLabel | '';
        condPresSign: string | undefined;
        irvPresSign: string | undefined;
        condPresPct: number | undefined;
        irvPresPct: number | undefined;
        methodSplit: boolean;
        houseSenateSplit: boolean;
        presSplit: boolean;
        score: number;
      }[];
  }, [senateVotes, houseByVar, condCombo, irvCombo, HOUSE_PROB]);

  if (divergentBills.length === 0) {
    return (
      <Card className="border-green-200 px-4 py-3">
        <span className="text-sm text-green-700">No method divergences found. Condorcet and IRV produce the same legislative outcomes.</span>
      </Card>
    );
  }

  const label = pipeline === 'rawMulti' ? 'Party-Line' : 'Crossover';
  const condColor = getBlendColor(condWinner);
  const irvColor = getBlendColor(irvWinner);
  const condParty = condWinner.split('_')[0];
  const irvParty = irvWinner.split('_')[0];
  // Grouped columns: House, then each method's (Senate + President) pair side by side.
  const COLS = 'md:grid-cols-[minmax(150px,1fr)_110px_110px_110px_110px_110px]';

  return (
    <Card className="border-amber-300 overflow-hidden">
      <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
        <h3 className="text-sm font-semibold text-amber-900">
          Method Divergences ({label}) — {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} where IRV ≠ Condorcet
        </h3>
        <p className="text-xs text-amber-700 mt-0.5">
          Bills where the election method (Condorcet vs IRV) changes the Senate outcome, the president&apos;s veto decision, or creates a House–Senate split.
        </p>
      </div>

      {/* Two-tier header: House, then a Condorcet group (Senate + President) and an IRV group */}
      <div className={`hidden md:grid ${COLS} gap-x-1 px-4 pt-2 text-[10px] font-bold uppercase tracking-widest`}>
        <div /><div />
        <div className="col-span-2 text-center border-l border-border/40" style={{ color: condColor }}>Condorcet</div>
        <div className="col-span-2 text-center border-l border-border/40" style={{ color: irvColor }}>IRV</div>
      </div>
      <div className={`hidden md:grid ${COLS} gap-x-1 px-4 pb-2 text-xs text-muted-foreground border-b border-border/50 uppercase tracking-widest`}>
        <div>Bill</div>
        <div className="text-center">House</div>
        <div className="text-center border-l border-border/40">Senate</div>
        <div className="text-center" style={{ color: condColor }}>{condParty} Pres</div>
        <div className="text-center border-l border-border/40">Senate</div>
        <div className="text-center" style={{ color: irvColor }}>{irvParty} Pres</div>
      </div>

      <div className="divide-y divide-slate-100">
        {divergentBills.map(({ row, houseLabel, senateCondLabel, senateIRVLabel, condPresPct, irvPresPct, methodSplit }) => (
          <div
            key={row.variable}
            className={`flex flex-col md:grid ${COLS} gap-x-1 items-start md:items-center px-4 py-2.5 ${
              methodSplit ? 'bg-amber-50/40' : 'bg-white'
            }`}
          >
            <div className="min-w-0 mb-1 md:mb-0">
              <span className="text-sm text-foreground">{row.question}</span>
              <span className="text-xs text-muted-foreground ml-2">{row.domain}</span>
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">House</span>
              <VerdictBadge label={houseLabel} />
            </div>
            {/* Condorcet group */}
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:border-l md:border-border/40">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">Senate (Condorcet)</span>
              <VerdictBadge label={senateCondLabel} />
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold uppercase tracking-wide" style={{ color: condColor }}>{condParty} Pres (Condorcet)</span>
              <SignBadge prob={condPresPct !== undefined ? condPresPct / 100 : undefined} />
            </div>
            {/* IRV group */}
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:border-l md:border-border/40">
              <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide">Senate (IRV)</span>
              <VerdictBadge label={senateIRVLabel} />
            </div>
            <div className="w-full flex items-center justify-between md:justify-center gap-3 mt-2 md:mt-0 border-t border-border/40 pt-2 md:border-0 md:pt-0">
              <span className="md:hidden text-xs font-semibold uppercase tracking-wide" style={{ color: irvColor }}>{irvParty} Pres (IRV)</span>
              <SignBadge prob={irvPresPct !== undefined ? irvPresPct / 100 : undefined} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
