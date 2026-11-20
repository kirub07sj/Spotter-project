import { memo, useState } from 'react';
import type { Checkpoint, Route } from '../../api/types';
import { formatMph, formatRate, formatTime } from '../../lib/format';
import { LevelChip } from '../../lib/ui/LevelChip';
import { useUi } from '../../store/ui';

const ROW_H = 36;
const VIRTUALIZE_OVER = 60;
const VIEWPORT_ROWS = 14;
const FACTOR_ICON = { wind: '💨', snow: '❄', rain: '🌧' } as const;

const Row = memo(function Row({ cp, hovered }: { cp: Checkpoint; hovered: boolean }) {
  const hover = useUi((s) => s.hoverCheckpoint);
  const w = cp.weather;
  return (
    <tr
      style={{ height: ROW_H }}
      className={`border-b border-slate-100 ${hovered ? 'bg-blue-50' : ''} ${cp.low_confidence ? 'text-slate-500' : ''}`}
      onMouseEnter={() => hover(cp.index)}
      onMouseLeave={() => hover(null)}
    >
      <td className="px-2 text-right">{cp.mile.toFixed(0)}</td>
      <td className="whitespace-nowrap px-2">
        {formatTime(cp.eta)}
        {cp.low_confidence && (
          <span className="ml-1" title="More than 72 h out: low-confidence forecast">
            <span aria-hidden="true">◌</span>
            <span className="sr-only">(low-confidence forecast)</span>
          </span>
        )}
      </td>
      <td className="whitespace-nowrap px-2 text-right">
        {formatMph(w.wind_mph)} / {formatMph(w.gust_mph)}
      </td>
      <td className="whitespace-nowrap px-2 text-right">{formatRate(w.rain_in_hr)}</td>
      <td className="whitespace-nowrap px-2 text-right">{formatRate(w.snow_in_hr)}</td>
      <td className="whitespace-nowrap px-2">
        <LevelChip level={cp.levels.overall} size="xs" />
        {cp.dominant_factor && cp.levels.overall !== 'LOW' && (
          <span className="ml-1" title={`Driven by ${cp.dominant_factor}`}>
            <span aria-hidden="true">{FACTOR_ICON[cp.dominant_factor]}</span>
            <span className="sr-only">driven by {cp.dominant_factor}</span>
          </span>
        )}
        {cp.load_adjusted && (
          <span
            className="ml-1 rounded bg-slate-800 px-1 text-[10px] font-bold text-white"
            title="Load rule raised the wind level"
          >
            LOAD
          </span>
        )}
      </td>
    </tr>
  );
});

/** A real table so screen readers get the same data as the map (docs/04 §10). Rows are
 * windowed once a route has more than 60 checkpoints. */
export function CheckpointTable({ route }: { route: Route }) {
  const hovered = useUi((s) => s.hoveredCheckpoint);
  const [scrollTop, setScrollTop] = useState(0);
  const rows = route.checkpoints;
  const virtual = rows.length > VIRTUALIZE_OVER;
  const start = virtual ? Math.max(0, Math.floor(scrollTop / ROW_H) - 4) : 0;
  const end = virtual ? Math.min(rows.length, start + VIEWPORT_ROWS + 8) : rows.length;
  return (
    <div
      className="overflow-auto rounded-lg border border-slate-200 bg-white"
      style={virtual ? { maxHeight: ROW_H * (VIEWPORT_ROWS + 1) } : undefined}
      onScroll={virtual ? (e) => setScrollTop(e.currentTarget.scrollTop) : undefined}
    >
      <table className="w-full text-xs">
        <caption className="sr-only">
          Checkpoints for route {route.id}: weather at each ETA and risk level
        </caption>
        <thead className="sticky top-0 z-10 bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
          <tr style={{ height: ROW_H }}>
            <th scope="col" className="px-2 text-right">
              Mile
            </th>
            <th scope="col" className="px-2">
              ETA
            </th>
            <th scope="col" className="px-2 text-right">
              Wind / gust
            </th>
            <th scope="col" className="px-2 text-right">
              Rain
            </th>
            <th scope="col" className="px-2 text-right">
              Snow
            </th>
            <th scope="col" className="px-2">
              Risk
            </th>
          </tr>
        </thead>
        <tbody>
          {start > 0 && <tr aria-hidden="true" style={{ height: start * ROW_H }} />}
          {rows.slice(start, end).map((cp) => (
            <Row key={cp.index} cp={cp} hovered={hovered === cp.index} />
          ))}
          {end < rows.length && (
            <tr aria-hidden="true" style={{ height: (rows.length - end) * ROW_H }} />
          )}
        </tbody>
      </table>
    </div>
  );
}
