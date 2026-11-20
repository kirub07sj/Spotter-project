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
          className="flex gap-2 rounded-md bg-sky-50 px-2.5 py-1.5 text-xs text-sky-900 ring-1 ring-sky-200"
        >
          <span aria-hidden="true">ℹ</span>
          {w.detail}
        </li>
      ))}
    </ul>
  );
}
