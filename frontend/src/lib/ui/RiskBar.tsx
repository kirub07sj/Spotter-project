import type { RiskLevel } from '../../api/types';
import { formatMiles } from '../format';
import { LEVELS, LEVEL_ORDER } from '../risk';

interface Props {
  milesByLevel: Record<Exclude<RiskLevel, 'UNKNOWN'>, number>;
  unknownMi?: number;
  className?: string;
}

/** Stacked bar of miles by level, proportional to distance. Colour is never alone: each
 * segment has a title and the bar has an accessible text summary. */
export function RiskBar({ milesByLevel, unknownMi = 0, className = '' }: Props) {
  const parts = [
    ...LEVEL_ORDER.map((lvl) => ({ lvl, mi: milesByLevel[lvl as keyof typeof milesByLevel] })),
    { lvl: 'UNKNOWN' as RiskLevel, mi: unknownMi },
  ].filter((p) => p.mi > 0);
  const total = parts.reduce((sum, p) => sum + p.mi, 0) || 1;
  const summary = parts.map((p) => `${LEVELS[p.lvl].label} ${formatMiles(p.mi)}`).join(', ');
  return (
    <div
      className={`flex h-2.5 w-full overflow-hidden rounded-full bg-slate-200 ${className}`}
      role="img"
      aria-label={`Miles by risk level: ${summary}`}
    >
      {parts.map((p) => (
        <div
          key={p.lvl}
          className={`${LEVELS[p.lvl].swatch} h-full`}
          style={{ width: `${(p.mi / total) * 100}%` }}
          title={`${LEVELS[p.lvl].label}: ${formatMiles(p.mi)}`}
        />
      ))}
    </div>
  );
}
