import { getBlendColor } from '../../constants/parties';
import type { CondorcetMatchup } from '../../types';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { FIELD_LABEL } from '../../constants/typography';

interface Props {
  matchups: CondorcetMatchup[];
  condorcetWinner: string;
}

export function CondorcetTable({ matchups, condorcetWinner }: Props) {
  // Sort by lock_order (already sorted in data) or by aWinsPct descending
  const sorted = [...matchups].sort((a, b) => {
    // Put matchups involving the condorcet winner first
    const aInvolvesWinner = a.candidateA === condorcetWinner || a.candidateB === condorcetWinner;
    const bInvolvesWinner = b.candidateA === condorcetWinner || b.candidateB === condorcetWinner;
    if (aInvolvesWinner && !bInvolvesWinner) return -1;
    if (!aInvolvesWinner && bInvolvesWinner) return 1;
    return b.margin - a.margin;
  });

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <div className={FIELD_LABEL}>Condorcet Winner</div>
        <div
          className="text-sm font-bold px-3 py-1 rounded"
          style={{
            backgroundColor: getBlendColor(condorcetWinner) + '33',
            border: `1px solid ${getBlendColor(condorcetWinner)}88`,
            color: getBlendColor(condorcetWinner),
          }}
        >
          {condorcetWinner}
        </div>
        <div className="text-xs text-muted-foreground">beats all opponents head-to-head</div>
      </div>

      <Table className="text-xs">
        <TableHeader>
          <TableRow>
            <TableHead className="text-left">Candidate A</TableHead>
            <TableHead className="text-left">Candidate B</TableHead>
            <TableHead className="text-left">Winner</TableHead>
            <TableHead className="text-right">A wins %</TableHead>
            <TableHead className="text-right">Margin</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((m, i) => {
            const isWinnerRow = m.candidateA === condorcetWinner || m.candidateB === condorcetWinner;
            return (
              <TableRow
                key={i}
                className={isWinnerRow ? 'bg-slate-50' : ''}
              >
                <TableCell className="font-mono" style={{ color: getBlendColor(m.candidateA) }}>
                  {m.candidateA}
                </TableCell>
                <TableCell className="font-mono" style={{ color: getBlendColor(m.candidateB) }}>
                  {m.candidateB}
                </TableCell>
                <TableCell>
                  <span
                    className="font-bold px-2 py-0.5 rounded text-xs"
                    style={{
                      backgroundColor: getBlendColor(m.winner) + '33',
                      color: getBlendColor(m.winner),
                    }}
                  >
                    {m.winner}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-foreground">
                  {m.aWinsPct.toFixed(1)}%
                </TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {m.margin.toFixed(2)}pp
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
