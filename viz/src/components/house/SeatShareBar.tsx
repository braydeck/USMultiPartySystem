// Shared seat-share bar: a full-width track with the label overlaid inside the bar. Used by both
// the party-list view and the STV "Population vs seat share" chart so the two read identically.
import { getContrastText } from '../../constants/parties';

export function SeatShareBar({ pct, max, color, label, faded, outline, dashed }: {
  pct: number; max: number; color: string; label: string;
  faded?: boolean; outline?: boolean; dashed?: boolean;
}) {
  const w = Math.max((pct / max) * 100, pct > 0 ? 2 : 0);
  const isSolid = !faded && !outline && !dashed;
  const style = outline
    ? { width: `${w}%`, background: color + '22', border: `1.5px solid ${color}` }
    : dashed
      ? { width: `${w}%`, background: 'transparent', border: `1.5px dashed ${color}` }
      : { width: `${w}%`, background: faded ? color + '66' : color };
  const textColor = isSolid ? getContrastText(color) : '#374151';
  const textClass = isSolid ? 'chip-text' : '';
  return (
    <div className="relative h-5 rounded bg-muted/60 overflow-hidden">
      <div className="h-full rounded" style={style} />
      <span className={`absolute left-1.5 top-1/2 -translate-y-1/2 text-3xs font-semibold whitespace-nowrap ${textClass}`}
        style={{ color: textColor }}>{label}</span>
    </div>
  );
}
