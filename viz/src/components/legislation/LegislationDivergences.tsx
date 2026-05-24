import { useMemo } from 'react';
import type { VoteModelRow, PresidentialElection } from '../../types';
import { getBlendColor } from '../../constants/parties';
import { getBayesianLabel, getDirection, VerdictBadge, VERDICT_STYLE, type VerdictLabel } from './UnifiedBillTable';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  senateMethod: 'condorcet' | 'irv';
}

const SENATE_PROB_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'condRawMultiProbPass',
  'rawMulti+irv':        'irvRawMultiProbPass',
  'factorDev+condorcet': 'condFDProbPass',
  'factorDev+irv':       'irvFDProbPass',
};

const PRES_SIGN_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'presRawMultiCondSigns',
  'rawMulti+irv':        'presRawMultiIRVSigns',
  'factorDev+condorcet': 'presFDCondSigns',
  'factorDev+irv':       'presFDIRVSigns',
};

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
        {signs === 'SIGN' ? '✓' : '✗'}
      </span>
      <span className="text-xs font-mono text-slate-400 truncate max-w-[72px]" title={winner}>{winner}</span>
    </div>
  );
}

export function LegislationDivergences({ houseVotes, senateVotes, fdElection, rawMultiElection, senateMethod }: Props) {
  const rmWinner = senateMethod === 'condorcet' ? rawMultiElection.condorcetWinner : rawMultiElection.irvWinner;
  const fdWinner = senateMethod === 'condorcet' ? fdElection.condorcetWinner       : fdElection.irvWinner;

  const rmCombo = `rawMulti+${senateMethod}`;
  const fdCombo = `factorDev+${senateMethod}`;

  const houseByVar = useMemo(
    () => Object.fromEntries(houseVotes.map(r => [r.variable, r])),
    [houseVotes],
  );

  const divergentBills = useMemo(() => {
    return senateVotes
      .map(row => {
        const hr = houseByVar[row.variable];

        const houseRMLabel  = getBayesianLabel([hr?.houseRawMultiProbPass]);
        const houseFDLabel  = getBayesianLabel([hr?.houseFDProbPass]);
        const senateRMLabel = getBayesianLabel([row[SENATE_PROB_FIELD[rmCombo]] as number | undefined]);
        const senateFDLabel = getBayesianLabel([row[SENATE_PROB_FIELD[fdCombo]] as number | undefined]);
        const rmPresSign    = row[PRES_SIGN_FIELD[rmCombo]] as string | undefined;
        const fdPresSign    = row[PRES_SIGN_FIELD[fdCombo]] as string | undefined;

        const hRMDir  = getDirection(houseRMLabel);
        const hFDDir  = getDirection(houseFDLabel);
        const sRMDir  = getDirection(senateRMLabel);
        const sFDDir  = getDirection(senateFDLabel);

        const senateSplit  = sRMDir !== 'uncertain' && sFDDir !== 'uncertain' && sRMDir !== sFDDir;
        const houseSplit   = hRMDir !== 'uncertain' && hFDDir !== 'uncertain' && hRMDir !== hFDDir;
        const houseSenateSplit =
          (hRMDir !== 'uncertain' && sRMDir !== 'uncertain' && hRMDir !== sRMDir) ||
          (hFDDir !== 'uncertain' && sFDDir !== 'uncertain' && hFDDir !== sFDDir);
        const presSplit    = !!(rmPresSign && fdPresSign && rmPresSign !== fdPresSign);

        if (!senateSplit && !houseSplit && !houseSenateSplit && !presSplit) return null;

        const score = (senateSplit ? 3 : 0) + (houseSenateSplit ? 2 : 0) + (houseSplit ? 1 : 0) + (presSplit ? 1 : 0);
        return { row, houseRMLabel, houseFDLabel, senateRMLabel, senateFDLabel, rmPresSign, fdPresSign, senateSplit, houseSplit, houseSenateSplit, score };
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score) as {
        row: VoteModelRow;
        houseRMLabel: VerdictLabel | '';
        houseFDLabel: VerdictLabel | '';
        senateRMLabel: VerdictLabel | '';
        senateFDLabel: VerdictLabel | '';
        rmPresSign: string | undefined;
        fdPresSign: string | undefined;
        senateSplit: boolean;
        houseSplit: boolean;
        houseSenateSplit: boolean;
        score: number;
      }[];
  }, [senateVotes, houseByVar, rmCombo, fdCombo]);

  if (divergentBills.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-amber-300 overflow-hidden">
      <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
        <h3 className="text-sm font-semibold text-amber-900">
          Scenario Divergences — {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different outcomes
        </h3>
        <p className="text-xs text-amber-700 mt-0.5">
          Bills where House, Raw Multi, and Factor Dev point in different directions, or presidents disagree.
        </p>
      </div>

      <div className="hidden md:grid grid-cols-[1fr_100px_100px_100px_100px_56px_56px] gap-x-2 px-4 py-2 text-xs text-slate-500 border-b border-slate-100 uppercase tracking-widest">
        <div>Bill</div>
        <div className="text-center">House RM</div>
        <div className="text-center">House FD</div>
        <div className="text-center">Senate RM</div>
        <div className="text-center">Senate FD</div>
        <div className="text-center" style={{ color: getBlendColor(rmWinner) }} title={rmWinner}>RM Pres</div>
        <div className="text-center" style={{ color: getBlendColor(fdWinner) }} title={fdWinner}>FD Pres</div>
      </div>

      <div className="divide-y divide-slate-100">
        {divergentBills.map(({ row, houseRMLabel, houseFDLabel, senateRMLabel, senateFDLabel, rmPresSign, fdPresSign, senateSplit, houseSplit, houseSenateSplit }) => (
          <div
            key={row.variable}
            className={`flex flex-col md:grid md:grid-cols-[1fr_100px_100px_100px_100px_56px_56px] gap-x-2 items-start md:items-center px-4 py-2.5 ${
              senateSplit || houseSplit || houseSenateSplit ? 'bg-amber-50/40' : 'bg-white'
            }`}
          >
            <div className="min-w-0 mb-1 md:mb-0">
              <span className="text-sm text-slate-800">{row.question}</span>
              <span className="text-xs text-slate-400 ml-2">{row.domain}</span>
            </div>
            <div className="flex justify-center"><VerdictBadge label={houseRMLabel} /></div>
            <div className="flex justify-center"><VerdictBadge label={houseFDLabel} /></div>
            <div className="flex justify-center"><VerdictBadge label={senateRMLabel} /></div>
            <div className="flex justify-center"><VerdictBadge label={senateFDLabel} /></div>
            <div className="flex justify-center"><PresCell signs={rmPresSign} winner={rmWinner} /></div>
            <div className="flex justify-center"><PresCell signs={fdPresSign} winner={fdWinner} /></div>
          </div>
        ))}
      </div>
    </div>
  );
}
