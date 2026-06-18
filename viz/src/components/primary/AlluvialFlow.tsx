import { useMemo, useRef, useState } from 'react';
import { getBlendColor } from '../../constants/parties';

interface AlluvialNode {
  id: string;
  label: string;
  stageIdx: number;
  pct: number;
}

interface AlluvialLink {
  source: string;
  target: string;
  value: number;
  type?: string; // "continuation" | "elimination" | "surplus" | "exhausted"
}

interface AlluvialData {
  stageLabels: string[];
  nodes: AlluvialNode[];
  links: AlluvialLink[];
}

interface AlluvialFlowProps {
  data: AlluvialData;
  height?: number;
  highlightStage?: number;
}

// ── Layout constants ────────────────────────────────────────────────────────

const SVG_WIDTH       = 900;
const MARGIN_TOP      = 40;
const MARGIN_BOTTOM   = 20;
const MARGIN_LEFT     = 72;
const MARGIN_RIGHT    = 80;
const BLOCK_W         = 28;
const BLOCK_GAP       = 3;    // px gap between stacked blocks in a column
const MIN_BLOCK_H     = 4;    // minimum visible block height

// F5 ideological order — used to sort candidates within each column
const F5_ORDER = [
  'PRG', 'PRG_dsa',
  'LIB', 'LIB_dsa', 'LIB_sd',
  'DSA', 'DSA_prg', 'DSA_lib',
  'SD',  'SD_lib', 'SD_sty',
  'STY', 'STY_sd', 'STY_ctr',
  'CUP', 'CUP_sty', 'CUP_con',
  'CON', 'CON_ctr', 'CON_ref',
  'POP', 'POP_con', 'POP_nat',
  'NAT', 'NAT_ref',
];

function f5Rank(label: string): number {
  const idx = F5_ORDER.indexOf(label);
  if (idx !== -1) return idx;
  // Raw Multi: "CON_1" → extract party prefix, sub-sort by suffix
  const parts = label.split('_');
  const partyIdx = F5_ORDER.indexOf(parts[0]);
  if (partyIdx !== -1) {
    const suffix = parseInt(parts[1] || '0', 10) || 0;
    return partyIdx + suffix * 0.1;
  }
  return 99;
}

// ── Tooltip state type ──────────────────────────────────────────────────────

interface TooltipInfo {
  x: number; y: number;
  text: string[];
}

// ── Main component ──────────────────────────────────────────────────────────

export default function AlluvialFlow({ data, height = 540, highlightStage }: AlluvialFlowProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const DRAW_H = height - MARGIN_TOP - MARGIN_BOTTOM;

  const layout = useMemo(() => {
    const { nodes, links, stageLabels } = data;
    const numStages = stageLabels.length;

    // Column x-positions (center of block)
    const colW = (SVG_WIDTH - MARGIN_LEFT - MARGIN_RIGHT) / (numStages - 1);
    const colX = (s: number) => MARGIN_LEFT + s * colW;

    // Group nodes by stage
    const byStage: Map<number, AlluvialNode[]> = new Map();
    for (const n of nodes) {
      if (!byStage.has(n.stageIdx)) byStage.set(n.stageIdx, []);
      byStage.get(n.stageIdx)!.push(n);
    }

    // Sort each stage by F5 ideological order
    for (const [, arr] of byStage) {
      arr.sort((a, b) => f5Rank(a.label) - f5Rank(b.label));
    }

    // Compute block y-positions for each node
    // Scale so all blocks + gaps fill DRAW_H
    const nodeLayout: Map<string, { x: number; y: number; h: number }> = new Map();

    for (const [stageIdx, stageNodes] of byStage) {
      const totalPct = stageNodes.reduce((s, n) => s + n.pct, 0) || 1;
      const totalGaps = (stageNodes.length - 1) * BLOCK_GAP;
      const availH = DRAW_H - totalGaps;

      let yOffset = MARGIN_TOP;
      for (const n of stageNodes) {
        const rawH = (n.pct / totalPct) * availH;
        const h = Math.max(rawH, MIN_BLOCK_H);
        nodeLayout.set(n.id, { x: colX(stageIdx), y: yOffset, h });
        yOffset += h + BLOCK_GAP;
      }
    }

    // Build link path data
    // For each link, compute the ribbon as a bezier connecting source right to target left
    // Track current "used" offsets within each block edge
    const srcUsed: Map<string, number> = new Map();
    const tgtUsed: Map<string, number> = new Map();

    // Sort links: continuation first (for cleaner ribbon stacking), then transfers
    const sortedLinks = [...links].sort((a, b) => {
      if (a.type === 'continuation' && b.type !== 'continuation') return -1;
      if (a.type !== 'continuation' && b.type === 'continuation') return 1;
      return b.value - a.value;
    });

    interface RibbonDef {
      d: string;
      color: string;
      opacity: number;
      isElimination: boolean;
      isExhausted: boolean;
      sourceLabel: string;
      targetLabel: string;
      value: number;
      srcStageIdx: number;
      tgtStageIdx: number;
    }

    const ribbons: RibbonDef[] = [];

    for (const link of sortedLinks) {
      const src = nodeLayout.get(link.source);
      const tgt = nodeLayout.get(link.target);
      if (!src || !tgt) continue;

      // Proportion of source block used by this link
      const srcNode = nodes.find(n => n.id === link.source);
      const tgtNode = nodes.find(n => n.id === link.target);
      if (!srcNode || !tgtNode) continue;

      const srcPct = srcNode.pct || 0.001;
      const tgtPct = tgtNode.pct || 0.001;

      const ribbonHSrc = Math.max((link.value / srcPct) * src.h, 1.5);
      const ribbonHTgt = Math.max((link.value / tgtPct) * tgt.h, 1.5);

      const sy0 = src.y + (srcUsed.get(link.source) ?? 0);
      const sy1 = sy0 + ribbonHSrc;
      const ty0 = tgt.y + (tgtUsed.get(link.target) ?? 0);
      const ty1 = ty0 + ribbonHTgt;

      srcUsed.set(link.source, (srcUsed.get(link.source) ?? 0) + ribbonHSrc);
      tgtUsed.set(link.target, (tgtUsed.get(link.target) ?? 0) + ribbonHTgt);

      // Cubic bezier: control points at 50% of horizontal distance
      const x0 = src.x + BLOCK_W;
      const x1 = tgt.x;
      const cx = (x0 + x1) / 2;

      const d = [
        `M${x0},${sy0}`,
        `C${cx},${sy0} ${cx},${ty0} ${x1},${ty0}`,
        `L${x1},${ty1}`,
        `C${cx},${ty1} ${cx},${sy1} ${x0},${sy1}`,
        'Z',
      ].join(' ');

      const isElim = link.type === 'elimination';
      const isExhausted = link.type === 'exhausted';
      const color = getBlendColor(srcNode.label);

      ribbons.push({
        d,
        color,
        opacity: (isElim || isExhausted) ? 0.55 : 0.35,
        isElimination: isElim,
        isExhausted,
        sourceLabel: srcNode.label,
        targetLabel: tgtNode.label,
        value: link.value,
        srcStageIdx: srcNode.stageIdx,
        tgtStageIdx: tgtNode.stageIdx,
      });
    }

    return { nodeLayout, byStage, colX, ribbons, stageLabels };
  }, [data, DRAW_H]);

  const handleBlockHover = (e: React.MouseEvent, node: AlluvialNode) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top - 10,
      text: [`${node.label}`, `${node.pct.toFixed(1)}% of stage votes`],
    });
  };

  const handleRibbonHover = (e: React.MouseEvent, r: { sourceLabel: string; targetLabel: string; value: number; isElimination: boolean; isExhausted: boolean }) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const label = r.isExhausted
      ? `${r.sourceLabel} → exhausted (no next pref)`
      : r.isElimination
        ? `${r.sourceLabel} eliminated → ${r.targetLabel}`
        : `${r.sourceLabel} continues`;
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top - 10,
      text: [label, `${r.value.toFixed(1)}% of votes`],
    });
  };

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG_WIDTH} ${height}`}
        className="w-full"
        style={{ minWidth: 600 }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* Stage column headers */}
        {layout.stageLabels.map((label, i) => (
          <text
            key={i}
            x={layout.colX(i) + BLOCK_W / 2}
            y={MARGIN_TOP - 10}
            textAnchor="middle"
            fontSize={10}
            fill="#64748b"
            fontWeight={600}
          >
            {label}
          </text>
        ))}

        {/* Ribbons (drawn first, behind blocks) */}
        {layout.ribbons.map((r, i) => {
          const isActive = highlightStage === undefined
            || r.srcStageIdx === highlightStage
            || r.tgtStageIdx === highlightStage;
          const ribbonOpacity = isActive ? r.opacity : 0.07;
          return (
            <path
              key={i}
              d={r.d}
              fill={r.color}
              opacity={ribbonOpacity}
              stroke="none"
              style={{ cursor: 'pointer' }}
              onMouseMove={(e) => handleRibbonHover(e, r)}
              onMouseLeave={() => setTooltip(null)}
            />
          );
        })}

        {/* Candidate blocks */}
        {Array.from(layout.byStage.entries()).map(([stageIdx, stageNodes]) =>
          stageNodes.map((node) => {
            const pos = layout.nodeLayout.get(node.id);
            if (!pos) return null;
            const color = getBlendColor(node.label);
            const isFinal = stageIdx === data.stageLabels.length - 1;
            const isActiveCol = highlightStage === undefined || stageIdx === highlightStage;
            const blockOpacity = isActiveCol ? 1 : 0.3;

            return (
              <g key={node.id} opacity={blockOpacity}>
                <rect
                  x={pos.x}
                  y={pos.y}
                  width={BLOCK_W}
                  height={pos.h}
                  fill={color}
                  rx={2}
                  style={{ cursor: 'pointer' }}
                  onMouseMove={(e) => handleBlockHover(e, node)}
                  onMouseLeave={() => setTooltip(null)}
                />
                {/* Label: show if block is tall enough, or always in final stage */}
                {(pos.h >= 10 || isFinal) && (
                  <text
                    x={pos.x + BLOCK_W + 4}
                    y={pos.y + pos.h / 2 + 4}
                    fontSize={isFinal ? 11 : 9}
                    fontWeight={isFinal ? 600 : 400}
                    fill="#1e293b"
                  >
                    {node.label}
                    {isFinal ? ` ${node.pct.toFixed(1)}%` : ''}
                  </text>
                )}
                {/* Left-side label for initial stage */}
                {stageIdx === 0 && pos.h >= 8 && (
                  <text
                    x={pos.x - 4}
                    y={pos.y + pos.h / 2 + 4}
                    fontSize={9}
                    textAnchor="end"
                    fill="#1e293b"
                  >
                    {node.label}
                  </text>
                )}
              </g>
            );
          })
        )}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded bg-slate-800 px-2 py-1 text-xs text-white shadow-lg"
          style={{ left: tooltip.x + 10, top: tooltip.y - 10, maxWidth: 180 }}
        >
          {tooltip.text.map((t, i) => (
            <div key={i} className={i === 0 ? 'font-semibold' : 'text-slate-300'}>{t}</div>
          ))}
        </div>
      )}
    </div>
  );
}
