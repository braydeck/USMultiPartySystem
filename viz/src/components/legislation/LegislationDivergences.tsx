import { useMemo } from 'react';
import type { VoteModelRow } from '../../types';
import { getBlendColor } from '../../constants/parties';

interface Props {
  senateVotes: VoteModelRow[];
}

const SCENARIOS = [
  { key: 'condMixed', label: 'Blended\nCondorcet', verdictField: 'condMixedVerdict' as keyof VoteModelRow, presField: 'presMixedCondSigns' as keyof VoteModelRow, presCode: 'SD/CON' },
  { key: 'irvMixed',  label: 'Blended\nIRV',       verdictField: 'irvMixedVerdict'  as keyof VoteModelRow, presField: 'presMixedSigns'     as keyof VoteModelRow, presCode: 'CON/SD' },
  { key: 'condPure',  label: 'Raw\nCondorcet',      verdictField: 'condPureVerdict'  as keyof VoteModelRow, presField: 'presPureSigns'       as keyof VoteModelRow, presCode: 'STY'    },
  { key: 'irvPure',   label: 'Raw\nIRV',            verdictField: 'irvPureVerdict'   as keyof VoteModelRow, presField: 'presPureSigns'       as keyof VoteModelRow, presCode: 'STY'    },
  { key: 'condLF',    label: 'LF\nCondorcet',       verdictField: 'condLFVerdict'    as keyof VoteModelRow, presField: 'presLFSigns'         as keyof VoteModelRow, presCode: 'STY_ctr'},
  { key: 'irvLF',     label: 'LF\nIRV',             verdictField: 'irvLFVerdict'     as keyof VoteModelRow, presField: 'presLFSigns'         as keyof VoteModelRow, presCode: 'STY_ctr'},
] as const;


function VerdictCell({ verdict }: { verdict: string | undefined }) {
  if (!verdict || verdict === '—') return <span className="text-slate-300 text-xs">—</span>;
  const cls =
    verdict === 'PASS'     ? 'bg-green-50 text-green-700 border-green-300' :
    verdict === 'FAIL'     ? 'bg-red-50 text-red-700 border-red-300' :
                             'bg-yellow-50 text-yellow-700 border-yellow-300';
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded border whitespace-nowrap ${cls}`}>
      {verdict}
    </span>
  );
}

function PresCell({ signs, code }: { signs: string | undefined; code: string }) {
  if (!signs || signs === '—') return <span className="text-slate-300 text-xs">—</span>;
  const color = getBlendColor(code);
  return (
    <span
      className="text-xs font-semibold px-1.5 py-0.5 rounded border whitespace-nowrap"
      style={
        signs === 'SIGN'
          ? { backgroundColor: color + '18', color, borderColor: color + '55' }
          : { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fca5a5' }
      }
    >
      {signs === 'SIGN' ? '✓' : '✗'} {code}
    </span>
  );
}

export function LegislationDivergences({ senateVotes }: Props) {
  const divergentBills = useMemo(() => {
    return senateVotes
      .map(row => {
        const verdicts = SCENARIOS.map(s => row[s.verdictField] as string | undefined);
        const unique = new Set(verdicts.filter(Boolean));
        const hasSplit = unique.size > 1 && unique.has('PASS') && unique.has('FAIL');

        const presSigns = SCENARIOS.map(s => row[s.presField] as string | undefined);
        const presUnique = new Set(presSigns.filter(Boolean));
        const presHasSplit = presUnique.size > 1;

        if (!hasSplit && !presHasSplit) return null;

        // Score: senate split is 2pts, pres split is 1pt, more disagreements = higher priority
        const senatePasses = verdicts.filter(v => v === 'PASS').length;
        const scenarioDiff = Math.abs(senatePasses - (SCENARIOS.length - senatePasses));
        const score = (hasSplit ? 2 : 0) + (presHasSplit ? 1 : 0) + (SCENARIOS.length - scenarioDiff);

        return { row, verdicts, presSigns, hasSplit, presHasSplit, score };
      })
      .filter(Boolean)
      .sort((a, b) => b!.score - a!.score) as NonNullable<ReturnType<typeof senateVotes['map']>[number]>[];
  }, [senateVotes]);

  if (divergentBills.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-amber-300 overflow-hidden">
      <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
        <h3 className="text-sm font-semibold text-amber-900">
          Scenario Divergences — {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different outcomes
        </h3>
        <p className="text-xs text-amber-700 mt-0.5">
          These bills pass under some scenarios but fail under others. Amber = senate split; pres column shows which presidents would sign.
        </p>
      </div>

      {/* Column headers */}
      <div className="hidden md:grid grid-cols-[1fr_repeat(6,_auto)_auto] gap-x-2 px-4 py-1.5 text-xs text-slate-500 border-b border-slate-100">
        <div>Bill</div>
        {SCENARIOS.map(s => (
          <div key={s.key} className="w-20 text-center whitespace-pre-line leading-tight">{s.label}</div>
        ))}
        <div className="w-24 text-center">Presidents</div>
      </div>

      <div className="divide-y divide-slate-100">
        {(divergentBills as unknown as { row: VoteModelRow; verdicts: (string|undefined)[]; presSigns: (string|undefined)[]; hasSplit: boolean; presHasSplit: boolean }[]).map(({ row, verdicts, presSigns, hasSplit }) => (
          <div
            key={row.variable}
            className={`flex flex-col md:grid md:grid-cols-[1fr_repeat(6,_auto)_auto] gap-x-2 items-start md:items-center px-4 py-2.5 ${
              hasSplit ? 'bg-amber-50/50' : 'bg-white'
            }`}
          >
            <div className="min-w-0 mb-1 md:mb-0">
              <span className="text-sm text-slate-800">{row.question}</span>
              <span className="text-xs text-slate-500 ml-2">{row.domain}</span>
            </div>
            {SCENARIOS.map((s, i) => (
              <div key={s.key} className="w-20 text-center">
                <VerdictCell verdict={verdicts[i]} />
              </div>
            ))}
            <div className="w-24 flex flex-wrap gap-1 justify-center">
              {/* Deduplicate: only show unique pres/sign combos */}
              {SCENARIOS.reduce<{ code: string; signs: string | undefined }[]>((acc, s, i) => {
                const signs = presSigns[i];
                if (!acc.find(x => x.code === s.presCode && x.signs === signs)) {
                  acc.push({ code: s.presCode, signs });
                }
                return acc;
              }, []).map(({ code, signs }) => (
                <PresCell key={code} signs={signs} code={code} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
