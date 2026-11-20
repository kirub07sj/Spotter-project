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
      className={`cursor-pointer rounded-lg border bg-white p-3 transition-shadow ${selected ? 'border-slate-900 shadow-md ring-1 ring-slate-900' : 'border-slate-200 hover:border-slate-400'}`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded text-xs font-bold text-white ${ROUTE_BADGE[route.id]}`}
          aria-hidden="true"
        >
          {route.id}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-medium" title={route.label}>
          <span className="sr-only">Route {route.id}, </span>
          {route.label}
        </span>
        {route.recommended && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-900">
            Recommended
          </span>
        )}
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-x-2 text-xs">
        <div>
          <dt className="text-slate-500">Drive</dt>
          <dd className="font-semibold text-slate-900">{formatDuration(route.duration_s)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Distance</dt>
          <dd className="font-semibold text-slate-900">{formatMiles(route.distance_mi)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Arrive</dt>
          <dd className="font-semibold text-slate-900">{formatTime(route.arrival_time)}</dd>
        </div>
      </dl>
      <RiskBar className="mt-2" milesByLevel={s.miles_by_level} unknownMi={s.unknown_mi} />
      <div className="mt-2 flex items-center justify-between text-xs text-slate-600">
        <span>
          Avg risk <span className="font-semibold text-slate-900">{s.avg_risk.toFixed(2)}</span> / 4
          {s.miles_by_level.SEVERE > 0 && <> · {formatMiles(s.miles_by_level.SEVERE)} severe</>}
          {s.miles_by_level.NO_TRAVEL > 0 && (
            <> · {formatMiles(s.miles_by_level.NO_TRAVEL)} no travel</>
          )}
        </span>
        <LevelChip level={s.max_level} size="xs" />
      </div>
      {route.source === 'via' && (
        <p className="mt-1 text-[11px] text-slate-500">Alternative generated through a via point</p>
      )}
    </div>
  );
}
