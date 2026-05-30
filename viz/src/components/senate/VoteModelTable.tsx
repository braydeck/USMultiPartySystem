import { useMemo, useState } from 'react';
import type { VoteModelRow, SenateScenario } from '../../types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

interface Props {
  rows: VoteModelRow[];
  scenario: SenateScenario;
}

const SCENARIO_FIELDS: Record<SenateScenario, {
  prob: keyof VoteModelRow;
  verdict: keyof VoteModelRow;
  signs: keyof VoteModelRow;
}> = {
  condFD:       { prob: 'condFDProbPass',   verdict: 'condFDVerdict',   signs: 'presFDSigns'   },
  irvFD:        { prob: 'irvFDProbPass',    verdict: 'irvFDVerdict',    signs: 'presFDSigns'   },
  condRawMulti: { prob: 'condRawMultiProbPass', verdict: 'condRawMultiVerdict', signs: 'presRawMultiCondSigns' },
  irvRawMulti:  { prob: 'irvRawMultiProbPass',  verdict: 'irvRawMultiVerdict',  signs: 'presRawMultiIRVSigns'  },
};

function VerdictBadge({ verdict }: { verdict: string }) {
  const color =
    verdict === 'PASS' ? 'bg-green-50 text-green-700 border-green-300' :
    verdict === 'FAIL' ? 'bg-red-50 text-red-700 border-red-300' :
    'bg-yellow-50 text-yellow-700 border-yellow-300';
  return (
    <Badge variant="outline" className={color}>
      {verdict}
    </Badge>
  );
}

export function VoteModelTable({ rows, scenario }: Props) {
  const [domain, setDomain] = useState<string>('All');
  const domains = useMemo(() => {
    const d = Array.from(new Set(rows.map(r => r.domain))).sort();
    return ['All', ...d];
  }, [rows]);

  const filtered = domain === 'All' ? rows : rows.filter(r => r.domain === domain);
  const fields = SCENARIO_FIELDS[scenario];

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
        {domains.map(d => (
          <Button
            key={d}
            onClick={() => setDomain(d)}
            variant={domain === d ? 'default' : 'secondary'}
            size="sm"
          >
            {d}
          </Button>
        ))}
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-left">Bill</TableHead>
            <TableHead className="text-center whitespace-nowrap">Senate</TableHead>
            <TableHead className="text-center whitespace-nowrap">President</TableHead>
            <TableHead className="text-center whitespace-nowrap">Becomes Law?</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map(row => {
            const verdict = row[fields.verdict] as string | undefined;
            const signs   = row[fields.signs] as string | undefined;
            const becomesLaw = verdict === 'PASS' && signs === 'SIGN';
            const vetoed     = verdict === 'PASS' && signs === 'VETO';
            return (
              <TableRow
                key={row.variable}
                className={vetoed ? 'bg-amber-50' : ''}
              >
                <TableCell className="text-foreground">
                  <div>{row.question}</div>
                  <div className="text-xs text-muted-foreground">{row.domain}</div>
                </TableCell>
                <TableCell className="text-center">
                  {verdict ? <VerdictBadge verdict={verdict} /> : <span className="text-muted-foreground text-xs">—</span>}
                </TableCell>
                <TableCell className="text-center">
                  {signs ? (
                    <Badge variant="outline" className={
                      signs === 'SIGN'
                        ? 'bg-green-50 text-green-700 border-green-300'
                        : 'bg-red-50 text-red-700 border-red-300'
                    }>
                      {signs === 'SIGN' ? 'Signs' : 'Vetoes'}
                    </Badge>
                  ) : <span className="text-muted-foreground text-xs">—</span>}
                </TableCell>
                <TableCell className="text-center">
                  {verdict && signs ? (
                    <span className={`text-base ${becomesLaw ? 'text-green-600' : 'text-red-500'}`}>
                      {becomesLaw ? '✓' : '✗'}
                    </span>
                  ) : <span className="text-muted-foreground text-xs">—</span>}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
