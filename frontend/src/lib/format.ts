/** Every time shown to the driver is in the browser's zone with its abbreviation (D-19). */

const timeFmt = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
  timeZoneName: 'short',
});

export function formatTime(iso: string | Date): string {
  const d = typeof iso === 'string' ? new Date(iso) : iso;
  const parts = timeFmt.formatToParts(d);
  const get = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value;
  return `${get('weekday')} ${get('hour')}:${get('minute')} ${get('timeZoneName')}`;
}

export function formatDuration(seconds: number): string {
  const totalMin = Math.round(seconds / 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m} min`;
}

const intFmt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const oneDp = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatMiles(mi: number): string {
  return `${mi >= 100 ? intFmt.format(mi) : oneDp.format(mi)} mi`;
}

export function formatInt(n: number): string {
  return intFmt.format(n);
}

export function formatRate(inPerHr: number | null): string {
  return inPerHr === null ? '—' : `${inPerHr.toFixed(2)} in/hr`;
}

export function formatMph(mph: number | null): string {
  return mph === null ? '—' : `${Math.round(mph)} mph`;
}

export function parseLoad(text: string): number | null {
  const digits = text.replace(/[,\s_]/g, '');
  if (!/^\d+$/.test(digits)) return null;
  return Number(digits);
}

/** "+12h · Thu 14:00" (D-14). */
export function formatOffset(hour: number, departureIso: string): string {
  const t = new Date(new Date(departureIso).getTime() + hour * 3_600_000);
  const sign = hour >= 0 ? '+' : '−';
  return `${sign}${Math.abs(Math.round(hour))}h · ${formatTime(t)}`;
}

const spokenFmt = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  hour: 'numeric',
  minute: '2-digit',
});

export function spokenOffset(hour: number, departureIso: string): string {
  const t = new Date(new Date(departureIso).getTime() + hour * 3_600_000);
  return `Plus ${Math.round(hour)} hours, ${spokenFmt.format(t)}`;
}
