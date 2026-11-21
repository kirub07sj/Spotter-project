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
      className={`border-b border-black/5 transition-colors dark:border-white/5 ${
        hovered
          ? 'bg-black/10 font-medium text-neutral-900 dark:bg-white/15 dark:text-white'
          : 'text-neutral-800 hover:bg-black/[0.03] dark:text-neutral-300 dark:hover:bg-white/[0.04]'
      } ${cp.low_confidence ? 'text-neutral-500 dark:text-neutral-400' : ''}`}
      onMouseEnter={() => hover(cp.index)}
      onMouseLeave={() => hover(null)}
    >
      <td className="px-2 text-right font-mono text-neutral-900 dark:text-neutral-200">
        {cp.mile.toFixed(0)}
      </td>
      <td className="whitespace-nowrap px-2 text-neutral-900 dark:text-neutral-200">
        {formatTime(cp.eta)}
        {cp.low_confidence && (
          <span
            className="ml-1 text-neutral-400"
            title="More than 72 h out: low-confidence forecast"
          >
            <span aria-hidden="true">◌</span>
            <span className="sr-only">(low-confidence forecast)</span>
          </span>
        )}
      </td>
      <td className="whitespace-nowrap px-2 text-right text-neutral-700 dark:text-neutral-300">
        {formatMph(w.wind_mph)} / {formatMph(w.gust_mph)}
      </td>
      <td className="whitespace-nowrap px-2 text-right text-neutral-700 dark:text-neutral-300">
        {formatRate(w.rain_in_hr)}
      </td>
      <td className="whitespace-nowrap px-2 text-right text-neutral-700 dark:text-neutral-300">
        {formatRate(w.snow_in_hr)}
      </td>
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
            className="ml-1 rounded bg-neutral-800 px-1 text-[10px] font-bold text-white dark:bg-neutral-200 dark:text-black"
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
      className="overflow-auto rounded-xl border border-black/10 bg-white/60 backdrop-blur-md dark:border-white/10 dark:bg-black/60"
      style={virtual ? { maxHeight: ROW_H * (VIEWPORT_ROWS + 1) } : undefined}
      onScroll={virtual ? (e) => setScrollTop(e.currentTarget.scrollTop) : undefined}
    >
      <table className="w-full text-xs">
        <caption className="sr-only">
          Checkpoints for route {route.id}: weather at each ETA and risk level
        </caption>
        <thead className="sticky top-0 z-10 border-b border-black/10 bg-neutral-100/90 text-left text-[11px] uppercase tracking-wide text-neutral-500 backdrop-blur dark:border-white/10 dark:bg-neutral-900/95 dark:text-neutral-400">
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
