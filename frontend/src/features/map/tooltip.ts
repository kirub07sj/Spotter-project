import type { Checkpoint } from '../../api/types';
import { formatMph, formatRate, formatTime } from '../../lib/format';
import { LEVELS } from '../../lib/risk';

const esc = (s: string) =>
  s.replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] as string,
  );

function chip(level: Checkpoint['levels']['overall']): string {
  const m = LEVELS[level];
  return `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${m.hex};margin-right:4px"></span>${m.icon} ${esc(m.label)}`;
}

export function checkpointTooltip(cp: Checkpoint, routeId: string): string {
  const w = cp.weather;
  const rows = [
    ['Gust', formatMph(w.gust_mph), cp.levels.wind],
    ['Sustained wind', formatMph(w.wind_mph), null],
    ['Rain', formatRate(w.rain_in_hr), cp.levels.rain],
    ['Snow', formatRate(w.snow_in_hr), cp.levels.snow],
  ] as const;
  const body = rows
    .map(
      ([name, value, level]) =>
        `<tr><td style="color:#64748b;padding-right:8px">${name}</td><td style="text-align:right;padding-right:8px">${esc(value)}</td><td>${level ? chip(level) : ''}</td></tr>`,
    )
    .join('');
  return `<div style="font:12px/1.4 Inter,system-ui,sans-serif;font-variant-numeric:tabular-nums;min-width:220px">
      <div style="font-weight:600;margin-bottom:2px">Route ${esc(routeId)} · mile ${cp.mile.toFixed(0)}</div>
      <div style="color:#475569">ETA ${esc(formatTime(cp.eta))} · forecast for ${esc(formatTime(cp.forecast_hour))}</div>
      <table style="margin:6px 0">${body}</table>
      <div style="font-weight:600">Overall: ${chip(cp.levels.overall)}</div>
      ${cp.load_adjusted ? '<div style="margin-top:2px;color:#7c2d12">Load rule applied: heavier load raised the wind level</div>' : ''}
      ${cp.low_confidence ? '<div style="margin-top:2px;color:#475569">Over 72 h out: low-confidence forecast</div>' : ''}</div>`.replace(
    /\n\s*/g,
    '',
  );
}
