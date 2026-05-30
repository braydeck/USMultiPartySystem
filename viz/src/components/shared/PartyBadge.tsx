import { getPartyColor } from '../../constants/parties';
import { Badge } from '@/components/ui/badge';

interface Props {
  code: string;
  size?: 'sm' | 'md';
}

export function PartyBadge({ code, size = 'md' }: Props) {
  const color = getPartyColor(code);
  return (
    <Badge
      variant="outline"
      className={size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'}
      style={{ backgroundColor: color + '33', color, borderColor: color + '88' }}
    >
      {code}
    </Badge>
  );
}
