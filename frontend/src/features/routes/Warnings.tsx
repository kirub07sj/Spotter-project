import type { PlanWarning } from '../../api/types';

const SHOWN: PlanWarning['code'][] = [
  'ONLY_N_DISTINCT_ROUTES',
  'LOW_CONFIDENCE_FORECAST',
  'WEATHER_GAPS',
];

export function Warnings({ warnings }: { warnings: PlanWarning[] }) {
  const items = warnings.filter((w) => SHOWN.includes(w.code));
  if (items.length === 0) return null;
  return (
    <ul className="space-y-1" aria-label="Notes about this plan">
      {items.map((w) => (
        <li
          key={w.code}
          className="flex gap-2 rounded-xl border border-black/10 bg-black/5 px-3 py-2 text-xs text-neutral-800 backdrop-blur-sm dark:border-white/10 dark:bg-white/5 dark:text-neutral-200"
        >
          <span aria-hidden="true">ℹ</span>
          {w.detail}
        </li>
      ))}
    </ul>
  );
}
