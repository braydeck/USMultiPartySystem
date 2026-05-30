import { useMemo } from 'react';
import type { VoteModelRow, PresidentialElection } from '../../types';
import { getBlendColor } from '../../constants/parties';
import { getBayesianLabel, getDirection, VerdictBadge, type VerdictLabel } from './UnifiedBillTable';
import { Card } from '@/components/ui/card';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  election: PresidentialElection;
  pipeline: 'rawMulti' | 'factorDev';
}

function PresCell({ signs, winner }: { signs: string | undefined; winner: string }) {
  if (!signs) return <span className="text-slate-300 text-xs">—</span>;
  const color = getBlendColor(winner);
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="text-xs font-semibold px-1.5 py-0.5 rounded border whitespace-nowrap"
        style={
          signs === 'SIGN'
            ? { backgroundColor: color + '18', color, borderColor: color + '55' }
            : { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fca5a5' }
        }
      >
        {signs === 'SIGN' ? '✓ Sign' : '✗ Veto'}
      </span>
      <span className="text-xs font-mono text-muted-foreground truncate max-w-[72px]" title={winner}>{winner}</span>
    </div>
  );
}

export function LegislationDivergences({ houseVotes, senateVotes, election, pipeline }: Props) {
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

  const HOUSE_PROB: keyof VoteModelRow = pipeline === 'rawMulti' ? 'houseRawMultiProbPass' : 'houseFDProbPass';

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
        return { row, houseLabel, senateCondLabel, senateIRVLabel, condPresSign, irvPresSign, methodSplit, houseSenateSplit, presSplit, score };
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score) as {
        row: VoteModelRow;
        houseLabel: VerdictLabel | '';
        senateCondLabel: VerdictLabel | '';
        senateIRVLabel: VerdictLabel | '';
        condPresSign: string | undefined;
        irvPresSign: string | undefined;
        methodSplit: boolean;
        houseSenateSplit: boolean;
        presSplit: boolean;
        score: number;
      }[];
  }, [senateVotes, houseByVar, condCombo, irvCombo, HOUSE_PROB]);

  if (divergentBills.length === 0) {
    return (
      <Card className="border-green-200 px-4 py-3">
        <span className="text-sm text-green-700">No method divergences found — Condorcet and IRV produce the same legislative outcomes.</span>
      </Card>
    );
  }

  const label = pipeline === 'rawMulti' ? 'Raw Multi' : 'Factor Dev';

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

      <div className="hidden md:grid grid-cols-[1fr_90px_90px_90px_60px_60px] gap-x-2 px-4 py-2 text-xs text-muted-foreground border-b border-border/50 uppercase tracking-widest">
        <div>Bill</div>
        <div className="text-center">House</div>
        <div className="text-center">Senate Cond</div>
        <div className="text-center">Senate IRV</div>
        <div className="text-center" style={{ color: getBlendColor(condWinner) }}>Cond Pres</div>
        <div className="text-center" style={{ color: getBlendColor(irvWinner) }}>IRV Pres</div>
      </div>

      <div className="divide-y divide-slate-100">
        {divergentBills.map(({ row, houseLabel, senateCondLabel, senateIRVLabel, condPresSign, irvPresSign, methodSplit }) => (
          <div
            key={row.variable}
            className={`flex flex-col md:grid md:grid-cols-[1fr_90px_90px_90px_60px_60px] gap-x-2 items-start md:items-center px-4 py-2.5 ${
              methodSplit ? 'bg-amber-50/40' : 'bg-white'
            }`}
          >
            <div className="min-w-0 mb-1 md:mb-0">
              <span className="text-sm text-foreground">{row.question}</span>
              <span className="text-xs text-muted-foreground ml-2">{row.domain}</span>
            </div>
            <div className="flex justify-center"><VerdictBadge label={houseLabel} /></div>
            <div className="flex justify-center"><VerdictBadge label={senateCondLabel} /></div>
            <div className="flex justify-center"><VerdictBadge label={senateIRVLabel} /></div>
            <div className="flex justify-center"><PresCell signs={condPresSign} winner={condWinner} /></div>
            <div className="flex justify-center"><PresCell signs={irvPresSign} winner={irvWinner} /></div>
          </div>
        ))}
      </div>
    </Card>
  );
}
