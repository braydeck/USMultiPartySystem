import { useEffect, useMemo, useRef, useState } from 'react';
import type { ConstellationNode } from '../../types';
import { FACTOR_LABELS, FACTOR_POLES, PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import { CARD_HINT, CHART_FILL, CHART_TYPE } from '../../constants/typography';
import { PARTY_ELLIPSES, ELLIPSE_FACTORS, ellipseFromCov2 } from '../../lib/partyOverlap';
import { bamForZ } from '../../lib/bam';
import { Button } from '@/components/ui/button';

const W = 560, H = 460;
const FACTORS = ['F1', 'F2', 'F4', 'F5'] as const;
type Factor = typeof FACTORS[number];
const AXIS_WORD: Record<string, string> = { F1: 'Security', F2: 'Distrust', F4: 'Traditionalism', F5: 'Populism' };
const DEFAULT_VIEW = { yaw: -0.6, pitch: 0.42 };
// Pitch stays at or above level: from below, the floor and its shadows would sit on top of the
// parties instead of under them.
const PITCH_MIN = 0.05, PITCH_MAX = 1.4;
const PARTIES = F5_ORDER.filter(p => PARTY_ELLIPSES[p]);
const R2_HALF = 2 * Math.LN2;

type Vec3 = [number, number, number];
type Mat3 = [Vec3, Vec3, Vec3];

/** Camera rotation: turn about the vertical axis (yaw), then tilt toward the viewer (pitch). */
function rotation(yaw: number, pitch: number): Mat3 {
  const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  return [
    [cy, 0, sy],
    [sy * sp, cp, -cy * sp],
    [-sy * cp, sp, cy * cp],
  ];
}
const apply = (R: Mat3, v: Vec3): Vec3 =>
  [0, 1, 2].map(r => R[r][0] * v[0] + R[r][1] * v[1] + R[r][2] * v[2]) as Vec3;

/** Screen covariance A S Aᵀ for a 2×n map A (screen rows of the rotation) and n×n covariance S. */
function projectCov(A: number[][], S: number[][]) {
  const AS = A.map(row => S[0].map((_, k) => row.reduce((acc, a, m) => acc + a * S[m][k], 0)));
  return AS.map(row => A.map(col => row.reduce((acc, v, m) => acc + v * col[m], 0)));
}

/** Largest eigenvalue of a small symmetric matrix, by power iteration. */
function maxEig(S: number[][]) {
  let v = S.map(() => 1), l = 0;
  for (let it = 0; it < 40; it++) {
    const w = S.map(row => row.reduce((acc, x, k) => acc + x * v[k], 0));
    l = Math.hypot(...w) || 1e-12; v = w.map(x => x / l);
  }
  return l;
}

/**
 * Three factors as axes and any factor as colour; colouring by the one left off the axes puts all
 * four interpretable factors on screen at once. Each party is its 50% ellipsoid from the
 * within-party covariance. Under orthographic projection an ellipsoid's outline is exactly the ellipse of its projected
 * covariance R Σ Rᵀ, and its shadow on the floor is the ellipse of the two floor axes' block, so
 * every frame is drawn without approximation. Shading, floor shadows and fading with distance
 * carry the depth that a flat outline loses.
 */
export function Constellation3D({ nodes, isDim }: {
  /** Supplies the current-party markers (DEM/IND/REP), which have positions but no covariance. */
  nodes: ConstellationNode[];
  isDim: (id: string) => boolean;
}) {
  const [axes, setAxes] = useState<[Factor, Factor, Factor]>(['F5', 'F1', 'F4']);
  const fourth = FACTORS.find(f => !axes.includes(f))!;
  const [colorMode, setColorMode] = useState<'party' | Factor>('F2');
  const [view, setView] = useState(DEFAULT_VIEW);
  const [spin, setSpin] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const drag = useRef<{ x: number; y: number; yaw: number; pitch: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    if (!spin) return;
    let raf = 0, last = performance.now();
    const tick = (t: number) => {
      const dt = t - last; last = t;
      if (!drag.current) setView(v => ({ ...v, yaw: v.yaw + dt * 0.0004 }));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [spin]);

  // Scene geometry that depends only on the chosen axes: where the floor sits, how far its grid
  // runs, and a radius that contains everything, so the frame never clips mid-turn.
  const scene = useMemo(() => {
    const ix = axes.map(f => ELLIPSE_FACTORS.indexOf(f));
    let bottom = 0, reach = 0, sphere = 0;
    for (const p of PARTIES) {
      const { mean, cov } = PARTY_ELLIPSES[p];
      const c = ix.map(i => mean[i]);
      const S = ix.map(i => ix.map(j => cov[i][j]));
      bottom = Math.min(bottom, c[1] - Math.sqrt(R2_HALF * S[1][1]));
      reach = Math.max(reach,
        Math.abs(c[0]) + Math.sqrt(R2_HALF * S[0][0]), Math.abs(c[2]) + Math.sqrt(R2_HALF * S[2][2]));
      sphere = Math.max(sphere, Math.hypot(...c) + Math.sqrt(R2_HALF * maxEig(S)));
    }
    const floorY = bottom - 0.2;
    const grid = Math.round((reach + 0.15) * 4) / 4;
    const radius = Math.max(sphere, Math.hypot(grid, floorY, grid));
    return { ix, floorY, grid, radius };
  }, [axes]);
  const { ix, floorY, grid, radius } = scene;

  // Zoom and vertical offset that fit everything on screen across a full turn at this tilt, so
  // spinning never rescales the scene but the parties still fill the frame.
  const fit = useMemo(() => {
    let xMax = 0, yMin = Infinity, yMax = -Infinity;
    const yTop = Math.max(-floorY, 1.5), half = grid + 0.4;
    for (let s = 0; s < 36; s++) {
      const Rs = rotation((s / 36) * 2 * Math.PI, view.pitch);
      const rows = [Rs[0], Rs[1]];
      const pts: Vec3[] = [[-half, floorY, -half], [half, floorY, -half], [half, floorY, half], [-half, floorY, half], [0, yTop, 0]];
      for (const v of pts) {
        const q = apply(Rs, v);
        xMax = Math.max(xMax, Math.abs(q[0])); yMin = Math.min(yMin, q[1]); yMax = Math.max(yMax, q[1]);
      }
      for (const p of PARTIES) {
        const { mean, cov } = PARTY_ELLIPSES[p];
        const c: Vec3 = [mean[ix[0]], mean[ix[1]], mean[ix[2]]];
        const P = projectCov(rows, ix.map(i => ix.map(j => cov[i][j])));
        const q = apply(Rs, c), hx = Math.sqrt(R2_HALF * P[0][0]), hy = Math.sqrt(R2_HALF * P[1][1]);
        xMax = Math.max(xMax, Math.abs(q[0]) + hx); yMin = Math.min(yMin, q[1] - hy); yMax = Math.max(yMax, q[1] + hy);
      }
    }
    const MARGIN = 26;
    const scale = Math.min((W / 2 - MARGIN) / xMax, (H - 2 * MARGIN) / (yMax - yMin));
    return { scale, yMid: (yMax + yMin) / 2 };
  }, [ix, floorY, grid, view.pitch]);

  const px = fit.scale;
  const R = rotation(view.yaw, view.pitch);
  const project = (v: Vec3) => {
    const q = apply(R, v);
    return { x: W / 2 + q[0] * px, y: H / 2 - (q[1] - fit.yMid) * px, depth: q[2] };
  };
  // 1 at the front of the scene, 0 at the back. Drives the fade that reads as distance.
  const nearness = (depth: number) => Math.max(0, Math.min(1, (depth + radius) / (2 * radius)));
  const screenRows = [R[0], R[1]];
  const floorMap = [[R[0][0], R[0][2]], [R[1][0], R[1][2]]];

  const ellipsoids = PARTIES.map(p => {
    const { mean, cov } = PARTY_ELLIPSES[p];
    const c: Vec3 = [mean[ix[0]], mean[ix[1]], mean[ix[2]]];
    const S = ix.map(i => ix.map(j => cov[i][j]));
    const P = projectCov(screenRows, S);
    const e = ellipseFromCov2(P[0][0], P[0][1], P[1][1]);
    const Sf = [[S[0][0], S[0][2]], [S[2][0], S[2][2]]];
    const Pf = projectCov(floorMap, Sf);
    const shadow = ellipseFromCov2(Pf[0][0], Pf[0][1], Pf[1][1]);
    const fourthZ = mean[ELLIPSE_FACTORS.indexOf(fourth)];
    const colorZ = colorMode === 'party' ? 0 : mean[ELLIPSE_FACTORS.indexOf(colorMode)];
    return { p, at: project(c), foot: project([c[0], floorY, c[2]]), e, shadow, fourthZ, colorZ };
  }).sort((a, b) => a.at.depth - b.at.depth);

  const currentMarkers = nodes
    .filter(n => !PARTY_ELLIPSES[n.id])
    .map(n => {
      const r = n as unknown as Record<string, number>;
      const v: Vec3 = [r[axes[0]], r[axes[1]], r[axes[2]]];
      return { id: n.id, at: project(v) };
    });

  const gridSteps = [-grid, ...Array.from({ length: 2 * Math.floor(grid) + 1 }, (_, i) => i - Math.floor(grid)), grid]
    .filter((t, i, a) => a.indexOf(t) === i);
  const gridLines = gridSteps.flatMap(t => [
    [project([t, floorY, -grid]), project([t, floorY, grid])],
    [project([-grid, floorY, t]), project([grid, floorY, t])],
  ]);
  const floorCorners = [[-grid, -grid], [grid, -grid], [grid, grid], [-grid, grid]]
    .map(([x, z]) => project([x, floorY, z]));

  const unit = (k: number, t: number): Vec3 => { const v: Vec3 = [0, 0, 0]; v[k] = t; return v; };
  const axisLen = (k: number) => (k === 1 ? Math.max(-floorY, 1.5) : grid + 0.4);
  const tickVals = [-2, -1, 1, 2];
  const axisEnds = axes.map((f, k) => {
    const len = axisLen(k);
    const lo = project(unit(k, k === 1 ? floorY : -len)), hi = project(unit(k, len));
    // An axis pointing at the viewer collapses to a short stub; its pole labels would sit on top
    // of each other and of the other axes, so they are dropped until it turns back out.
    const showLabels = Math.hypot(hi.x - lo.x, hi.y - lo.y) > len * px * 0.7;
    return { f, k, lo, hi, len, showLabels };
  });

  // Highlight sits up and to the left on screen whatever the ellipse's rotation, so the light
  // reads as fixed while the shapes turn. Gradients live in the ellipse's own unrotated frame.
  const lightOffset = (e: { rx: number; ry: number; angle: number }) => {
    const a = e.angle * Math.PI / 180;
    const d = 0.45 * Math.min(e.rx, e.ry);
    const sx = -0.7 * d, sy = -0.7 * d;
    const lx = sx * Math.cos(a) - sy * Math.sin(a), ly = sx * Math.sin(a) + sy * Math.cos(a);
    return { fx: 0.5 + lx / (2 * e.rx), fy: 0.5 + ly / (2 * e.ry) };
  };

  const setAxis = (k: number, f: Factor) => {
    setAxes(prev => {
      const next = [...prev] as [Factor, Factor, Factor];
      const clash = next.indexOf(f);
      if (clash !== -1) next[clash] = prev[k];
      next[k] = f;
      return next;
    });
  };

  const onDown = (e: React.PointerEvent<SVGSVGElement>) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, ...view };
    setDragging(true);
  };
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = drag.current;
    if (!d) return;
    setView({
      yaw: d.yaw + (e.clientX - d.x) * 0.01,
      pitch: Math.max(PITCH_MIN, Math.min(PITCH_MAX, d.pitch + (e.clientY - d.y) * 0.01)),
    });
  };
  const onUp = () => { drag.current = null; setDragging(false); };

  // Hover isolates a party, except mid-drag, where the pointer crosses shapes by accident.
  const dimmed = (p: string) => (hover && !dragging) ? hover !== p : isDim(p);

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
      <div className="min-w-0 flex-1">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%"
          style={{ height: 'auto', maxWidth: 620, display: 'block', margin: '0 auto', touchAction: 'none', cursor: dragging ? 'grabbing' : 'grab' }}
          onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
          aria-label={`Parties in three dimensions: ${axes.map(f => FACTOR_LABELS[f]).join(', ')}`}>
          <defs>
            <filter id="c3d-shadow-blur" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" />
            </filter>
            {ellipsoids.map(({ p, e, colorZ }) => {
              const base = colorMode === 'party' ? PARTY_COLORS[p] : bamForZ(colorZ);
              const { fx, fy } = lightOffset(e);
              return (
                <radialGradient key={p} id={`c3d-shade-${p}`} cx={0.5} cy={0.5} r={0.5} fx={fx} fy={fy}>
                  <stop offset="0%" stopColor="#ffffff" stopOpacity={0.9} />
                  <stop offset="35%" stopColor={base} stopOpacity={0.35} />
                  <stop offset="85%" stopColor={base} stopOpacity={0.55} />
                  <stop offset="100%" stopColor={base} stopOpacity={0.75} />
                </radialGradient>
              );
            })}
          </defs>

          {/* Floor: grid, then each party's shadow straight below it. */}
          <polygon points={floorCorners.map(c => `${c.x},${c.y}`).join(' ')} fill="#f1f5f9" />
          {gridLines.map(([a, b], i) => (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#e2e8f0" strokeWidth={1} />
          ))}
          {ellipsoids.map(({ p, foot, shadow }) => (
            <ellipse key={p} cx={foot.x} cy={foot.y} rx={shadow.rx * px} ry={shadow.ry * px}
              transform={`rotate(${-shadow.angle} ${foot.x} ${foot.y})`}
              fill={dimmed(p) ? '#cbd5e1' : '#64748b'} fillOpacity={dimmed(p) ? 0.12 : 0.22}
              filter="url(#c3d-shadow-blur)" />
          ))}

          {axisEnds.map(({ f, k, lo, hi, showLabels }) => (
            <g key={f}>
              <line x1={lo.x} y1={lo.y} x2={hi.x} y2={hi.y} stroke="#94a3b8" strokeDasharray="4,3" />
              {tickVals.filter(t => Math.abs(t) < axisLen(k) && (k !== 1 || t > floorY)).map(t => {
                const q = project(unit(k, t));
                return <circle key={t} cx={q.x} cy={q.y} r={1.6} fill="#94a3b8" />;
              })}
              {showLabels && (
                <>
                  <text x={hi.x} y={hi.y} dy={-4} textAnchor="middle" fontSize={CHART_TYPE.smallTick} fontWeight={600} fill={CHART_FILL.label}
                    stroke="#fff" strokeWidth={3} paintOrder="stroke">
                    {FACTOR_POLES[f]?.high} →
                  </text>
                  <text x={lo.x} y={lo.y} dy={11} textAnchor="middle" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.tick}
                    stroke="#fff" strokeWidth={3} paintOrder="stroke">
                    {FACTOR_POLES[f]?.low}
                  </text>
                </>
              )}
            </g>
          ))}

          {ellipsoids.map(({ p, at, e, fourthZ }) => {
            const dim = dimmed(p);
            const near = nearness(at.depth);
            return (
              <g key={p} onPointerEnter={() => setHover(p)} onPointerLeave={() => setHover(null)}
                opacity={dim ? 0.18 : 0.55 + 0.45 * near}>
                <title>{`${PARTY_NAMES[p]}: ${FACTOR_LABELS[fourth]} ${fourthZ >= 0 ? '+' : ''}${fourthZ.toFixed(2)} SD`}</title>
                <ellipse cx={at.x} cy={at.y} rx={e.rx * px} ry={e.ry * px}
                  transform={`rotate(${-e.angle} ${at.x} ${at.y})`}
                  fill={`url(#c3d-shade-${p})`}
                  stroke={PARTY_COLORS[p]} strokeOpacity={0.9} strokeWidth={dim ? 1 : 1.5} />
                {!dim && (
                  <text x={at.x} y={at.y + 3} textAnchor="middle" fontSize={CHART_TYPE.inMark} fontWeight={700}
                    fill={PARTY_COLORS[p]} stroke="#fff" strokeWidth={2.5} paintOrder="stroke">{p}</text>
                )}
              </g>
            );
          })}

          {currentMarkers.map(({ id, at }) => (
            <g key={id} opacity={isDim(id) ? 0.25 : 1}>
              <circle cx={at.x} cy={at.y} r={4} fill="#fff" stroke="#475569" strokeWidth={1.5} strokeDasharray="2,1.5" />
              <text x={at.x + 6} y={at.y + 3} fontSize={CHART_TYPE.inMark} fontWeight={700} fill="#475569">{id}</text>
            </g>
          ))}
        </svg>
        <p className={`${CARD_HINT} mt-1 text-center`}>
          Drag to rotate. Each shape holds the middle half of a party's voters as seen from the current
          angle, with its shadow on the floor directly below. Dots on the axes mark 1 and 2 standard deviations.
        </p>
      </div>

      <div className="flex shrink-0 flex-col gap-2.5 border-t border-border pt-3 lg:w-60 lg:border-l lg:border-t-0 lg:pl-4 lg:pt-0">
        {(['Axis 1', 'Axis 2', 'Axis 3'] as const).map((label, k) => (
          <div key={label} className="flex items-start gap-1.5">
            <span className="w-12 shrink-0 pt-1 text-xs text-muted-foreground font-semibold">{label}</span>
            <div className="flex flex-wrap gap-1">
              {FACTORS.map(f => (
                <Button key={f} onClick={() => setAxis(k, f)} title={FACTOR_LABELS[f]}
                  variant={axes[k] === f ? 'default' : 'secondary'} size="sm" className="px-2 h-6 flex-none">
                  {AXIS_WORD[f]}
                </Button>
              ))}
            </div>
          </div>
        ))}
        <div className="flex items-start gap-1.5">
          <span className="w-12 shrink-0 pt-1 text-xs text-muted-foreground font-semibold">Color</span>
          <div className="flex flex-wrap items-center gap-1">
            {(['party', ...FACTORS] as const).map(opt => (
              <Button key={opt} onClick={() => setColorMode(opt)}
                title={opt === 'party' ? 'Party color' : FACTOR_LABELS[opt]}
                variant={colorMode === opt ? 'default' : 'secondary'} size="sm" className="px-2 h-6 flex-none">
                {opt === 'party' ? 'Party' : AXIS_WORD[opt]}
              </Button>
            ))}
            {colorMode !== 'party' && (
              <div className="flex items-center gap-1 ml-1">
                <span className="text-4xs text-muted-foreground">{FACTOR_POLES[colorMode]?.low}</span>
                <div className="h-1.5 w-14 rounded-full"
                  style={{ background: `linear-gradient(to right, ${bamForZ(-2.5)}, ${bamForZ(0)}, ${bamForZ(2.5)})` }} />
                <span className="text-4xs text-muted-foreground">{FACTOR_POLES[colorMode]?.high}</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-1">
          <Button onClick={() => setSpin(s => !s)} variant={spin ? 'default' : 'secondary'} size="sm" className="px-2 h-6">
            {spin ? 'Stop' : 'Spin'}
          </Button>
          <Button onClick={() => setView(DEFAULT_VIEW)} variant="secondary" size="sm" className="px-2 h-6">
            Reset view
          </Button>
        </div>
      </div>
    </div>
  );
}
