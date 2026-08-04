import { lightenHex } from '../../constants/parties';
import { carve, type Faceoff } from './faceoff';

const MOB_HATCH = 'repeating-linear-gradient(45deg, rgba(255,255,255,0.55) 0 2px, transparent 2px 5px)';
const fmt = (w: number) => (w >= 10 ? w.toFixed(0) : w.toFixed(1));

/**
 * A vs B as one visual bar. Each side, outer→inner: mobilize (hatched — aligned voters who skip
 * midterms), likely (solid), persuadable (desaturated, near the boundary, A-side vs B-side). With
 * `labels`, each segment's share is printed BELOW the bar in that side's color (the two persuadable
 * numbers sit just left / right of the split so they never collide). Boundary shifts per matchup.
 */
export function FaceoffBar({ f, aColor, bColor, height = 34, labels = false }: {
  f: Faceoff; aColor: string; bColor: string; height?: number; labels?: boolean;
}) {
  const c = carve(f);
  const aLight = lightenHex(aColor, 0.5), bLight = lightenHex(bColor, 0.5);
  const aPct = c.aMob + c.aLik + c.aPer;

  const segs = [
    { key: 'aMob', w: c.aMob, bg: aColor, hatch: true, tip: 'mobilize for A' },
    { key: 'aLik', w: c.aLik, bg: aColor, hatch: false, tip: 'likely A' },
    { key: 'aPer', w: c.aPer, bg: aLight, hatch: false, tip: 'persuadable (leans A)' },
    { key: 'bPer', w: c.bPer, bg: bLight, hatch: false, tip: 'persuadable (leans B)' },
    { key: 'bLik', w: c.bLik, bg: bColor, hatch: false, tip: 'likely B' },
    { key: 'bMob', w: c.bMob, bg: bColor, hatch: true, tip: 'mobilize for B' },
  ];

  // Below-bar labels: mobilize/likely centered on their segment; persuadable pinned to the split.
  type Lab = { key: string; v: number; color: string; anchor: 'c' | 'l' | 'r'; at: number };
  const labs: Lab[] = labels ? ([
    c.aMob > 0.5 && { key: 'aMob', v: c.aMob, color: aColor, anchor: 'c', at: c.aMob / 2 },
    c.aLik > 0.5 && { key: 'aLik', v: c.aLik, color: aColor, anchor: 'c', at: c.aMob + c.aLik / 2 },
    c.aPer > 0.3 && { key: 'aPer', v: c.aPer, color: aColor, anchor: 'r', at: aPct },
    c.bPer > 0.3 && { key: 'bPer', v: c.bPer, color: bColor, anchor: 'l', at: aPct },
    c.bLik > 0.5 && { key: 'bLik', v: c.bLik, color: bColor, anchor: 'c', at: aPct + c.bPer + c.bLik / 2 },
    c.bMob > 0.5 && { key: 'bMob', v: c.bMob, color: bColor, anchor: 'c', at: 100 - c.bMob / 2 },
  ].filter(Boolean) as Lab[]) : [];

  return (
    <div className="w-full">
      <div className="relative flex rounded-md overflow-hidden border border-border" style={{ height }}>
        {segs.map(s => s.w <= 0.05 ? null : (
          <div key={s.key} style={{ width: `${s.w}%`, backgroundColor: s.bg, backgroundImage: s.hatch ? MOB_HATCH : undefined }}
            title={`${s.tip}: ${s.w.toFixed(1)}%`} />
        ))}
        <div className="absolute inset-y-0 pointer-events-none" style={{ left: `${aPct}%`, borderLeft: '2px solid white' }} />
      </div>
      {labels && (
        <div className="relative h-3.5 mt-0.5">
          {labs.map(l => (
            <span key={l.key} className="absolute top-0 text-3xs font-semibold tabular-nums whitespace-nowrap"
              style={l.anchor === 'r'
                ? { left: `${l.at}%`, transform: 'translateX(-100%)', paddingRight: '3px', color: l.color }
                : l.anchor === 'l'
                  ? { left: `${l.at}%`, paddingLeft: '3px', color: l.color }
                  : { left: `${l.at}%`, transform: 'translateX(-50%)', color: l.color }}>
              {fmt(l.v)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Key for the three tones a faceoff bar uses, in one party's color. */
export function ToneLegend({ color }: { color: string }) {
  const sw = 'w-3.5 h-3 rounded-sm inline-block shrink-0';
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-3xs text-muted-foreground">
      <span className="flex items-center gap-1"><span className={sw} style={{ backgroundColor: color }} /> likely to vote</span>
      <span className="flex items-center gap-1"><span className={sw} style={{ backgroundColor: color, backgroundImage: MOB_HATCH }} /> mobilize (unlikely voter)</span>
      <span className="flex items-center gap-1"><span className={sw} style={{ backgroundColor: lightenHex(color, 0.5) }} /> persuadable</span>
    </div>
  );
}
