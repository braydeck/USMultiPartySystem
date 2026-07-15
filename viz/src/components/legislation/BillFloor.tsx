import type { CandidateVoteRow, VoteModelRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { pLaw, verdict } from '../../lib/lawChain';

interface Props {
  bill: CandidateVoteRow;
  houseRow?: VoteModelRow;
  senateRow?: VoteModelRow;
  presParty: string;
  pivotal: string | null;
  houseField: { pass: string; ovr: string };
  senateField: { pass: keyof VoteModelRow; ovr: keyof VoteModelRow };
}

const num = (v: unknown): number => (typeof v === 'number' ? v : 0);
const pct = (v: number) => `${Math.round(v * 100)}%`;

function Step({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col items-center px-3 py-1.5 rounded bg-background border border-border min-w-[92px]">
      <span className="text-[15px] font-bold tabular-nums">{value}</span>
      <span className="text-[10px] text-muted-foreground text-center leading-tight">{label}</span>
    </div>
  );
}

export function BillFloor({ bill, houseRow, senateRow, presParty, pivotal, houseField, senateField }: Props) {
  const pHouse = num(houseRow?.[houseField.pass as keyof VoteModelRow]);
  const pSenate = num(senateRow?.[senateField.pass]);
  const pOverrideHouse = num(houseRow?.[houseField.ovr as keyof VoteModelRow]);
  const pOverrideSenate = num(senateRow?.[senateField.ovr]);
  const presV = bill.parties[presParty];
  const pSign = presV?.pYes ?? 0;
  const law = pLaw({ pHouse, pSenate, pSign, pOverrideHouse, pOverrideSenate });

  const diverging = F5_ORDER.map((p) => ({ p, v: bill.parties[p] })).filter((x) => x.v?.diverges);

  return (
    <div className="px-3 py-3 mb-1 rounded-b bg-muted/30 border-x border-b border-border space-y-3">
      {/* Party floor — every party as a vote pill */}
      <div className="flex flex-wrap gap-1.5">
        {F5_ORDER.map((p) => {
          const v = bill.parties[p];
          if (!v) return null;
          const yes = v.pYes >= 0.5;
          return (
            <span
              key={p}
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold"
              style={{
                backgroundColor: getPartyColor(p) + '22',
                color: getPartyColor(p),
                border: `1px solid ${getPartyColor(p)}${p === pivotal ? 'ff' : '55'}`,
                boxShadow: p === pivotal ? `0 0 0 1.5px ${getPartyColor(p)}66` : 'none',
              }}
              title={`${PARTY_NAMES[p]} · P(yes) ${pct(v.pYes)}${p === pivotal ? ' · pivotal' : ''}`}
            >
              {p} {yes ? '✓' : '✗'} {Math.round(v.pYes * 100)}
            </span>
          );
        })}
      </div>

      {/* Law chain */}
      <div className="flex flex-wrap items-center gap-1.5 text-muted-foreground">
        <Step label="House pass" value={pct(pHouse)} />
        <span className="text-lg">×</span>
        <Step label="Senate pass" value={pct(pSenate)} />
        <span className="text-lg">×</span>
        <div className="flex flex-col items-center px-3 py-1.5 rounded bg-background border border-border">
          <span className="text-[13px] font-bold">{pSign >= 0.5 ? 'signs' : 'vetoes'}</span>
          <span className="text-[10px] text-muted-foreground text-center leading-tight">
            {presParty} pres · sign {pct(pSign)}
            {pSign < 0.5 && pOverrideHouse * pOverrideSenate > 0.01 && (
              <> · override {pct(pOverrideHouse * pOverrideSenate)}</>
            )}
          </span>
        </div>
        <span className="text-lg">=</span>
        <div className="flex flex-col items-center px-3 py-1.5 rounded bg-foreground/5 border border-foreground/20">
          <span className="text-[16px] font-extrabold tabular-nums">{pct(law)}</span>
          <span className="text-[10px] uppercase tracking-wide">{verdict(law)} law</span>
        </div>
      </div>

      {diverging.length > 0 && (
        <div className="text-[11px] text-muted-foreground">
          <span className="font-semibold text-foreground">Ideology vs. stated:</span>{' '}
          {diverging.map(({ p, v }) => (
            <span key={p} className="mr-2">
              {p} votes {v!.delta! > 0 ? 'yes more' : 'no more'} than its factor position predicts ({v!.delta! > 0 ? '+' : ''}{v!.delta}pp).
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
