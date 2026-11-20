import type { RiskLevel } from '../../api/types';
import { LEVELS } from '../risk';

export function LevelChip({ level, size = 'sm' }: { level: RiskLevel; size?: 'xs' | 'sm' }) {
  const meta = LEVELS[level];
  const pad = size === 'xs' ? 'px-1.5 py-0 text-[11px]' : 'px-2 py-0.5 text-xs';
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full font-medium ring-1 ring-inset ${pad} ${meta.chip}`}
    >
      <span aria-hidden="true">{meta.icon}</span>
      {meta.label}
    </span>
  );
}
