import type { Route } from '../../api/types';
import { formatDuration, formatMiles, formatTime } from '../../lib/format';
import { ROUTE_BADGE } from '../../lib/routes';
import { LevelChip } from '../../lib/ui/LevelChip';
import { RiskBar } from '../../lib/ui/RiskBar';

interface Props {
  route: Route;
  selected: boolean;
  focusable: boolean;
  onSelect: () => void;
  onHover: (hovering: boolean) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => void;
}

export function RouteCard({ route, selected, focusable, onSelect, onHover, onKeyDown }: Props) {
  const s = route.stats;
  return (
    <div
      role="radio"
      aria-checked={selected}
      tabIndex={focusable ? 0 : -1}
      data-route-id={route.id}
      onClick={onSelect}
      onKeyDown={onKeyDown}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onFocus={() => onHover(true)}
      onBlur={() => onHover(false)}
      className={`cursor-pointer rounded-xl border p-3.5 transition-all backdrop-blur-md ${
        selected
          ? 'border-black/50 bg-black/[0.06] shadow-xl shadow-black/10 ring-1 ring-black/30 dark:border-white/50 dark:bg-white/[0.1] dark:shadow-black/70 dark:ring-1 dark:ring-white/30'
          : 'border-black/10 bg-black/[0.02] hover:border-black/20 hover:bg-black/[0.04] dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-white/20 dark:hover:bg-white/[0.06]'
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold text-white shadow-sm ${ROUTE_BADGE[route.id]}`}
          aria-hidden="true"
        >
          {route.id}
        </span>
        <span
          className="min-w-0 flex-1 truncate text-sm font-medium text-neutral-900 dark:text-white"
          title={route.label}
        >
          <span className="sr-only">Route {route.id}, </span>
          {route.label}
        </span>
        {route.recommended && (
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-semibold text-emerald-800 ring-1 ring-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-300">
            Recommended
          </span>
        )}
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-x-2 text-xs">
        <div>
          <dt className="text-neutral-500 dark:text-neutral-400">Drive</dt>
          <dd className="font-semibold text-neutral-900 dark:text-white">
            {formatDuration(route.duration_s)}
          </dd>
        </div>
        <div>
          <dt className="text-neutral-500 dark:text-neutral-400">Distance</dt>
          <dd className="font-semibold text-neutral-900 dark:text-white">
            {formatMiles(route.distance_mi)}
          </dd>
        </div>
        <div>
          <dt className="text-neutral-500 dark:text-neutral-400">Arrive</dt>
          <dd className="font-semibold text-neutral-900 dark:text-white">
            {formatTime(route.arrival_time)}
          </dd>
        </div>
      </dl>
      <RiskBar className="mt-2" milesByLevel={s.miles_by_level} unknownMi={s.unknown_mi} />
      <div className="mt-2 flex items-center justify-between text-xs text-neutral-600 dark:text-neutral-300">
        <span>
          Avg risk{' '}
          <span className="font-semibold text-neutral-900 dark:text-white">
            {s.avg_risk.toFixed(2)}
          </span>{' '}
          / 4{s.miles_by_level.SEVERE > 0 && <> · {formatMiles(s.miles_by_level.SEVERE)} severe</>}
          {s.miles_by_level.NO_TRAVEL > 0 && (
            <> · {formatMiles(s.miles_by_level.NO_TRAVEL)} no travel</>
          )}
        </span>
        <LevelChip level={s.max_level} size="xs" />
      </div>
      {route.source === 'via' && (
        <p className="mt-1 text-[11px] text-neutral-500 dark:text-neutral-400">
          Alternative generated through a via point
        </p>
      )}
    </div>
  );
}
