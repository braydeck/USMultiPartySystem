import { useState, useMemo } from 'react';
import { PARTY_COLORS, F5_ORDER, FACTOR_LABELS } from '../../constants/parties';
import { Button } from '@/components/ui/button';

interface Candidate {
  code: string;
  party: string;
  axis: string;
  direction: string;
  F1: number; F2: number; F3: number; F4: number; F5: number;
}

interface ClusterSpread {
  party: string;
  n: number;
  [key: string]: string | number;
}

interface Props {
  candidates: Candidate[];
  fdSeats?: Record<string, number>;
  clusterSpreads?: ClusterSpread[];
}

const FACTORS = ['F1', 'F2', 'F3', 'F4', 'F5'] as const;
type Factor = typeof FACTORS[number];

const AXIS_LABEL: Record<string, string> = {
  so: 'SO', ae: 'AE', pc: 'PC', rt: 'RT', base: '',
};

const W = 600, H = 480, PAD = 50;

export function VariantConstellationChart({ candidates, fdSeats, clusterSpreads }: Props) {
  const [xAxis, setXAxis] = useState<Factor>('F5');
  const [yAxis, setYAxis] = useState<Factor>('F1');
  const [enabledParties, setEnabledParties] = useState<Set<string>>(new Set(F5_ORDER));
  const [showVariants, setShowVariants] = useState(true);
  const [showEffective, setShowEffective] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  const getVal = (c: Candidate, f: Factor) => {
    if (showEffective && c.axis !== 'base') {
      const effKey = `eff_${f}`;
      const effVal = (c as unknown as Record<string, number>)[effKey];
      if (effVal !== undefined) return effVal;
    }
    return (c as unknown as Record<string, number>)[f];
  };

  const visible = useMemo(() =>
    candidates.filter(c =>
      enabledParties.has(c.party) && (showVariants || c.axis === 'base')
    ),
    [candidates, enabledParties, showVariants]
  );

  const xVals = visible.map(c => getVal(c, xAxis));
  const yVals = visible.map(c => getVal(c, yAxis));
  const xMin = Math.min(...xVals, -1), xMax = Math.max(...xVals, 1);
  const yMin = Math.min(...yVals, -1), yMax = Math.max(...yVals, 1);

  const sx = (v: number) => PAD + (v - xMin) / (xMax - xMin) * (W - 2 * PAD);
  const sy = (v: number) => H - PAD - (v - yMin) / (yMax - yMin) * (H - 2 * PAD);

  const toggleParty = (p: string) => {
    const next = new Set(enabledParties);
    if (next.has(p)) next.delete(p); else next.add(p);
    setEnabledParties(next);
  };

  return (
    <div>
      {/* Axis selectors */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">X:</span>
          {FACTORS.map(f => (
            <Button key={f} onClick={() => setXAxis(f)}
              variant={xAxis === f ? 'default' : 'secondary'}
              size="sm" className="h-6 px-2">
              {f}
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">Y:</span>
          {FACTORS.map(f => (
            <Button key={f} onClick={() => setYAxis(f)}
              variant={yAxis === f ? 'default' : 'secondary'}
              size="sm" className="h-6 px-2">
              {f}
            </Button>
          ))}
        </div>
        <Button onClick={() => setShowVariants(!showVariants)}
          variant={showVariants ? 'default' : 'secondary'}
          size="sm" className="h-6">
          {showVariants ? 'Variants ON' : 'Variants OFF'}
        </Button>
        <Button onClick={() => setShowEffective(!showEffective)}
          variant={showEffective ? 'default' : 'secondary'}
          size="sm" className="h-6"
          title="Show covariance-adjusted positions: where variants effectively attract voters, accounting for factor correlations">
          {showEffective ? 'Effective Pos' : 'Raw Pos'}
        </Button>
      </div>

      {/* Party toggles */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {F5_ORDER.map(p => {
          const on = enabledParties.has(p);
          const color = PARTY_COLORS[p];
          return (
            <button key={p} onClick={() => toggleParty(p)}
              className="text-xs px-2 py-0.5 rounded border transition-all"
              style={{
                borderColor: color,
                color: on ? 'white' : color,
                backgroundColor: on ? color : 'transparent',
                opacity: on ? 1 : 0.4,
              }}>
              {p}
            </button>
          );
        })}
      </div>

      {/* Tooltip */}
      {hovered && (
        <div className="text-sm text-foreground bg-white border border-border rounded px-3 py-1.5 shadow-sm mb-2 inline-block">
          {hovered}{fdSeats && fdSeats[hovered] ? ` — ${fdSeats[hovered]} seats` : ''}
        </div>
      )}

      {/* Scatter */}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 500 }}>
        {/* Grid */}
        <line x1={PAD} x2={W - PAD} y1={sy(0)} y2={sy(0)} stroke="#e2e8f0" strokeWidth={1} />
        <line x1={sx(0)} x2={sx(0)} y1={PAD} y2={H - PAD} stroke="#e2e8f0" strokeWidth={1} />

        {/* Axis labels */}
        <text x={W / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="#64748b">
          {xAxis} · {FACTOR_LABELS[xAxis]}
        </text>
        <text x={12} y={H / 2} textAnchor="middle" fontSize={11} fill="#64748b"
          transform={`rotate(-90, 12, ${H / 2})`}>
          {yAxis} · {FACTOR_LABELS[yAxis]}
        </text>

        {/* Voter penumbra — 1.5σ ellipses behind everything */}
        {clusterSpreads && clusterSpreads.filter(cs => enabledParties.has(cs.party)).map(cs => {
          const color = PARTY_COLORS[cs.party] ?? '#6b7280';
          const mx = Number(cs[`mean_${xAxis}`] ?? 0);
          const my = Number(cs[`mean_${yAxis}`] ?? 0);
          const sdx = Number(cs[`sd_${xAxis}`] ?? 0);
          const sdy = Number(cs[`sd_${yAxis}`] ?? 0);
          const cov = Number(cs[`cov_${xAxis}_${yAxis}`] ?? cs[`cov_${yAxis}_${xAxis}`] ?? 0);

          // Ellipse radii and rotation from 2x2 covariance
          const a = sdx * sdx, b = cov, d = sdy * sdy;
          const trace = a + d;
          const det = a * d - b * b;
          const disc = Math.sqrt(Math.max(0, trace * trace / 4 - det));
          const lambda1 = trace / 2 + disc;
          const lambda2 = Math.max(0.001, trace / 2 - disc);
          const angle = b !== 0 ? Math.atan2(lambda1 - a, b) * (180 / Math.PI) : 0;

          const SIGMA_SCALE = 1.5;
          const rx = Math.sqrt(lambda1) * SIGMA_SCALE / (xMax - xMin) * (W - 2 * PAD);
          const ry = Math.sqrt(lambda2) * SIGMA_SCALE / (yMax - yMin) * (H - 2 * PAD);

          return (
            <ellipse
              key={`cloud-${cs.party}`}
              cx={sx(mx)} cy={sy(my)}
              rx={rx} ry={ry}
              transform={`rotate(${-angle}, ${sx(mx)}, ${sy(my)})`}
              fill={color} fillOpacity={0.08}
              stroke={color} strokeOpacity={0.2} strokeWidth={1}
            />
          );
        })}

        {/* Lines connecting variants to base */}
        {showVariants && visible.filter(c => c.axis !== 'base').map(c => {
          const base = candidates.find(b => b.party === c.party && b.axis === 'base');
          if (!base) return null;
          const cx = getVal(c, xAxis);
          const cy = getVal(c, yAxis);
          const bx = getVal(base, xAxis);
          const by = getVal(base, yAxis);
          return (
            <line key={`line-${c.code}`}
              x1={sx(bx)} y1={sy(by)} x2={sx(cx)} y2={sy(cy)}
              stroke={PARTY_COLORS[c.party] ?? '#6b7280'} strokeWidth={0.8} strokeOpacity={0.25}
            />
          );
        })}

        {/* Points */}
        {visible.map(c => {
          const cx = getVal(c, xAxis);
          const cy = getVal(c, yAxis);
          const color = PARTY_COLORS[c.party] ?? '#6b7280';
          const isBase = c.axis === 'base';
          const seats = fdSeats?.[c.code] ?? 0;
          const r = isBase ? 8 : Math.max(3, Math.min(7, seats / 8));
          const isHovered = hovered === c.code;

          return (
            <g key={c.code}
              onMouseEnter={() => setHovered(c.code)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: 'pointer' }}>
              <circle cx={sx(cx)} cy={sy(cy)} r={isHovered ? r + 3 : r}
                fill={color} fillOpacity={isBase ? 0.9 : 0.7}
                stroke={isBase ? '#1e293b' : color}
                strokeWidth={isBase ? 1.5 : 0.8}
              />
              {/* Label for base */}
              {isBase && (
                <text x={sx(cx)} y={sy(cy) - r - 4} textAnchor="middle"
                  fontSize={10} fontWeight={700} fill={color}>
                  {c.party}
                </text>
              )}
              {/* Always-visible label for variants */}
              {!isBase && (
                <text x={sx(cx) + r + 3} y={sy(cy) + 3} textAnchor="start"
                  fontSize={8} fontWeight={isHovered ? 700 : 500}
                  fill={isHovered ? color : '#64748b'}
                  opacity={isHovered ? 1 : 0.7}>
                  {c.direction === 'hi' ? 'hi' : 'lo'} {AXIS_LABEL[c.axis]}{seats > 0 ? ` ${seats}s` : ''}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <p className="text-xs text-muted-foreground mt-1 text-center">
        Large circles = base party positions. Small circles = axis deviations (size ∝ seats won).
        Lines connect variants to their party base. Toggle parties and variants to explore overlap.
      </p>
    </div>
  );
}
