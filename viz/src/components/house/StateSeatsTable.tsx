import type { HouseStateEntry } from '../../types';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

// 2024 congressional apportionment (post-2020 census, 435 total)
const FPTP_SEATS: Record<string, number> = {
  AL: 7,  AK: 1,  AZ: 9,  AR: 4,  CA: 52, CO: 8,  CT: 5,  DE: 1,
  FL: 28, GA: 14, HI: 2,  ID: 2,  IL: 17, IN: 9,  IA: 4,  KS: 4,
  KY: 6,  LA: 6,  ME: 2,  MD: 8,  MA: 9,  MI: 13, MN: 8,  MS: 4,
  MO: 8,  MT: 2,  NE: 3,  NV: 4,  NH: 2,  NJ: 12, NM: 3,  NY: 26,
  NC: 14, ND: 1,  OH: 15, OK: 5,  OR: 6,  PA: 17, RI: 2,  SC: 7,
  SD: 1,  TN: 9,  TX: 38, UT: 4,  VT: 1,  VA: 11, WA: 10, WV: 2,
  WI: 8,  WY: 1,
};

interface Props {
  stateMap: Record<string, HouseStateEntry>;
  wyoming?: 'double' | 'triple';
}

export function StateSeatsTable({ stateMap, wyoming = 'double' }: Props) {
  const rows = Object.values(stateMap)
    .map(entry => ({
      abbr:  entry.stateAbbr,
      stv:   entry.totalSeats,
      fptp:  FPTP_SEATS[entry.stateAbbr] ?? 0,
      delta: entry.totalSeats - (FPTP_SEATS[entry.stateAbbr] ?? 0),
    }))
    .sort((a, b) => a.abbr.localeCompare(b.abbr));

  const stvTotal  = rows.reduce((s, r) => s + r.stv, 0);
  const fptpTotal = rows.reduce((s, r) => s + r.fptp, 0);

  const half  = Math.ceil(rows.length / 2);
  const left  = rows.slice(0, half);
  const right = rows.slice(half);

  const renderRows = (data: typeof rows) =>
    data.map(({ abbr, stv, fptp, delta }) => (
      <TableRow key={abbr}>
        <TableCell className="py-1 pr-2 text-xs font-semibold text-foreground w-8">{abbr}</TableCell>
        <TableCell className="py-1 px-2 text-xs text-right tabular-nums text-muted-foreground">{fptp}</TableCell>
        <TableCell className="py-1 px-2 text-xs text-right tabular-nums font-medium text-foreground">{stv}</TableCell>
        <TableCell className="py-1 pl-2 text-xs text-right tabular-nums font-bold text-emerald-600">+{delta}</TableCell>
      </TableRow>
    ));

  const ColHead = () => (
    <TableHeader>
      <TableRow>
        <TableHead className="pb-1.5 pr-2 text-xs text-muted-foreground text-left">State</TableHead>
        <TableHead className="pb-1.5 px-2 text-xs text-muted-foreground text-right">Now</TableHead>
        <TableHead className="pb-1.5 px-2 text-xs text-muted-foreground text-right">STV</TableHead>
        <TableHead className="pb-1.5 pl-2 text-xs text-muted-foreground text-right">Gain</TableHead>
      </TableRow>
    </TableHeader>
  );

  return (
    <div>
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Seats per State: STV vs Current
      </h3>
      <p className="text-xs text-muted-foreground mb-3">
        Now = 2024 FPTP apportionment ({fptpTotal} total). STV = simulated proportional districts ({stvTotal} total).
        Every state gains seats because multi-member STV targets one seat per ~{wyoming === 'triple' ? '192k' : '380k'} residents.
      </p>
      <div className="grid grid-cols-2 gap-x-8">
        <Table>
          <ColHead />
          <TableBody>{renderRows(left)}</TableBody>
        </Table>
        <Table>
          <ColHead />
          <TableBody>{renderRows(right)}</TableBody>
        </Table>
      </div>
    </div>
  );
}
